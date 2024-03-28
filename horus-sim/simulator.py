"""Usage:
simulator.py -d <working_dir> -p <policy> -l <load> -k <k_value> -r <spine_ratio>  -t <task_distribution> -i <id> -f <failure_mode> [--delay <link_delay>] [--loss <loss_probability>] [--fid <failed_switch_id>] [--colocate] [--centralized] [--du] [--all]

simulator.py -h | --help
simulator.py -v | --version

Arguments:
  -d <working_dir> Directory containing dataset which is also used for result files
  -p <policy>  Scheduling policy to simulate (pow_of_k|pow_of_k_partitioned|jiq|adaptive)
  -l <load> System load
  -k <k_value> K: number of samples each switch takes for making decisions
  -r <spine_ratio> Ratio between #ToRs / #Spines (Inverse of L value)
  -i <run_id> Run ID used for multiple runs of single dataset
  -t <task_distribution> Distribution name for generated tasks (bimodal|trimodal|exponential)
  -f <failure_mode> Component to fail in the simulations (none|spine|leaf)
  --fid <failed_switch_id>
  --delay <link_delay>
  --loss <loss_probability>
Options:
  -h --help  Displays this message
  -v --version  Displays script version
"""
import numpy.random as nr
import numpy as np
import math
import random 
import sys
import pandas as pd
import time
from multiprocessing import Process, Queue, Value, Array
from loguru import logger
import docopt
import shutil
import queue
from heapq import *
import itertools

import utils
from vcluster import VirtualCluster, Event
from task import Task
from latency_model import LatencyModel
from spine_selector import SpineSelector

LOG_PROGRESS_INTERVAL = 900 # Dump some progress info periodically (in seconds)
LOAD_IMB_MEASURE_INT_TICKS = 50 * utils.TICKS_PER_MICRO_SEC # Measure load imbalance periodically (in us based on ticks)
SAMPLE_TENANTS_FRACTIONAL = 20 # 1/SAMPLE_TENANTS_FRACTIONAL of 1K tenants will be simulated for faster simulation results, use 1 for full results
result_dir = "./"
FAILURE_TIME_TICK = 100

counter = itertools.count()     # unique sequence count
event_queue = []
latency_model = LatencyModel()

def report_cluster_results(log_handler, policy_file_tag, sys_load, vcluster, run_id, is_colocate=False, save_all_results=False):
    log_handler.info(policy_file_tag + ' Finished cluster with ID:' + str(vcluster.cluster_id) +' wait_times @' + str(sys_load) + ':\n' +  str(pd.Series(vcluster.log_task_wait_time).describe([0.01, 0.25, 0.5, 0.75, 0.99])))
    log_handler.info(policy_file_tag + ' Finished cluster with ID:' + str(vcluster.cluster_id) +' response_times @' + str(sys_load) + ':\n' +  str(pd.Series(vcluster.log_response_time).describe([0.01, 0.25, 0.5, 0.75, 0.99])))
    latency_arr = np.array(latency_model.latency_hist)
    print(f"Latency summary: mean = {np.mean(latency_arr)}, median = {np.median(latency_arr)}, min = {np.min(latency_arr)}, 99th = {np.percentile(latency_arr, 99)}")
    utils.write_to_file(result_dir, 'wait_times', policy_file_tag, sys_load, vcluster.task_distribution_name,  vcluster.log_task_wait_time, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)
    utils.write_to_file(result_dir, 'response_times', policy_file_tag, sys_load, vcluster.task_distribution_name,  vcluster.log_response_time, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)
    # To reduce output file size, we do not store the following stats (its optional)
    # we used these in intermediate simulation stages for design decisions
    if save_all_results:
        #log_handler.info(policy_file_tag + ' Finished cluster with ID:' + str(vcluster.cluster_id) + ' transfer_times @' + str(sys_load) + ':\n' +  str(pd.Series(vcluster.log_task_transfer_time).describe()))
        utils.write_to_file(result_dir, 'transfer_times', policy_file_tag, sys_load, vcluster.task_distribution_name, vcluster.log_task_transfer_time, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)
        utils.write_to_file(result_dir, 'idle_count', policy_file_tag, sys_load, vcluster.task_distribution_name, vcluster.idle_counts, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)
        utils.write_to_file(result_dir, 'queue_lens', policy_file_tag, sys_load, vcluster.task_distribution_name,  vcluster.log_queue_len_signal_workers, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)
        if vcluster.policy == 'adaptive' or vcluster.policy == 'jiq':
                utils.write_to_file(result_dir, 'decision_type', policy_file_tag, sys_load, vcluster.task_distribution_name, vcluster.log_decision_type, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)

def handle_task_done(finished_task, tick, is_centralized):
    i = finished_task.target_worker
    vcluster = finished_task.vcluster
    tor_idx = finished_task.target_tor
    #  finished executing task
    vcluster.task_lists[i].pop(0)  # Remove from list
    if len(vcluster.task_lists[i]) != 0:  # Not idle after this event, another task will start on worker
        vcluster.curr_task_start_time[i] = tick
    if is_centralized:
        vcluster.queue_lens_workers[i] = len(vcluster.task_lists[i])
    n_hops = 1
    #print(f"Finished Task ID {finished_task.task_idx} at worker {i}, worker Qlen is {len(vcluster.task_lists[i])}")
    # Loss simulation: reply pkt (load info) from worker to leaf
    update_msg = Event(event_type='task_reply',
                       vcluster=finished_task.vcluster,
                       task=finished_task,
                       qlen=len(vcluster.task_lists[i]),
                       src_id=i,
                       component_id=tor_idx,
                       delay=latency_model.get_in_network_delay(n_hops=n_hops))
    return update_msg

def handle_task_reply(msg):
    finished_task = msg.task
    tor_idx = finished_task.target_tor
    i = finished_task.target_worker
    vcluster = finished_task.vcluster
    #print(f"Reply Task ID {finished_task.task_idx} at ToR {tor_idx}, Selected worker was: ", i)
    tor_id = utils.get_tor_id_for_host(vcluster.host_list[i])
    #print(f"Qlen worker was {vcluster.queue_lens_workers[i]}, Qlen tor was {vcluster.queue_lens_tors[tor_idx]}")
    vcluster.queue_lens_workers[i] = msg.qlen  # Decrement worker queue len

    vcluster.queue_lens_tors[tor_idx] = utils.calculate_tor_queue_len(tor_id, vcluster.queue_lens_workers,
                                                                      vcluster.host_list)
    #print(f"Qlen worker updated {vcluster.queue_lens_workers[i]}, Qlen tor updated {vcluster.queue_lens_tors[tor_idx]}")
    msg_list = []
    # REUSE
    if (vcluster.policy == 'pow_of_k') or (vcluster.policy == 'pow_of_k_partitioned'): # Random and JIQ do not use this part
        if vcluster.policy == 'pow_of_k':
            # Update ToR queue len at all of the spines
            for spine_idx, spine_id in enumerate(vcluster.selected_spine_list):
                load_msg = Event(event_type='msg_load_signal',
                      vcluster=finished_task.vcluster,
                      qlen=vcluster.queue_lens_tors[tor_idx],
                      src_id=tor_idx,
                      component_id=spine_idx,
                      delay=latency_model.get_in_network_delay(n_hops=utils.get_tor_spine_hops(finished_task.global_tor_id, spine_id)))
                msg_list.append(load_msg)
        else: # Only update the designated spine
            mapped_spine_idx = vcluster.tor_spine_map[tor_idx]
            mapped_spine_id = vcluster.selected_spine_list[mapped_spine_idx]
            load_msg = Event(event_type='msg_load_signal',
                             vcluster=finished_task.vcluster,
                             qlen=vcluster.queue_lens_tors[tor_idx],
                             src_id=tor_idx,
                             component_id=mapped_spine_idx,
                             delay=latency_model.get_in_network_delay(
                                 n_hops=utils.get_tor_spine_hops(finished_task.global_tor_id, mapped_spine_id)))
            msg_list.append(load_msg)
    elif vcluster.policy == 'adaptive' or vcluster.policy == 'jiq':  # JIQ and adaptive
        if msg.qlen == 0: # New idle worker
            vcluster.idle_queue_tor[tor_idx].add(i)
        #     if vcluster.tor_idle_link[tor_idx] == -1 and (len(vcluster.idle_queue_tor[tor_idx]) > 2): # Not linked with any spine yet
        #         spine_to_pair_idx = random.choice(range(0, vcluster.num_spines))
        #         spine_to_pair_id = vcluster.selected_spine_list[spine_to_pair_idx]
        #         #print(f"Tor {tor_idx} Sent idle signal to {spine_to_pair_idx} ")
        #         idle_link_msg = Event(event_type='msg_idle_signal',
        #                          vcluster=finished_task.vcluster,
        #                          qlen=0,
        #                          src_id=tor_idx,
        #                          component_id=spine_to_pair_idx,
        #                          delay=latency_model.get_in_network_delay(n_hops=utils.get_tor_spine_hops(finished_task.global_tor_id, spine_to_pair_id)))
        #         msg_list.append(idle_link_msg)
        #         vcluster.tor_idle_link[tor_idx] = spine_to_pair_idx
        # if len(vcluster.idle_queue_tor[tor_idx]) <= 2:
        #     if vcluster.tor_idle_link[tor_idx] != -1: # linked with some spine
        #         spine_to_pair_idx = vcluster.tor_idle_link[tor_idx]
        #         spine_to_pair_id = vcluster.selected_spine_list[spine_to_pair_idx]
        #         #print(f"Tor {tor_idx} Sent idle REMOVE to {spine_to_pair_idx} ")
        #         idle_remove_msg = Event(event_type='msg_idle_remove',
        #                          vcluster=finished_task.vcluster,
        #                          qlen=0,
        #                          src_id=tor_idx,
        #                          component_id=spine_to_pair_idx,
        #                          delay=latency_model.get_in_network_delay(n_hops=utils.get_tor_spine_hops(finished_task.global_tor_id, spine_to_pair_id)))
        #         msg_list.append(idle_remove_msg)
        #         vcluster.tor_idle_link[tor_idx] = -1
        if vcluster.policy == 'adaptive' and not is_centralized:  # Adaptive
            # ToR that is paired with a spine, will update the signal
            linked_spine_idx = vcluster.tor_spine_map[tor_idx]
            vcluster.num_reply_observed[tor_idx] += 1
            # Design for reducing for msg rate: Update spine switch view only if the state is drifted more than "1" !
            if vcluster.num_reply_observed[tor_idx] >= (vcluster.workers_per_tor[tor_idx]):
                spine_id = vcluster.selected_spine_list[linked_spine_idx]
                vcluster.num_reply_observed[tor_idx] = 0
                load_msg = Event(event_type='msg_load_signal',
                                 vcluster=finished_task.vcluster,
                                 qlen=vcluster.queue_lens_tors[tor_idx],
                                 src_id=tor_idx,
                                 component_id=linked_spine_idx,
                                 delay=latency_model.get_in_network_delay(n_hops=utils.get_tor_spine_hops(finished_task.global_tor_id, spine_id)))
                msg_list.append(load_msg)
    return msg_list

def spine_schedule_task_random_pow_of_k(new_task, target_spine):
    vcluster = new_task.vcluster
    queue_lens_workers = vcluster.queue_lens_workers
    target_tor = random.randrange(vcluster.num_tors) # Randomly select one leaf scheduler
    
    new_task.set_decision_spine(target_spine, target_tor)
    return new_task

def tor_schedule_task_pow_of_k(new_task, k, target_tor):
    vcluster = new_task.vcluster
    num_workers = vcluster.num_workers
    queue_lens_workers = vcluster.queue_lens_workers
    worker_indices = utils.get_worker_indices_for_tor(vcluster.tor_id_unique_list[target_tor], vcluster.host_list)
    if len(worker_indices) < 1:
        print("Bug")
        print("Vcluster: ", vcluster.cluster_id)
        print("Target tor: ", target_tor)
        print("vcluster.tor_id_unique_list: ", vcluster.tor_id_unique_list[target_tor])
        print("vcluster.host_list: ", vcluster.tor_id_unique_list[target_tor])
        print("queue_lens_workers: ", queue_lens_workers)
        print("num_workers: ", num_workers)
        exit(0)
    # Select worker
    num_samples = min(len(worker_indices), k)
    sample_indices = random.sample(worker_indices, num_samples) # Sample from workers connected to that ToR
    target_worker = utils.select_sample(queue_lens_workers, sample_indices)
    new_task.set_decision_tor(target_worker)
    #print(f"Task ID {new_task.task_idx} at ToR {target_tor}, Selected worker: ", target_worker)
    return new_task, []

def schedule_task_central_queue(new_task, target_spine_id, target_spine_idx, spine_falcon_used_slots):
    vcluster = new_task.vcluster
    if (spine_falcon_used_slots[target_spine_id] >= utils.FALCON_QUEUE_SLOTS):
        return -1, spine_falcon_used_slots
    vcluster.falcon_queue.append(new_task)
    spine_falcon_used_slots[target_spine_id] += 1
    return 0, spine_falcon_used_slots

def spine_schedule_task_pow_of_k(new_task, k, target_spine, is_centralized):
    vcluster = new_task.vcluster
    num_spines = vcluster.num_spines
    num_tors = vcluster.num_tors
    num_workers = vcluster.num_workers
    queue_lens_tors = vcluster.known_queue_len_spine[target_spine]
    #print("Known queue lens", vcluster.known_queue_len_spine[target_spine])
    #print("Actual queue lens", vcluster.queue_lens_tors)
    queue_lens_workers = vcluster.queue_lens_workers
    # In centralized scenario, the decision is worker-based so we drive the ToR based on worker for our simulation calculations only
    if is_centralized:
        worker_indices = range(0, vcluster.num_workers)
        num_samples = min(vcluster.num_workers, k)
        sample_indices = random.sample(worker_indices, num_samples) # Sample from workers connected to that ToR
        target_worker = utils.select_sample(queue_lens_workers, sample_indices)
        target_tor = vcluster.tor_id_unique_list.index(utils.get_tor_id_for_host(vcluster.host_list[target_worker]))
        new_task.set_decision_centralized(target_spine, target_tor, target_worker)
    else:
        # Select ToR
        num_samples = min(num_tors, k)
        sample_indices = random.sample(range(0, num_tors), num_samples) # Info about all tors available at every spine
        target_tor = utils.select_sample(queue_lens_tors, sample_indices)
        new_task.set_decision_spine(target_spine, target_tor)
    #print(f"Task ID {new_task.task_idx} at Spine, Selected tor: ", target_tor)
    return new_task

def spine_schedule_task_pow_of_k_partitioned(new_task, k, target_spine):
    vcluster = new_task.vcluster
    num_spines = vcluster.num_spines
    num_tors = vcluster.num_tors
    queue_lens_tors = vcluster.queue_lens_tors

    # Make decision at Spine level:
    mapped_tor_list = new_task.vcluster.spine_tor_map[target_spine]
    num_samples = min(len(mapped_tor_list), k)

    sample_indices = random.sample(mapped_tor_list, num_samples) # k samples from tors available to that spine
    target_tor = utils.select_sample(queue_lens_tors, sample_indices)
    new_task.set_decision_spine(target_spine, target_tor)
    return new_task

def spine_schedule_task_jiq(new_task, target_spine, is_centralized):
    if is_centralized:
        if new_task.vcluster.idle_queue_spine[target_spine]: # Spine scheduler is aware of some idle workers
            target_worker = new_task.vcluster.idle_queue_spine[target_spine].pop(0)
        else:
            worker_indices = range(0, new_task.vcluster.num_workers)
            target_worker = random.choice(worker_indices)

        target_tor = new_task.vcluster.tor_id_unique_list.index(utils.get_tor_id_for_host(new_task.vcluster.host_list[target_worker]))
        new_task.set_decision_centralized(target_spine, target_tor, target_worker)
    else:
        # Make decision at spine level:
        if new_task.vcluster.idle_queue_spine[target_spine]:  # Spine is aware of some tors with idle wokrers
            target_tor = new_task.vcluster.idle_queue_spine[target_spine][0]
            new_task.decision_tag = 0
        else:   # No tor with idle worker is known, dispatch to a random tor
            #target_tor = random.choice(get_tor_partition_range_for_spine(target_spine)) Limit to pod
            target_tor = nr.randint(0, new_task.vcluster.num_tors) # Can forward to any ToR
            new_task.decision_tag = 2
        new_task.set_decision_spine(target_spine, target_tor)
        
    return new_task

def tor_schedule_task_jiq(new_task, target_tor):
    target_tor = new_task.target_tor
    if len(new_task.vcluster.idle_queue_tor[target_tor]) > 0: # Tor is aware of some idle workers
            target_worker = new_task.vcluster.idle_queue_tor[target_tor].pop()
    else:
        worker_indices = utils.get_worker_indices_for_tor(new_task.vcluster.tor_id_unique_list[target_tor], new_task.vcluster.host_list)
        target_worker = random.choice(worker_indices)
    new_task.set_decision_tor(target_worker)
    # @parham: REUSE
    update_msg = None
    if len(new_task.vcluster.idle_queue_tor[target_tor]) <= 2:
        for spine_idx, idle_tors in enumerate(new_task.vcluster.idle_queue_spine):
            if target_tor in idle_tors:   # Tor was previously presented as idle to one of spines
                spine_id = new_task.vcluster.selected_spine_list[spine_idx]
                update_msg = Event(event_type='msg_idle_remove',
                                    vcluster=new_task.vcluster,
                                    src_id=target_tor,
                                    component_id=spine_idx,
                                    delay=latency_model.get_in_network_delay(n_hops=utils.get_tor_spine_hops(new_task.global_tor_id, spine_id)))
                break
                # @parham: REUSE
                #new_task.vcluster.idle_queue_spine[spine_idx].remove(target_tor)
                #spine_id = new_task.vcluster.selected_spine_list[spine_idx]
                #num_msg_spine[spine_id] += 1
    return new_task, [update_msg]

def spine_schedule_task_adaptive(new_task, k, target_spine, is_centralized):
    partition_size_spine = new_task.vcluster.partition_size
    vcluster = new_task.vcluster
    if is_centralized:
        num_workers = vcluster.num_workers
        queue_lens_workers = vcluster.queue_lens_workers
        # Make decision at spine layer:
        if len(new_task.vcluster.idle_queue_spine[target_spine]) > 0:  # Spine is aware of idle workers
            target_worker = new_task.vcluster.idle_queue_spine[target_spine].pop(0)
            new_task.decision_tag = 0
        else:   # No idle worker is known do pow-of-k
            num_samples = min(num_workers, k)
            sample_indices = random.sample(range(0, num_workers), num_samples) 
            target_worker = utils.select_sample(queue_lens_workers, sample_indices)
        target_tor = new_task.vcluster.tor_id_unique_list.index(utils.get_tor_id_for_host(new_task.vcluster.host_list[target_worker]))
        new_task.set_decision_centralized(target_spine, target_tor, target_worker)
    else:
        target_spine_id = new_task.vcluster.selected_spine_list[target_spine]
        # Make decision at spine layer:
        if len(new_task.vcluster.idle_queue_spine[target_spine]) > 0:  # Spine is aware of some tors with idle servers
            idle_index = random.choice(range(len(new_task.vcluster.idle_queue_spine[target_spine])))
            target_tor = new_task.vcluster.idle_queue_spine[target_spine][idle_index]
            new_task.decision_tag = 0
        else:   # No tor with idle server is known
            if (len(new_task.vcluster.known_queue_len_spine[target_spine]) > 2): # Do shortest queue if enough info available    
                num_samples = min(len(new_task.vcluster.known_queue_len_spine[target_spine]), k)
                sample_tors = random.sample(list(new_task.vcluster.known_queue_len_spine[target_spine]), num_samples) # k samples from ToR queue lenghts available to that spine
                target_tor = utils.select_sample(new_task.vcluster.known_queue_len_spine[target_spine], sample_tors)
                new_task.decision_tag = 1 # shortest-queue-based decision
            else: # Randomly select a ToR from all of the available tors
                target_tor = nr.randint(0, new_task.vcluster.num_tors)
                new_task.decision_tag = 2 # Random-based decision
        new_task.set_decision_spine(target_spine, target_tor)
    return new_task
    
    # for tor_idx, idle_worker_list in enumerate(new_task.vcluster.idle_queue_tor):
    #     isUnique = np.unique(idle_worker_list).size == len(idle_worker_list)
    #     if not isUnique:
    #         print ("DEBUG: Idle list of Tor is not unique! Problem!")
    
    # for spine_idx, idle_tor_list in enumerate(new_task.vcluster.idle_queue_spine):
    #         isUnique = np.unique(idle_tor_list).size == len(idle_tor_list)
    #         if not isUnique:
    #             print ("DEBUG: Idle list of Spine is not unique! Problem!")
    # temp_tor_idx_list = []
    # for known_queue_len_list in new_task.vcluster.known_queue_len_spine:
    #     for tor_idx in known_queue_len_list:
    #         if tor_idx not in temp_tor_idx_list:
    #             temp_tor_idx_list.append(tor_idx)
    #         else:
    #             print("DEBUG: Load list of spines not disjoint!")

def tor_schedule_task_adaptive(new_task, k):
    target_tor = new_task.target_tor
    vcluster = new_task.vcluster
    idle_list_len = len(new_task.vcluster.idle_queue_tor[target_tor])
    if idle_list_len > 0:  # Tor is aware of some idle workers
            target_worker = new_task.vcluster.idle_queue_tor[target_tor].pop()
    else: # No idle worker
        worker_indices = utils.get_worker_indices_for_tor(new_task.vcluster.tor_id_unique_list[target_tor], new_task.vcluster.host_list)
        num_samples = min(len(worker_indices), k)
        sample_indices = random.sample(worker_indices, num_samples) # Sample from workers connected to that ToR
        target_worker = utils.select_sample(new_task.vcluster.queue_lens_workers, sample_indices)
    new_task.set_decision_tor(target_worker)
    linked_spine_idx = new_task.vcluster.tor_idle_link[target_tor]
    # This is how tor (passivley) detects idle remove signal was failed
    if new_task.decision_tag == 0 and linked_spine_idx == -1:
        vcluster.num_idle_task_observed[target_tor] += 1
        if (vcluster.num_idle_task_observed[target_tor] > vcluster.workers_per_tor[target_tor]):
            linked_spine_idx = new_task.first_spine
            new_task.vcluster.tor_idle_link[target_tor] = new_task.first_spine
            vcluster.num_idle_task_observed[target_tor] = 0;
        
        
    update_msgs = []
    # Rack is not idle anymore
    if len(new_task.vcluster.idle_queue_tor[target_tor]) <= 4: 
        if (linked_spine_idx != -1): # Tor linked with one of spines (spine thinks it's idle)
            # @parham: REUSE
            new_task.vcluster.tor_idle_link[target_tor] = -1 # Tor removed linkage
            spine_id = new_task.vcluster.selected_spine_list[linked_spine_idx]
            #print(f"ToR {target_tor} sent idle REMOVE to {linked_spine_idx}")
            update_msg_idle = Event(event_type='msg_idle_remove',
                            vcluster=new_task.vcluster,
                            src_id=target_tor,
                            component_id=linked_spine_idx,
                            delay=latency_model.get_in_network_delay(n_hops=utils.get_tor_spine_hops(new_task.global_tor_id, spine_id)))
            update_msgs.append(update_msg_idle)
            vcluster.num_idle_task_observed[target_tor] = 0;
    elif len(new_task.vcluster.idle_queue_tor[target_tor]) > 4:
        if (linked_spine_idx == -1):
            spine_to_pair_idx = random.choice(range(0, vcluster.num_spines))
            spine_to_pair_id = vcluster.selected_spine_list[spine_to_pair_idx]
            idle_link_msg = Event(event_type='msg_idle_signal',
                                  vcluster=new_task.vcluster,
                                  qlen=0,
                                  src_id=target_tor,
                                  component_id=spine_to_pair_idx,
                                  delay=latency_model.get_in_network_delay(
                                      n_hops=utils.get_tor_spine_hops(new_task.global_tor_id, spine_to_pair_id)))
            update_msgs.append(idle_link_msg)
            new_task.vcluster.tor_idle_link[target_tor] = spine_to_pair_idx
            vcluster.num_idle_task_observed[target_tor] = 0;
    tor_update_switch_views(new_task)
    new_task.vcluster.queue_lens_tors[new_task.target_tor] = utils.calculate_tor_queue_len(new_task.global_tor_id,
                                    new_task.vcluster.queue_lens_workers,
                                    new_task.vcluster.host_list
                                    )

    #linked_spine_idx = new_task.vcluster.tor_spine_map[new_task.target_tor]
    # if abs(new_task.vcluster.queue_lens_tors[new_task.target_tor] - new_task.vcluster.known_queue_len_spine[linked_spine_idx][new_task.target_tor]) >= 1:
    #     spine_id = new_task.vcluster.selected_spine_list[linked_spine_idx]
    #     update_msg_load = Event(event_type='msg_load_signal',
    #                             vcluster=new_task.vcluster,
    #                             src_id=target_tor,
    #                             qlen=new_task.vcluster.queue_lens_tors[new_task.target_tor],
    #                             component_id=linked_spine_idx,
    #                             delay=latency_model.get_in_network_delay(n_hops=utils.get_tor_spine_hops(new_task.global_tor_id, spine_id)))
    #     update_msgs.append(update_msg_load)
    return new_task, update_msgs
    
def handle_msg_idle_remove(msg):
    vcluster = msg.vcluster
    spine_idx = msg.component_id
    if msg.src_id in vcluster.idle_queue_spine[spine_idx]:
        vcluster.idle_queue_spine[spine_idx].remove(msg.src_id)

def handle_msg_load(msg):
    vcluster = msg.vcluster
    spine_idx = msg.component_id
    vcluster.known_queue_len_spine[spine_idx].update({msg.src_id: msg.qlen}) # Update SQ signals
    #print(f"Msg load from ToR {msg.src_id} : {msg.qlen}")

def handle_msg_idle_signal(msg):
    vcluster = msg.vcluster
    spine_idx = msg.component_id
    if msg.src_id not in vcluster.idle_queue_spine[spine_idx]:
        vcluster.idle_queue_spine[spine_idx].append(msg.src_id)

def spine_update_switch_views(scheduled_task, is_centralized):
    if is_centralized:
        scheduled_task.vcluster.queue_lens_workers[scheduled_task.target_worker] += 1 
        return   
    if scheduled_task.vcluster.policy == 'adaptive':
        # If spine knows the queue len of this tor, it will increment it
        if (scheduled_task.target_tor in scheduled_task.vcluster.spine_tor_map[scheduled_task.first_spine]): 
            scheduled_task.vcluster.known_queue_len_spine[scheduled_task.first_spine][scheduled_task.target_tor] += (1.0 / scheduled_task.vcluster.workers_per_tor[scheduled_task.target_tor])

def tor_update_switch_views(scheduled_task):
    scheduled_task.vcluster.queue_lens_workers[scheduled_task.target_worker] += 1   

def get_dcn_results(tick, num_msg_spine, num_msg_spine_idle_remove, num_msg_spine_idle_signal, num_msg_spine_load_signal, num_task_tor, num_task_spine):
    exp_duration_s = float(tick) / (10**9)
    msg_per_sec_spine = [x / exp_duration_s for x in num_msg_spine]
    msg_per_sec_spine_idle_remove = [x / exp_duration_s for x in num_msg_spine_idle_remove]
    msg_per_sec_spine_idle_signal = [x / exp_duration_s for x in num_msg_spine_idle_signal]
    msg_per_sec_spine_load_signal = [x / exp_duration_s for x in num_msg_spine_load_signal]
    msg_per_sec_spine = [x / exp_duration_s for x in num_msg_spine]
    task_per_sec_tor = [x / exp_duration_s for x in num_task_tor]
    task_per_sec_spine = [x / exp_duration_s for x in num_task_spine]
    return msg_per_sec_spine, msg_per_sec_spine_idle_remove, msg_per_sec_spine_idle_signal, msg_per_sec_spine_load_signal, task_per_sec_tor, task_per_sec_spine

def handle_task_delivered(event, is_centralized, tick, policy):
    delivered_task = event.task

    if len(delivered_task.vcluster.task_lists[delivered_task.target_worker]) == 0: 
        delivered_task.vcluster.curr_task_start_time[delivered_task.target_worker] = tick
    # Calculates amount of time passed for the task that is currently running
    running_task_passed = tick - delivered_task.vcluster.curr_task_start_time[delivered_task.target_worker]

    if policy != 'central_queue': # Task (will) wait in worker queue: should wait as long as pending tasks at worker
        task_waiting_time = np.sum(delivered_task.vcluster.task_lists[delivered_task.target_worker]) - running_task_passed
        task_response_time = task_waiting_time + delivered_task.load + (tick - delivered_task.arrive_time)
    else:
        task_waiting_time = tick - delivered_task.arrive_time # Task waited in scheduler queue
        task_response_time = task_waiting_time + delivered_task.load
    
    if task_waiting_time == 0:
        delivered_task.vcluster.log_zero_wait_tasks += 1
    
    #print(f"Delivered Task {delivered_task.task_idx}, #tasks in queue : {len(delivered_task.vcluster.task_lists[delivered_task.target_worker])}, waiting time : {task_waiting_time}, selected ToR : {delivered_task.target_tor}, selected worker: {delivered_task.target_worker}")
    
    delivered_task.vcluster.log_total_tasks += 1
    delivered_task.vcluster.log_task_wait_time.append(task_waiting_time) 
    delivered_task.vcluster.log_response_time.append(task_response_time)
    
    delivered_task.vcluster.log_task_transfer_time.append(tick - delivered_task.arrive_time)
    delivered_task.vcluster.log_queue_len_signal_workers.append(delivered_task.vcluster.queue_lens_workers[delivered_task.target_worker])
    delivered_task.vcluster.log_decision_type.append(delivered_task.decision_tag)
    if not is_centralized:
        delivered_task.vcluster.log_queue_len_signal_tors.append(delivered_task.vcluster.queue_lens_tors[delivered_task.target_tor])
    
    delivered_task.vcluster.task_lists[delivered_task.target_worker].append(delivered_task.load)
    
    return task_waiting_time

def run_scheduling(policy, data, k, task_distribution_name, sys_load, spine_ratio, run_id, failure_mode, is_colocate, failed_switch_id, expon_arrival=True, is_centralized=False, delayed_updates=False, save_all_results=False):
    nr.seed()
    random.seed()
    
    if is_centralized:
        utils.num_spines = 1
    
    latency_model.read_dataset(result_dir)
    latency_model.set_loss_p(utils.LOSS_PROBABILITY)
    spine_selector = SpineSelector(utils.PER_SPINE_CAPACITY)
    controller_pod = random.choice(range(utils.num_pods))

    policy_file_tag = utils.get_policy_file_tag(policy, k)
    
    if delayed_updates:
        if policy == 'adaptive': # This is a special case for adaptive (ours), others use delayed updates by default
            policy_file_tag += str('_du')
    else:
        if policy == 'random_pow_of_k' or policy == 'pow_of_k' or policy == 'pow_of_k_partitioned':
            policy_file_tag += str('_iu') # Instant update is special case for other systems, only used for dissection to show Saqr benefits

    logger_tag_clusters = "summary_clusters_" + policy_file_tag + '_' + str(sys_load) + '_r' + str(run_id) + ".log"
    logger_tag_dcn = "summary_dcn_" + policy_file_tag + '_' + str(sys_load) + '_r' + str(run_id) + ".log"

    logger.add(sys.stdout, filter=lambda record: record["extra"]["task"] == logger_tag_clusters)
    log_handler_experiment = logger.bind(task=logger_tag_clusters)

    logger.add(sys.stdout, filter=lambda record: record["extra"]["task"] == logger_tag_dcn, level="INFO")
    log_handler_dcn = logger.bind(task=logger_tag_dcn)

    cluster_terminate_count = 0
    vcluster_list = []

    tenants = data['tenants']

    num_total_workers = data['tenants']['worker_count']

    tenants_maps = tenants['maps']
    #tenants_maps = [t for i, t in enumerate(tenants_maps) if ((i >= run_id*1) and (i < (run_id+1)*1))]
    tenants_maps = [t for i, t in enumerate(tenants_maps) if (i%SAMPLE_TENANTS_FRACTIONAL==0)]
    # print ("len(tenants_maps):")
    # print (len(tenants_maps))
    # exit(0)
    num_tenants = len(tenants_maps)
    
    worker_start_idx = 0 # Used for mapping local worker_id to global_worker_id
    
    for t in range(len(tenants_maps)):
        host_list = tenants_maps[t]['worker_to_host_map']
        cluster_id = tenants_maps[t]['app_id']
        vcluster = VirtualCluster(cluster_id,
            worker_start_idx,
            policy,
            host_list,
            sys_load,
            spine_selector,
            target_partition_size=spine_ratio,
            task_distribution_name=task_distribution_name,
            is_single_layer=is_centralized)
        
        # For failure simulations we only process events of the impacted clusters (instead of all vclusters)
        if failure_mode == 'none':
            seq = next(counter)
            event_entry = [0, seq, Event(event_type='new_task', vcluster=vcluster)]
            heappush(event_queue, event_entry)
            if policy == 'central_queue':
                for w_idx in range (vcluster.num_workers): # Initially add a retrive attempt for all workers
                    seq = next(counter)
                    event_entry = [100, seq, Event(event_type='falcon_retrive', vcluster=vcluster, component_id=w_idx)]
                    heappush(event_queue, event_entry)
        for i, client_pod in enumerate(vcluster.client_pods):
            controller_latency = latency_model.get_notification_to_client_latency(controller_pod, client_pod)
            vcluster.set_client_controller_latency(i, controller_latency)

        vcluster_list.append(vcluster)
        worker_start_idx += tenants_maps[t]['worker_count']
    
    failure_happened = False
    failure_detected = False
    num_msg_to_client = 0
    num_msg_to_leaf_controller = 0
    num_converged_vclusters = 0
    affected_tor_list = []
    affected_vcluster_list = []  
    
    if (failure_mode == 'spine'):
        failed_spine_id = failed_switch_id
        # If the failed spine was not used by any of the vclusters, terminate otherwise add events for the (to-be) impacted vclusters and process them
        for vcluster in vcluster_list:
            #print (vcluster.selected_spine_list)
            if failed_spine_id in vcluster.selected_spine_list:
                print(vcluster.inter_arrival)
                affected_vcluster_list.append(vcluster)
                seq = next(counter)
                event_entry = [0, seq, Event(event_type='new_task', vcluster=vcluster)]
                heappush(event_queue, event_entry)
                
        if len(affected_vcluster_list)==0:
            print ("Failure had no impact terminating experiment")
            exit(1) 
        seq = next(counter)
        event_entry = [FAILURE_TIME_TICK, seq, Event(event_type='switch_failure', component_id=failed_spine_id)]
        heappush(event_queue, event_entry)
        
    elif (failure_mode == 'leaf'):
        failed_leaf_id = failed_switch_id

    in_transit_tasks = []
    
    decision_tag = 0
    
    num_msg_spine = [0] * utils.num_spines
    num_msg_spine_idle_remove = [0] * utils.num_spines
    num_msg_spine_idle_signal = [0] * utils.num_spines
    num_msg_spine_load_signal = [0] * utils.num_spines

    num_task_spine = [0] * utils.num_spines  
    num_task_tor = [0] * utils.num_tors

    switch_state_spine = [] * utils.num_spines 
    switch_state_tor = [] * utils.num_tors

    spine_falcon_used_slots = [0] * utils.num_spines 
    terminate_experiment = False
    for spine_idx in range(utils.num_spines):
        switch_state_spine.append([0])

    for tor_idx in range(utils.num_tors):
        switch_state_tor.append([0])

    start_time_log = time.time()
    start_time_imb_measure = 0 # ticks

    tick = 0
    
    event_count = 0
    max_event_tick = 0
    failure_detection_time = 0

    # Main loop for simulated events
    while(cluster_terminate_count < len(vcluster_list)):
        event_tick, count, event = heappop(event_queue)
        event_count += 1

        if (spine_falcon_used_slots[0]>=utils.FALCON_QUEUE_SLOTS):
            print("Reached queue capacity!")
            print("Got event: " + str(event.type) + " at tick: " + str(event_tick))
            print(spine_falcon_used_slots[0])

        if event_tick >= max_event_tick:
            max_event_tick = event_tick
        else:
            print("Max event tick: " + str(max_event_tick))
            print("But got tick: " + str(event_tick))
            raise Exception("Got event in past!")
        
        tick = event_tick
        if event.type == 'new_task':
            vcluster = event.vcluster
            vcluster.last_task_arrival = event_tick

            load = vcluster.task_distribution[vcluster.task_idx] # Pick new task load (load is execution time)
            new_task = Task(latency_model, load, vcluster, tick)
            scheduling_failed = False
            # A random client will initiate the request
            client_index = random.randrange(vcluster.num_clients)
            # Simulating arrival of task at a spine randomly
            spine_sched_id = random.choice(vcluster.client_spine_list[client_index]) # Global ID of spine
            spine_shched_index = vcluster.selected_spine_list.index(spine_sched_id) # Index of spine for that vcluster (i.e local index 0-S for each vcluster)

            if failure_happened:
                if spine_sched_id == failed_spine_id: # Task was sent to the failed scheduler
                    vcluster.num_failed_tasks += 1
                    scheduling_failed = True
                else:
                    if not vcluster.failover_converged:
                        vcluster.num_scheduled_tasks += 1

            if not scheduling_failed:
                if vcluster.policy == 'random_pow_of_k':
                    scheduled_task = spine_schedule_task_random_pow_of_k(new_task, spine_shched_index)
                
                elif vcluster.policy == 'central_queue':
                    is_failed, spine_falcon_used_slots = schedule_task_central_queue(new_task, spine_sched_id, spine_shched_index, spine_falcon_used_slots)
                    if is_failed:
                        vcluster.num_failed_tasks += 1
                        print ("Failed tasks: " + str(vcluster.num_failed_tasks))
                    scheduled_task = new_task
                    scheduled_task.set_decision_spine(0, 0) # Dummy 
                
                elif vcluster.policy == 'pow_of_k':
                    scheduled_task = spine_schedule_task_pow_of_k(new_task, k, spine_shched_index, is_centralized)
                    
                elif vcluster.policy == 'pow_of_k_partitioned':
                    scheduled_task = spine_schedule_task_pow_of_k_partitioned(new_task, k, spine_shched_index)

                elif vcluster.policy == 'jiq':
                    scheduled_task = spine_schedule_task_jiq(
                        new_task,  
                        spine_shched_index,
                        is_centralized)

                elif vcluster.policy == 'adaptive':
                    scheduled_task = spine_schedule_task_adaptive(
                        new_task,
                        k, 
                        spine_shched_index,
                        is_centralized)

                #print(new_task.vcluster.queue_lens_tors)

                num_task_spine[spine_sched_id] += 1
                num_task_tor[scheduled_task.global_tor_id] += 1
                if not delayed_updates:
                    spine_update_switch_views(scheduled_task, is_centralized)
                
                if (policy != 'central_queue') and (not scheduling_failed):
                    # Trigger two future events (1) task delivered to worker (2) next task arrive at scheduler
                    seq = next(counter)
                    if is_centralized:
                        event_entry = [tick + scheduled_task.network_time, seq, Event(event_type='delivered', vcluster=vcluster, task=scheduled_task)]
                    else:
                        event_entry = [tick + scheduled_task.network_time, seq, Event(event_type='new_task_tor', vcluster=vcluster, task=scheduled_task)]
                    heappush(event_queue, event_entry)

            if vcluster.task_idx < (len(vcluster.task_distribution) - 1):
                seq = next(counter)
                if expon_arrival: # Interarrival delay is not constant (not uniform) and simulates a poisson process with exponential interarrivals
                    next_arrival = tick + random.expovariate(1.0 / vcluster.inter_arrival)
                    #print("vcluster size: " + str(vcluster.num_workers) + " int arrival : " + str(random.expovariate(1.0 / vcluster.inter_arrival)))
                else: # Uniform inter arrivals
                    next_arrival = tick + vcluster.inter_arrival

                event_entry = [next_arrival, seq, Event(event_type='new_task', vcluster=vcluster)]
                heappush(event_queue, event_entry)
                vcluster.task_idx += 1

        elif event.type == 'new_task_tor':
            new_task = event.task
            tor = new_task.target_tor
            policy = vcluster.policy
            update_msgs=[]
            if policy == 'random_pow_of_k' or policy == 'pow_of_k' or policy == 'pow_of_k_partitioned':
                scheduled_task, update_msgs = tor_schedule_task_pow_of_k(new_task, k, tor)
            elif policy == 'jiq':
                scheduled_task, update_msgs = tor_schedule_task_jiq(new_task, tor)
            elif policy == 'adaptive':
                scheduled_task, update_msgs = tor_schedule_task_adaptive(new_task, k)
            seq = next(counter)
            event_entry = [tick + scheduled_task.network_time, seq, Event(event_type='delivered', vcluster=vcluster, task=scheduled_task)]
            heappush(event_queue, event_entry)
            for msg in update_msgs:
                if latency_model.is_pkt_sent():
                    seq = next(counter)
                    event_entry = [tick + msg.delay, seq, msg]
                    heappush(event_queue, event_entry)

        elif event.type == 'msg_idle_remove':
            handle_msg_idle_remove(event)
            num_msg_spine[event.vcluster.selected_spine_list[event.component_id]] += 1
            num_msg_spine_idle_remove[event.vcluster.selected_spine_list[event.component_id]] += 1
            #print("msg_load_signal")
        elif event.type == 'msg_load_signal':
            handle_msg_load(event)
            num_msg_spine[event.vcluster.selected_spine_list[event.component_id]] += 1
            num_msg_spine_load_signal[event.vcluster.selected_spine_list[event.component_id]] += 1
            #print("msg_load_signal")
        elif event.type == 'msg_idle_signal':
            handle_msg_idle_signal(event)
            num_msg_spine[event.vcluster.selected_spine_list[event.component_id]] += 1
            num_msg_spine_idle_signal[event.vcluster.selected_spine_list[event.component_id]] += 1
            #print(f"spine index {event.vcluster.selected_spine_list[event.component_id]} : {num_msg_spine[event.vcluster.selected_spine_list[event.component_id]] }")
            #print("msg_idle_signal")
        elif event.type == 'finished':
            event.vcluster.tasks_done += 1
            task_reply = handle_task_done(
                    finished_task=event.task,
                    tick=tick,
                    is_centralized=is_centralized)

            if event.task.vcluster.policy == 'central_queue':
                seq = next(counter) # After task is done Falcon sends a retrive packet to scheduler
                event_entry = [tick + latency_model.get_one_way_latency(), seq, Event(event_type='falcon_retrive', vcluster=event.task.vcluster, component_id=event.task.target_worker)]
                heappush(event_queue, event_entry)
            else: # Reply packet from worker to TOR
                if latency_model.is_pkt_sent():
                    seq = next(counter)
                    event_entry = [tick + task_reply.delay, seq, task_reply]
                    heappush(event_queue, event_entry)
            if event.vcluster.tasks_done == len(event.vcluster.task_distribution):
                cluster_terminate_count += 1
                report_cluster_results(log_handler_experiment, policy_file_tag, sys_load, event.vcluster, run_id, is_colocate, save_all_results)
                # Report these metrics for the period that all vclusters are running
                if (cluster_terminate_count==1):
                    print("msg per sec spine")
                    print(num_msg_spine)
                    msg_per_sec_spine, msg_per_sec_spine_idle_remove, msg_per_sec_spine_idle_signal, msg_per_sec_spine_load_signal, task_per_sec_tor, task_per_sec_spine = get_dcn_results(tick, num_msg_spine, num_msg_spine_idle_remove, num_msg_spine_idle_signal, num_msg_spine_load_signal, num_task_tor, num_task_spine)

                    utils.write_to_file(result_dir + '/analysis/', 'task_per_sec_tor', policy_file_tag, sys_load, task_distribution_name, task_per_sec_tor, run_id, is_colocate=is_colocate, append=True)
                    utils.write_to_file(result_dir + '/analysis/', 'task_per_sec_spine', policy_file_tag, sys_load, task_distribution_name, task_per_sec_spine, run_id, is_colocate=is_colocate, append=True)
                    if policy != 'random':
                        utils.write_to_file(result_dir + '/analysis/', 'msg_per_sec_spine', policy_file_tag, sys_load, task_distribution_name, msg_per_sec_spine, run_id, is_colocate=is_colocate, append=True)
                        utils.write_to_file(result_dir + '/analysis/', 'msg_per_sec_spine_idle_remove', policy_file_tag, sys_load, task_distribution_name, msg_per_sec_spine_idle_remove, run_id, is_colocate=is_colocate, append=True)
                        utils.write_to_file(result_dir + '/analysis/', 'msg_per_sec_spine_idle_signal', policy_file_tag, sys_load, task_distribution_name, msg_per_sec_spine_idle_signal, run_id, is_colocate=is_colocate, append=True)
                        utils.write_to_file(result_dir + '/analysis/', 'msg_per_sec_spine_load_signal', policy_file_tag, sys_load, task_distribution_name, msg_per_sec_spine_load_signal, run_id, is_colocate=is_colocate, append=True)


        elif event.type == 'task_reply':
            if not is_centralized:
                update_msgs = handle_task_reply(event)
                for msg in update_msgs:
                    if latency_model.is_pkt_sent():
                        seq = next(counter)
                        event_entry = [tick + msg.delay, seq, msg]
                        heappush(event_queue, event_entry)

        elif event.type == 'falcon_retrive':
            scheduler_id = event.vcluster.selected_spine_list[0]
            num_msg_spine[scheduler_id] += 1
            if (len(event.vcluster.falcon_queue) > 0): # there is a task in switch queue
                retrived_task = event.vcluster.falcon_queue.pop(0)
                spine_falcon_used_slots[event.vcluster.selected_spine_list[0]] -= 1
                retrived_task.target_worker = event.component_id # Send task to the worker that is source of this msg
                seq = next(counter) # After task is done we Falcon sends a retrive packet to scheduler
                event_entry = [tick + latency_model.get_one_way_latency(), seq, Event(event_type='delivered', vcluster=retrived_task.vcluster, task=retrived_task)]
                heappush(event_queue, event_entry)
            else: # Queue empty, wroker backs off and retry
                seq = next(counter) # After task is done we Falcon sends a retrive packet to scheduler
                event_entry = [tick + latency_model.get_one_way_latency() + utils.FALCON_RETRY_INTERVAL, seq, Event(event_type='falcon_retrive', vcluster=event.vcluster, component_id=event.component_id)]
                heappush(event_queue, event_entry)

        elif event.type == 'delivered':
            task_waiting_time = handle_task_delivered(event, is_centralized, tick, policy)
            if task_waiting_time < 0:
                print ("\n\nISSUE\n\n")
                print("load: " + str(event.task.vcluster.load))
                raise Exception("Got negative waiting time!")

            task_finish_time = tick + task_waiting_time + event.task.load
            #print ("Registered: finish_time: " + str(task_finish_time) + " waiting_time: " + str(task_waiting_time) + " load: " + str(delivered_task.load))
            seq = next(counter)
            event_entry = [task_finish_time, seq, Event(event_type='finished', vcluster=event.task.vcluster, task=event.task)]
            heappush(event_queue, event_entry)
        
        elif event.type == 'switch_failure':
            if (failure_mode == 'spine'):
                failure_happened = True
                seq = next(counter)
                event_entry = [tick + latency_model.failure_detection_latency, seq, Event(event_type='spine_failure_detected', component_id=event.component_id)]
                heappush(event_queue, event_entry)
            print("Got failure event for spine: " + str(event.component_id) + " Time tick: " + str(event_tick))

        elif event.type == 'spine_failure_detected':
            print("Got failure detected event spine: " + str(event.component_id) + " Time tick: " + str(event_tick))
            failure_detection_time = tick
            for vcluster in affected_vcluster_list:
                print("Affected vcluster: " + str(vcluster.cluster_id))
                num_msg_to_client += vcluster.num_clients
                affected_tor_list.extend(vcluster.tor_id_unique_list)
                for client_index, client_controller_latency in enumerate(vcluster.client_controller_latency):
                    seq = next(counter)
                    event_entry = [tick + client_controller_latency, seq, Event(event_type='failure_notice_client', vcluster=vcluster, component_id=event.component_id, client_id=client_index)]
                    heappush(event_queue, event_entry)
                affected_tor_list = list(set(affected_tor_list))
                seq = next(counter)
                event_entry = [tick + vcluster.max_controller_latency, seq, Event(event_type='vcluster_failover_converged', vcluster=vcluster)]
                heappush(event_queue, event_entry)
    
        elif event.type == 'failure_notice_client':
            print("Got failure notice for client: " + str(event.client_id) + " for vcluster: " + str(event.vcluster.cluster_id) + " Time tick: " + str(event_tick))
            event.vcluster.client_spine_list[event.client_id].remove(event.component_id)

        elif event.type == 'vcluster_failover_converged':
            print("Failover converged for vcluster: " + str(event.vcluster.cluster_id) + " Time tick: " + str(event_tick))
            event.vcluster.failover_converged = True
            event.vcluster.failover_converge_latency = tick - FAILURE_TIME_TICK
            num_converged_vclusters +=1
            if num_converged_vclusters == len(affected_vcluster_list):
                terminate_experiment = True
                break
        
        elapsed_time_log = time.time() - start_time_log
        elapsed_time_imb_measure = tick - start_time_imb_measure
        
        # Measure load imbalance per vcluster at the intervals
        if elapsed_time_imb_measure > LOAD_IMB_MEASURE_INT_TICKS:
            for vcluster in vcluster_list:
                max_load_workers = max(vcluster.queue_lens_workers)
                max_load_tors = max(vcluster.queue_lens_tors)
                avg_load_workers = sum(vcluster.queue_lens_workers) / float(vcluster.num_workers)
                avg_load_tors = sum(vcluster.queue_lens_tors) / float(vcluster.num_tors)
                if avg_load_workers != 0 and max_load_workers>1: # Avoid calculating (large) values when only one task is in workers 
                    vcluster.log_load_imbalance_workers.append(max_load_workers/avg_load_workers)
                if avg_load_tors != 0 and max_load_tors>0:
                    vcluster.log_load_imbalance_tors.append(max_load_tors/avg_load_tors)
                
                sum_intra_rack_imbalances = 0
                max_intra_rack_imbalances = 0
                for tor_id in vcluster.tor_id_unique_list:
                    worker_indices = utils.get_worker_indices_for_tor(tor_id, vcluster.host_list)
                    queue_len_workers_in_rack = [vcluster.queue_lens_workers[i] for i in worker_indices]
                    max_load_workers_in_rack = max(queue_len_workers_in_rack)
                    avg_load_workers_in_rack = sum(queue_len_workers_in_rack) / float(len(queue_len_workers_in_rack))
                    
                    if avg_load_workers_in_rack != 0 and max_load_workers_in_rack > 1: # Avoid calculating (large) values when only one task is in workers 
                        load_imbalance_in_rack = max_load_workers_in_rack / avg_load_workers_in_rack
                        if load_imbalance_in_rack > max_intra_rack_imbalances:
                            max_intra_rack_imbalances = load_imbalance_in_rack
                        sum_intra_rack_imbalances += load_imbalance_in_rack
                    avg_intra_rack_imbalances = sum_intra_rack_imbalances / vcluster.num_tors

                vcluster.log_load_imbalance_intra_rack_mean.append(avg_intra_rack_imbalances)
                vcluster.log_load_imbalance_intra_rack_max.append(max_intra_rack_imbalances)

            start_time_imb_measure = tick

        # Produce log message about the progress of simulation at the intervals
        if elapsed_time_log > LOG_PROGRESS_INTERVAL:
            log_handler_dcn.debug(policy_file_tag + ' progress log @' + str(sys_load) + ' Ticks passed: ' + str(tick) + ' Events processed: ' + str(event_count) + ' Clusters done: ' + str(cluster_terminate_count))
            msg_per_sec_spine, msg_per_sec_spine_idle_remove, msg_per_sec_spine_idle_signal, msg_per_sec_spine_load_signal, task_per_sec_tor, task_per_sec_spine =  get_dcn_results(tick, num_msg_spine, num_msg_spine_idle_remove, num_msg_spine_idle_signal, num_msg_spine_load_signal, num_task_tor, num_task_spine)
            
            if failure_mode == 'spine':
                failed_tasks = [vcluster.num_failed_tasks for vcluster in affected_vcluster_list]
                scheduled_tasks = [vcluster.num_scheduled_tasks for vcluster in affected_vcluster_list]
                converge_latency = [vcluster.failover_converge_latency for vcluster in affected_vcluster_list]
                affected_clients = [vcluster.num_clients for vcluster in affected_vcluster_list]
                log_handler_dcn.info(policy_file_tag + ' num_failed_tasks @' + str(sys_load) + ' :' +  str(pd.Series(failed_tasks).describe()))
                log_handler_dcn.info(policy_file_tag + ' num_scheduled_tasks @' + str(sys_load) + ' :' +  str(pd.Series(scheduled_tasks).describe()))

            # for vcluster in vcluster_list:
            #     print ("vcluster " + str(vcluster.cluster_id) + " msg_sq: " + str(vcluster.log_msg_sq))
            #     print ("vcluster " + str(vcluster.cluster_id) + " log_msg_iq_sample: " + str(vcluster.log_msg_iq_sample))
            #     print ("vcluster " + str(vcluster.cluster_id) + " log_msg_iq_link: " + str(vcluster.log_msg_iq_link))
            #     print ("vcluster " + str(vcluster.cluster_id) + " log_msg_other: " + str(vcluster.log_msg_other))

            log_handler_dcn.info(policy_file_tag + ' task_per_sec_spine @' + str(sys_load) + ':\n' +  str(pd.Series(task_per_sec_spine).describe()))
            log_handler_dcn.info(policy_file_tag + ' task_per_sec_tor @' + str(sys_load) + ':\n' +  str(pd.Series(task_per_sec_tor).describe()))
            log_handler_dcn.info(policy_file_tag + ' msg_per_sec_spine @' + str(sys_load) + ':\n' +  str(pd.Series(msg_per_sec_spine).describe()))
            
            start_time_log = time.time()
            if terminate_experiment:
                break

    if failure_mode == 'spine':
        failed_tasks = [vcluster.num_failed_tasks for vcluster in affected_vcluster_list]
        scheduled_tasks = [vcluster.num_scheduled_tasks for vcluster in affected_vcluster_list]
        converge_latency = [vcluster.failover_converge_latency for vcluster in affected_vcluster_list]
        affected_clients = [vcluster.num_clients for vcluster in affected_vcluster_list]

        utils.write_to_file(result_dir, 'num_failed_tasks', policy_file_tag, sys_load, task_distribution_name, failed_tasks, run_id, is_colocate=is_colocate)
        utils.write_to_file(result_dir, 'num_scheduled_tasks', policy_file_tag, sys_load, task_distribution_name, scheduled_tasks, run_id, is_colocate=is_colocate)
        utils.write_to_file(result_dir, 'converge_latency', policy_file_tag, sys_load, task_distribution_name, converge_latency, run_id, is_colocate=is_colocate)
        utils.write_to_file(result_dir, 'affected_tors', policy_file_tag, sys_load, task_distribution_name, affected_tor_list, run_id, is_colocate=is_colocate)
        utils.write_to_file(result_dir, 'affected_clients', policy_file_tag, sys_load, task_distribution_name, affected_clients, run_id, is_colocate=is_colocate)
    
    else:
        for p in range(101):
            wait_times_percentiles = []
            response_times_percentiles = []
            worker_load_imbalance_percentiles = []
            tor_load_imbalance_percentiles = []
            intra_rack_load_imbalance_max_percentiles = []

            for vcluster in vcluster_list:
                wait_times_percentiles.append(np.percentile(vcluster.log_task_wait_time[vcluster.num_workers:], p))
                response_times_percentiles.append(np.percentile(vcluster.log_response_time[vcluster.num_workers:], p))
                
                if p==1 or p == 25 or p==50 or p==75 or p==99 or p==100:
                    if len(vcluster.log_load_imbalance_workers) > 0:
                        worker_load_imbalance_percentiles.append(np.percentile(vcluster.log_load_imbalance_workers, p))
                    if len(vcluster.log_load_imbalance_tors) > 0:
                        tor_load_imbalance_percentiles.append(np.percentile(vcluster.log_load_imbalance_tors, p))
                    if len(vcluster.log_load_imbalance_intra_rack_max) > 0:
                        intra_rack_load_imbalance_max_percentiles.append(np.percentile(vcluster.log_load_imbalance_intra_rack_max, p))
            
            if p==1 or p == 25 or p==50 or p==75 or p==99 or p==100:    
                utils.write_to_file(result_dir + '/analysis/', 'p' + str(p) +'_load_imb_workers',policy_file_tag, sys_load, vcluster.task_distribution_name,  worker_load_imbalance_percentiles, run_id, is_colocate=is_colocate, append=True)
                utils.write_to_file(result_dir + '/analysis/', 'p' + str(p) +'_load_imb_tors',policy_file_tag, sys_load, vcluster.task_distribution_name,  tor_load_imbalance_percentiles, run_id, is_colocate=is_colocate, append=True)
                utils.write_to_file(result_dir + '/analysis/', 'p' + str(p) +'_intra_rack_load_imb_max',policy_file_tag, sys_load, vcluster.task_distribution_name,  intra_rack_load_imbalance_max_percentiles, run_id, is_colocate=is_colocate, append=True)

            utils.write_to_file(result_dir + '/analysis/', 'p' + str(p) +'_wait_times', policy_file_tag, sys_load, vcluster.task_distribution_name,  wait_times_percentiles, run_id, is_colocate=is_colocate, append=True)
            utils.write_to_file(result_dir + '/analysis/', 'p' + str(p) +'_response_times', policy_file_tag, sys_load, vcluster.task_distribution_name,  response_times_percentiles, run_id, is_colocate=is_colocate, append=True)
            
        response_times_mean = []
        wait_times_mean = []
        zero_wait_fraction = []
        worker_load_imbalance_mean = []
        tor_load_imbalance_mean = []
        intra_rack_load_imbalance_mean = []
        intra_rack_max_load_imbalance_mean = []

        for vcluster in vcluster_list:
            response_times_mean.append(np.mean(vcluster.log_response_time[vcluster.num_workers:]))
            wait_times_mean.append(np.mean(vcluster.log_task_wait_time[vcluster.num_workers:]))
            zero_wait_fraction.append(float(vcluster.log_zero_wait_tasks) / len(vcluster.task_distribution))
            worker_load_imbalance_mean.append(np.mean(vcluster.log_load_imbalance_workers))
            tor_load_imbalance_mean.append(np.mean(vcluster.log_load_imbalance_tors))
            intra_rack_load_imbalance_mean.append(np.mean(vcluster.log_load_imbalance_intra_rack_mean))
            intra_rack_max_load_imbalance_mean.append(np.mean(vcluster.log_load_imbalance_intra_rack_max))

        utils.write_to_file(result_dir + '/analysis/', 'mean_wait_times', policy_file_tag, sys_load, vcluster.task_distribution_name,  wait_times_mean, run_id, is_colocate=is_colocate, append=True)
        utils.write_to_file(result_dir + '/analysis/', 'mean_response_times', policy_file_tag, sys_load, vcluster.task_distribution_name,  response_times_mean, run_id, is_colocate=is_colocate, append=True)
        utils.write_to_file(result_dir + '/analysis/', 'zero_wait_frac', policy_file_tag, sys_load, vcluster.task_distribution_name,  zero_wait_fraction, run_id, is_colocate=is_colocate, append=True)
        utils.write_to_file(result_dir + '/analysis/', 'mean_load_imb_workers', policy_file_tag, sys_load, vcluster.task_distribution_name,  worker_load_imbalance_mean, run_id, is_colocate=is_colocate, append=True)
        utils.write_to_file(result_dir + '/analysis/', 'mean_load_imb_tors', policy_file_tag, sys_load, vcluster.task_distribution_name,  tor_load_imbalance_mean, run_id, is_colocate=is_colocate, append=True)
        utils.write_to_file(result_dir + '/analysis/', 'mean_load_imb_intra_rack', policy_file_tag, sys_load, vcluster.task_distribution_name,  intra_rack_load_imbalance_mean, run_id, is_colocate=is_colocate, append=True)
        utils.write_to_file(result_dir + '/analysis/', 'mean_load_imb_intra_rack_max', policy_file_tag, sys_load, vcluster.task_distribution_name,  intra_rack_max_load_imbalance_mean, run_id, is_colocate=is_colocate, append=True)

if __name__ == "__main__":
    arguments = docopt.docopt(__doc__, version='1.0')
    working_dir = arguments['-d']
    # global result_dir
    result_dir = working_dir
    policy = arguments['-p']
    load = float(arguments['-l'])
    k_value = int(arguments['-k'])
    spine_ratio = int(arguments['-r'])
    run_id = int(arguments['-i'])
    task_distribution_name = arguments['-t']
    failure_mode = arguments['-f']
    failed_switch_id = arguments.get('--fid', -1)
    is_centralized = arguments.get('--centralized')
    if failed_switch_id:
        failed_switch_id = int(arguments.get('--fid', -1))

    hop_delay = arguments.get('--delay')
    if hop_delay:
        utils.PER_HOP_LATENCY = int(arguments.get('--delay'))
    loss_prob = arguments.get('--loss')
    if loss_prob:
        utils.LOSS_PROBABILITY = float(arguments.get('--loss'))

    print (utils.LOSS_PROBABILITY)
    print(utils.PER_HOP_LATENCY)

    is_colocate = arguments.get('--colocate', False)
    delayed_updates = arguments.get('--du', True)
    save_all_results = arguments.get('--all', False)

    print(policy)
    print(save_all_results)
    
    data = utils.read_dataset(working_dir, is_colocate)
    run_scheduling(policy, data, k_value, task_distribution_name, load, spine_ratio, run_id, failure_mode, is_colocate, failed_switch_id, expon_arrival=True, is_centralized=is_centralized, delayed_updates=delayed_updates, save_all_results=save_all_results)

