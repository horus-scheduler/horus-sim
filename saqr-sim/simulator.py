"""Usage:
simulator.py -d <working_dir> -p <policy> -l <load> -k <k_value> -r <spine_ratio>  -t <task_distribution> -i <id> -f <failure_mode> [--fid <failed_switch_id>] [--colocate] [--centralized] [--du] [--all]

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

import utils as utils
from vcluster import VirtualCluster, Event
from task import Task
from latency_model import LatencyModel
from spine_selector import SpineSelector

LOG_PROGRESS_INTERVAL = 900 # Dump some progress info periodically (in seconds)
result_dir = "./"
FAILURE_TIME_TICK = 100

counter = itertools.count()     # unique sequence count
event_queue = []

def report_cluster_results(log_handler, policy_file_tag, sys_load, vcluster, run_id, is_colocate=False, save_all_results=False):
    log_handler.info(policy_file_tag + ' Finished cluster with ID:' + str(vcluster.cluster_id) +' wait_times @' + str(sys_load) + ':\n' +  str(pd.Series(vcluster.log_task_wait_time).describe()))
    log_handler.info(policy_file_tag + ' Finished cluster with ID:' + str(vcluster.cluster_id) +' response_times @' + str(sys_load) + ':\n' +  str(pd.Series(vcluster.log_response_time).describe()))
    

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


def jiq_idle_process(vcluster, num_msg_spine, k, worker_idx, tor_idx, is_centralized):
    min_idle_queue = float("inf")
    if is_centralized:
        sample_indices = random.sample(range(0, vcluster.num_spines), min(k, vcluster.num_spines)) # Sample k spines
        #print sample_indices
        for idx in sample_indices:  # Find the sampled spine with min idle queue len
            sampled_value = len(vcluster.idle_queue_spine[idx])
            sampled_spine_id = vcluster.selected_spine_list[idx]
            if len(sample_indices) > 1: # Probe msg is required only if there is more than one spine scheduler
                num_msg_spine[sampled_spine_id] += 1   # total k msgs for sampling spine idle queues
            if sampled_value < min_idle_queue:
                min_idle_queue = sampled_value
                target_spine_idx = idx
        vcluster.idle_queue_spine[target_spine_idx].append(worker_idx) # Add ToR to the idle queue of selected spine
        target_spine_id = vcluster.selected_spine_list[target_spine_idx]
        num_msg_spine[target_spine_id] += 1 # 1 msg for updating spine idle queue 
    else:
        if len(vcluster.idle_queue_tor[tor_idx])==1: # Tor just became aware of idle workers and add itself to a spine
            sample_indices = random.sample(range(0, vcluster.num_spines), min(k, vcluster.num_spines)) # Sample k spines
            #target_spine_idx = random.choice(range(0, vcluster.num_spines))

            for idx in sample_indices:  # Find the sampled spine with min idle queue len
                sampled_value = len(vcluster.idle_queue_spine[idx])
                sampled_spine_id = vcluster.selected_spine_list[idx]

                num_msg_spine[sampled_spine_id] += 1   # total k msgs for sampling spine idle queues
                if sampled_value < min_idle_queue:
                    min_idle_queue = sampled_value
                    target_spine_idx = idx
            vcluster.idle_queue_spine[target_spine_idx].append(tor_idx) # Add ToR to the idle queue of selected spine
            target_spine_id = vcluster.selected_spine_list[target_spine_idx]
            num_msg_spine[target_spine_id] += 1 # 1 msg for updating spine idle queue
        
        vcluster.idle_queue_tor[tor_idx].append(worker_idx) # Add idle worker to idle queue of ToR
        tor_id = vcluster.tor_id_unique_list[tor_idx]
    
    return vcluster, num_msg_spine


def adaptive_idle_process(vcluster, num_msg_spine, k, worker_idx, tor_idx, is_centralized):
    k = 2
    # In centralized simulations idle process for idle server in adaptive is identical to jiq
    if is_centralized:
       return jiq_idle_process(vcluster, num_msg_spine, k, worker_idx, tor_idx, is_centralized)
    else:
        if worker_idx not in vcluster.idle_queue_tor[tor_idx]:
            vcluster.idle_queue_tor[tor_idx].append(worker_idx)

        if vcluster.tor_idle_link[tor_idx] == -1: # Tor just became aware of idle workers and not already linked to a spine
            sample_indices = random.sample(range(0, vcluster.num_spines), min(k, vcluster.num_spines)) # Sample k dispatchers
            #target_spine_idx = random.choice(range(0, vcluster.num_spines))
            # for spine_idx, idle_tors in enumerate(vcluster.idle_queue_spine):
            #     if tor_idx in idle_tors:   # Tor was previously presented as idle to one of spines
            #         print ("BUG! Idle inkage while already linked!")
            #         print (len(vcluster.idle_queue_tor[tor_idx]))
                    
            min_idle_queue = float("inf")
            for idx in sample_indices:  # Find the sampled spine with min idle queue len (k msgs)
                sampled_value = len(vcluster.idle_queue_spine[idx])
                sampled_spine_id = vcluster.selected_spine_list[idx]

                num_msg_spine[sampled_spine_id] += 1
                vcluster.log_msg_iq_sample += 1
                if sampled_value < min_idle_queue:
                    min_idle_queue = sampled_value
                    target_spine_idx = idx

            # Add tor to the idle queue of that spine (1 msg)
            vcluster.idle_queue_spine[target_spine_idx].append(tor_idx) 
            vcluster.tor_idle_link[tor_idx] = target_spine_idx # New linkage value
            target_spine_id = vcluster.selected_spine_list[target_spine_idx]
            num_msg_spine[target_spine_id] += 1 # for updating the spine idle queue
            vcluster.log_msg_iq_link += 1
    return  vcluster, num_msg_spine

def handle_task_done(
    finished_task,
    tick,
    num_msg_spine=None,
    k=2,
    is_centralized=False):
    
    i = finished_task.target_worker
    vcluster = finished_task.vcluster

    #  finished executing task
    
    vcluster.task_lists[i].pop(0)        # Remove from list
    vcluster.queue_lens_workers[i] = len(vcluster.task_lists[i])       # Decrement worker queue len

    tor_id = utils.get_tor_id_for_host(vcluster.host_list[i])
    # Conversion for mapping to cluster's local lists
    tor_idx = finished_task.target_tor

    vcluster.queue_lens_tors[tor_idx] = utils.calculate_tor_queue_len(tor_id, vcluster.queue_lens_workers, vcluster.host_list)

    if vcluster.queue_lens_workers[i] != 0: # Not idle after this event, another task will start on worker
        vcluster.curr_task_start_time[i] = tick

    if (vcluster.policy == 'pow_of_k') or (vcluster.policy == 'pow_of_k_partitioned'): # Random and JIQ do not use this part
        if vcluster.policy == 'pow_of_k':
            # Update ToR queue len at all of the spines
            for spine_id in vcluster.selected_spine_list:
                num_msg_spine[spine_id] += 1 
        else: # Only update the designated spine
            mapped_spine_idx = vcluster.tor_spine_map[tor_idx]
            mapped_spine_id = vcluster.selected_spine_list[mapped_spine_idx]
            num_msg_spine[mapped_spine_id] += 1
    
    else: #JIQ and adaptive
        if vcluster.policy == 'jiq': # JIQ
            if vcluster.queue_lens_workers[i] == 0: # Process for when a server becomes idle 
                vcluster, num_msg_spine = jiq_idle_process(
                    vcluster, 
                    num_msg_spine,
                    k,
                    i,
                    tor_idx,
                    is_centralized)
        elif vcluster.policy == 'adaptive': # Adaptive
            # Process for event that a server becomes idle 
            if vcluster.queue_lens_workers[i] == 0:
                vcluster, num_msg_spine = adaptive_idle_process(
                    vcluster,
                    num_msg_spine,
                    k,
                    i,
                    tor_idx,
                    is_centralized)

            if not is_centralized:
                # ToR that is paired with a spine, will update the signal 
                linked_spine_idx = vcluster.tor_spine_map[tor_idx]
                # Design for reducing for msg rate: Update spine switch view only if the state is drifted more than "1" !
                if abs(vcluster.queue_lens_tors[tor_idx] - vcluster.known_queue_len_spine[linked_spine_idx][tor_idx]) >= 1:
                    vcluster.known_queue_len_spine[linked_spine_idx].update({tor_idx: vcluster.queue_lens_tors[tor_idx]}) # Update SQ signals
                    spine_id = vcluster.selected_spine_list[linked_spine_idx]
                    num_msg_spine[spine_id] += 1
                    vcluster.log_msg_sq += 1
    return num_msg_spine

def schedule_task_random_pow_of_k(new_task, k, target_spine): 
    vcluster = new_task.vcluster
    queue_lens_workers = vcluster.queue_lens_workers
    target_tor = random.randrange(vcluster.num_tors) # Randomly select one leaf scheduler
    
    worker_indices = utils.get_worker_indices_for_tor(vcluster.tor_id_unique_list[target_tor], vcluster.host_list)
    min_load = float("inf")
    num_samples = k
    if len(worker_indices) < k:
        num_samples = len(worker_indices)

    sample_indices = random.sample(worker_indices, num_samples) # Sample from workers connected to that ToR

    for idx in sample_indices:
        sample = queue_lens_workers[idx]
        if sample < min_load:
            min_load = sample
            target_worker = idx

    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task

def schedule_task_central_queue(new_task, target_spine_id, target_spine_idx, spine_falcon_used_slots):
    vcluster = new_task.vcluster
    if (spine_falcon_used_slots[target_spine_id] >= utils.FALCON_QUEUE_SLOTS):
        return -1, spine_falcon_used_slots
    vcluster.falcon_queue.append(new_task)
    spine_falcon_used_slots[target_spine_id] += 1
    return 0, spine_falcon_used_slots

def schedule_task_pow_of_k(new_task, k, target_spine, is_centralized):
    vcluster = new_task.vcluster
    num_spines = vcluster.num_spines
    num_tors = vcluster.num_tors
    num_workers = vcluster.num_workers
    queue_lens_tors = vcluster.queue_lens_tors
    queue_lens_workers = vcluster.queue_lens_workers
    
    if is_centralized:
        worker_indices = range(0, vcluster.num_workers)
    else:
        # Select ToR
        min_load = float("inf")
        num_samples = k
        if num_tors < k:
            num_samples = num_tors
        sample_indices = random.sample(range(0, num_tors), num_samples) # Info about all tors available at every spine
        for idx in sample_indices:
            sample = queue_lens_tors[idx]
            if sample < min_load:
                min_load = sample
                target_tor = idx

        worker_indices = utils.get_worker_indices_for_tor(vcluster.tor_id_unique_list[target_tor], vcluster.host_list)
    
    # Select worker
    min_load = float("inf")
    num_samples = k
    if len(worker_indices) < k:
        num_samples = len(worker_indices)

    sample_indices = random.sample(worker_indices, num_samples) # Sample from workers connected to that ToR

    for idx in sample_indices:
        sample = queue_lens_workers[idx]
        if sample < min_load:
            min_load = sample
            target_worker = idx

    # In centralized scenario, the decision is worker-based so we drive the ToR based on worker for our simulation calculations only
    if is_centralized: 
        target_tor = vcluster.tor_id_unique_list.index(utils.get_tor_id_for_host(vcluster.host_list[target_worker]))

    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task

def schedule_task_pow_of_k_partitioned(new_task, k, target_spine):
    vcluster = new_task.vcluster
    num_spines = vcluster.num_spines
    num_tors = vcluster.num_tors
    num_workers = vcluster.num_workers
    queue_lens_tors = vcluster.queue_lens_tors
    queue_lens_workers = vcluster.queue_lens_workers

    # Make decision at Spine level:
    min_load = float("inf")

    mapped_tor_list = new_task.vcluster.spine_tor_map[target_spine]
    
    num_samples = k
    if len(mapped_tor_list) < k:
        num_samples = len(mapped_tor_list)

    sample_indices = random.sample(mapped_tor_list, num_samples) # k samples from tors available to that spine

    for idx in sample_indices:
        sample = queue_lens_tors[idx]
        if sample < min_load:
            min_load = sample
            target_tor = idx
    if min_load == float("inf"):
        log_handler_system.error(queue_lens_tors)
        log_handler_system.error(new_task.vcluster.spine_tor_map)

    # Make the decision at ToR:
    min_load = float("inf")
    worker_indices = utils.get_worker_indices_for_tor(vcluster.tor_id_unique_list[target_tor], vcluster.host_list)
    num_samples = k
    if len(worker_indices) < k:
        num_samples = len(worker_indices)

    sample_indices = random.sample(worker_indices, num_samples) # Sample from workers connected to that ToR
    for idx in sample_indices:
        sample = queue_lens_workers[idx]
        if sample < min_load:
            min_load = sample
            target_worker = idx
    
    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task

def schedule_task_jiq(new_task, num_msg_spine, target_spine, is_centralized):
    if is_centralized:
        if new_task.vcluster.idle_queue_spine[target_spine]: # Spine scheduler is aware of some idle workers
            target_worker = new_task.vcluster.idle_queue_spine[target_spine].pop(0)
        else:
            worker_indices = range(0, new_task.vcluster.num_workers)
            target_worker = random.choice(worker_indices)

        target_tor = new_task.vcluster.tor_id_unique_list.index(utils.get_tor_id_for_host(new_task.vcluster.host_list[target_worker]))
    else:
        # Make decision at spine level:
        if new_task.vcluster.idle_queue_spine[target_spine]:  # Spine is aware of some tors with idle wokrers
            target_tor = new_task.vcluster.idle_queue_spine[target_spine][0]
            new_task.decision_tag = 0
        else:   # No tor with idle worker is known, dispatch to a random tor
            #target_tor = random.choice(get_tor_partition_range_for_spine(target_spine)) Limit to pod
            target_tor = nr.randint(0, new_task.vcluster.num_tors) # Can forward to any ToR
            new_task.decision_tag = 2

        if new_task.vcluster.idle_queue_tor[target_tor]: # Tor is aware of some idle workers
            target_worker = new_task.vcluster.idle_queue_tor[target_tor].pop(0)
        else:
            worker_indices = utils.get_worker_indices_for_tor(new_task.vcluster.tor_id_unique_list[target_tor], new_task.vcluster.host_list)
            target_worker = random.choice(worker_indices)
            if target_worker in new_task.vcluster.idle_queue_tor[target_tor]:
                new_task.vcluster.idle_queue_tor[target_tor].remove(target_worker)

        for spine_idx, idle_tors in enumerate(new_task.vcluster.idle_queue_spine):
            if target_tor in idle_tors:   # Tor was previously presented as idle to one of spines
                if len(new_task.vcluster.idle_queue_tor[target_tor]) == 0:
                    new_task.vcluster.idle_queue_spine[spine_idx].remove(target_tor)
                    spine_id = new_task.vcluster.selected_spine_list[spine_idx]
                    num_msg_spine[spine_id] += 1

    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task, num_msg_spine

def schedule_task_adaptive(new_task, k, num_msg_spine, target_spine, is_centralized):
    partition_size_spine = new_task.vcluster.partition_size
    vcluster = new_task.vcluster
    if is_centralized:
        
        num_spines = vcluster.num_spines
        num_workers = vcluster.num_workers
        queue_lens_workers = vcluster.queue_lens_workers
        # Make decision at spine layer:
        min_load = float("inf")
        if len(new_task.vcluster.idle_queue_spine[target_spine]) > 0:  # Spine is aware of idle workers
            target_worker = new_task.vcluster.idle_queue_spine[target_spine].pop(0)
            new_task.decision_tag = 0
        else:   # No idle worker is known do pow-of-k
            min_load = float("inf")
            num_samples = k
            if num_workers < k:
                num_samples = num_workers
            sample_indices = random.sample(range(0, vcluster.num_workers), num_samples) 
            for idx in sample_indices:
                sample = queue_lens_workers[idx]
                if sample < min_load:
                    min_load = sample
                    target_worker = idx
        target_tor = new_task.vcluster.tor_id_unique_list.index(utils.get_tor_id_for_host(new_task.vcluster.host_list[target_worker]))
    else:
        target_spine_id = new_task.vcluster.selected_spine_list[target_spine]
        # Make decision at spine layer:
        min_load = float("inf")
        if len(new_task.vcluster.idle_queue_spine[target_spine]) > 0:  # Spine is aware of some tors with idle servers
            idle_index = random.choice(range(len(new_task.vcluster.idle_queue_spine[target_spine])))
            target_tor = new_task.vcluster.idle_queue_spine[target_spine][idle_index]
            new_task.decision_tag = 0
        else:   # No tor with idle server is known
            if (len(new_task.vcluster.known_queue_len_spine[target_spine]) > 2): # Do shortest queue if enough info available    
                num_samples = k
                if len(new_task.vcluster.known_queue_len_spine[target_spine]) < k:
                    num_samples = len(new_task.vcluster.known_queue_len_spine[target_spine])

                sample_tors = random.sample(list(new_task.vcluster.known_queue_len_spine[target_spine]), num_samples) # k samples from ToR queue lenghts available to that spine
                #print (sample_workers)
                for tor_idx in sample_tors:
                    sample_queue_len = new_task.vcluster.known_queue_len_spine[target_spine][tor_idx]
                    if sample_queue_len < min_load:
                        min_load = sample_queue_len
                        target_tor = tor_idx
                new_task.decision_tag = 1 # shortest-queue-based decision

            else: # Randomly select a ToR from all of the available tors
                target_tor = nr.randint(0, new_task.vcluster.num_tors)
                new_task.decision_tag = 2 # Random-based decision

        if len(new_task.vcluster.idle_queue_tor[target_tor]) > 0:  # Tor is aware of some idle workers
            target_worker = new_task.vcluster.idle_queue_tor[target_tor].pop(0)

        else: # No idle worker

            min_load = float("inf")
            worker_indices = utils.get_worker_indices_for_tor(new_task.vcluster.tor_id_unique_list[target_tor], new_task.vcluster.host_list)
            num_samples = k
            if len(worker_indices) < k:
                num_samples = len(worker_indices)
            sample_indices = random.sample(worker_indices, num_samples) # Sample from workers connected to that ToR

            for idx in sample_indices:
                sample = new_task.vcluster.queue_lens_workers[idx]
                if sample < min_load:
                    min_load = sample
                    target_worker = idx

        if len(new_task.vcluster.idle_queue_tor[target_tor]) == 0: # Rack is not idle anymore
            linked_spine_idx = new_task.vcluster.tor_idle_link[target_tor]
            if (linked_spine_idx != -1): # Tor linked with one of spines (spine thinks it's idle)
                new_task.vcluster.idle_queue_spine[linked_spine_idx].remove(target_tor)
                new_task.vcluster.tor_idle_link[target_tor] = -1 # Tor removed linkage
                spine_id = new_task.vcluster.selected_spine_list[linked_spine_idx]
                num_msg_spine[spine_id] += 1 # "Remove" msg from tor
                new_task.vcluster.log_msg_other += 1
    
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

    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task, num_msg_spine

def update_switch_views(scheduled_task, num_msg_spine, is_centralized):
    scheduled_task.vcluster.queue_lens_workers[scheduled_task.target_worker] += 1   
    if not is_centralized:
        scheduled_task.vcluster.queue_lens_tors[scheduled_task.target_tor] = utils.calculate_tor_queue_len(
            scheduled_task.global_tor_id,
            scheduled_task.vcluster.queue_lens_workers,
            scheduled_task.vcluster.host_list
        )
        if scheduled_task.vcluster.policy == 'adaptive':
            if (scheduled_task.target_tor in scheduled_task.vcluster.spine_tor_map[scheduled_task.first_spine]): # If spine knows the queue len of this tor, it will increment it
                scheduled_task.vcluster.known_queue_len_spine[scheduled_task.first_spine][scheduled_task.target_tor] += (1.0 / scheduled_task.vcluster.workers_per_tor[scheduled_task.target_tor])
            else:
                linked_spine_idx = scheduled_task.vcluster.tor_spine_map[scheduled_task.target_tor]
                if abs(scheduled_task.vcluster.queue_lens_tors[scheduled_task.target_tor] - scheduled_task.vcluster.known_queue_len_spine[linked_spine_idx][scheduled_task.target_tor]) >= 1:
                    scheduled_task.vcluster.known_queue_len_spine[linked_spine_idx].update({scheduled_task.target_tor: scheduled_task.vcluster.queue_lens_tors[scheduled_task.target_tor]}) # Update SQ signals
                    spine_id = scheduled_task.vcluster.selected_spine_list[linked_spine_idx]
                    num_msg_spine[spine_id] += 1
                    scheduled_task.vcluster.log_msg_sq += 1
        elif scheduled_task.vcluster.policy == 'pow_of_k': # Need one msg to all spine schedulers to update the view (except the spine that made the scheduling decision)
            for spine_idx in range(len(scheduled_task.vcluster.selected_spine_list)):
                if spine_idx != scheduled_task.first_spine: # All spine schedulers except the one that received this task initially need updates
                    spine_id = scheduled_task.vcluster.selected_spine_list[spine_idx] # Find global Spine switch ID
                    num_msg_spine[spine_id] += 1
    return num_msg_spine

def get_dcn_results(tick, num_msg_spine, num_task_tor, num_task_spine):
    exp_duration_s = float(tick) / (10**9)
    msg_per_sec_spine = [x / exp_duration_s for x in num_msg_spine]
    task_per_sec_tor = [x / exp_duration_s for x in num_task_tor]
    task_per_sec_spine = [x / exp_duration_s for x in num_task_spine]
    return msg_per_sec_spine, task_per_sec_tor, task_per_sec_spine

def handle_task_delivered(event, is_centralized, tick, policy):
    delivered_task = event.task

    running_task_passed = 0 # Calculates amount of time passed for the task that is currently running
    if len(delivered_task.vcluster.task_lists[delivered_task.target_worker]) == 0: 
        delivered_task.vcluster.curr_task_start_time[delivered_task.target_worker] = tick
    running_task_passed = tick - delivered_task.vcluster.curr_task_start_time[delivered_task.target_worker]

    if policy != 'central_queue': # Task (will) wait in worker queue: should wait as long as pending tasks at worker
        task_waiting_time = np.sum(delivered_task.vcluster.task_lists[delivered_task.target_worker]) - running_task_passed
        task_response_time = task_waiting_time + delivered_task.load + (tick - delivered_task.arrive_time)
    else:
        task_waiting_time = tick - delivered_task.arrive_time # Task waited in scheduler queue
        task_response_time = task_waiting_time + delivered_task.load
    
    if task_waiting_time == 0:
        delivered_task.vcluster.log_zero_wait_tasks += 1
    
    delivered_task.vcluster.log_total_tasks += 1

    delivered_task.vcluster.log_task_wait_time.append(task_waiting_time) 
    delivered_task.vcluster.log_response_time.append(task_response_time) # Wait
    
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
    
    latency_model = LatencyModel(result_dir)
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

    start_time = time.time()

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
            new_task = Task(load, vcluster, tick)
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
                    scheduled_task = schedule_task_random_pow_of_k(new_task, k, spine_shched_index)
                
                elif vcluster.policy == 'central_queue':
                    is_failed, spine_falcon_used_slots = schedule_task_central_queue(new_task, spine_sched_id, spine_shched_index, spine_falcon_used_slots)
                    if is_failed:
                        vcluster.num_failed_tasks += 1
                        print ("Failed tasks: " + str(vcluster.num_failed_tasks))
                    scheduled_task = new_task
                    scheduled_task.set_decision(0, 0, 0) # Dummy 
                elif vcluster.policy == 'pow_of_k':
                    scheduled_task = schedule_task_pow_of_k(new_task, k, spine_shched_index, is_centralized)
                    
                elif vcluster.policy == 'pow_of_k_partitioned':
                    scheduled_task = schedule_task_pow_of_k_partitioned(new_task, k, spine_shched_index)

                elif vcluster.policy == 'jiq':
                    scheduled_task, num_msg_spine = schedule_task_jiq(
                        new_task, 
                        num_msg_spine, 
                        spine_shched_index,
                        is_centralized)

                elif vcluster.policy == 'adaptive':
                    scheduled_task, num_msg_spine = schedule_task_adaptive(
                        new_task,
                        k,
                        num_msg_spine, 
                        spine_shched_index,
                        is_centralized)

                #print(new_task.vcluster.queue_lens_tors)

                num_task_spine[spine_sched_id] += 1
                num_task_tor[scheduled_task.global_tor_id] += 1
                if not delayed_updates:
                    num_msg_spine = update_switch_views(scheduled_task, num_msg_spine, is_centralized)
            
                if policy != 'central_queue':
                    # Trigger two future events (1) task delivered to worker (2) next task arrive at scheduler
                    seq = next(counter)
                    event_entry = [tick + scheduled_task.network_time, seq, Event(event_type='delivered', vcluster=vcluster, task=scheduled_task)]
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
            else:
                cluster_terminate_count += 1
                report_cluster_results(log_handler_experiment, policy_file_tag, sys_load, vcluster, run_id, is_colocate, save_all_results)
                # Report these metrics for the period that all vclusters are running
                if (cluster_terminate_count==1):
                    msg_per_sec_spine, task_per_sec_tor, task_per_sec_spine = get_dcn_results(tick, num_msg_spine, num_task_tor, num_task_spine)
                    utils.write_to_file(result_dir + '/analysis/', 'task_per_sec_tor', policy_file_tag, sys_load, task_distribution_name, task_per_sec_tor, run_id, is_colocate=is_colocate)
                    utils.write_to_file(result_dir + '/analysis/', 'task_per_sec_spine', policy_file_tag, sys_load, task_distribution_name, task_per_sec_spine, run_id, is_colocate=is_colocate)
                    if policy != 'random':
                        utils.write_to_file(result_dir + '/analysis/', 'msg_per_sec_spine', policy_file_tag, sys_load, task_distribution_name, msg_per_sec_spine, run_id, is_colocate=is_colocate)

        elif event.type == 'finished':
            num_msg_spine = handle_task_done(
                    finished_task=event.task,
                    tick=tick,
                    num_msg_spine=num_msg_spine,
                    k=k, 
                    is_centralized=is_centralized)
            
            if event.task.vcluster.policy == 'central_queue':
                seq = next(counter) # After task is done Falcon sends a retrive packet to scheduler
                event_entry = [tick + latency_model.get_one_way_latency(), seq, Event(event_type='falcon_retrive', vcluster=event.task.vcluster, component_id=event.task.target_worker)]
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
        
        elapsed_time = time.time() - start_time
        
        if elapsed_time > LOG_PROGRESS_INTERVAL:
            log_handler_dcn.debug(policy_file_tag + ' progress log @' + str(sys_load) + ' Ticks passed: ' + str(tick) + ' Events processed: ' + str(event_count) + ' Clusters done: ' + str(cluster_terminate_count))
            msg_per_sec_spine, task_per_sec_tor, task_per_sec_spine =  get_dcn_results(tick, num_msg_spine, num_task_tor, num_task_spine)
            
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
            
            start_time = time.time()
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
            for vcluster in vcluster_list:
                wait_times_percentiles.append(np.percentile(vcluster.log_task_wait_time[vcluster.num_workers:], p))
                response_times_percentiles.append(np.percentile(vcluster.log_response_time[vcluster.num_workers:], p))
            utils.write_to_file(result_dir + '/analysis/', 'p' + str(p) +'_wait_times', policy_file_tag, sys_load, vcluster.task_distribution_name,  wait_times_percentiles, run_id, is_colocate=is_colocate)
            utils.write_to_file(result_dir + '/analysis/', 'p' + str(p) +'_response_times', policy_file_tag, sys_load, vcluster.task_distribution_name,  response_times_percentiles, run_id, is_colocate=is_colocate)
        
        response_times_mean = []
        wait_times_mean = []
        zero_wait_fraction = []
        for vcluster in vcluster_list:
            response_times_mean.append(np.mean(vcluster.log_response_time[vcluster.num_workers:]))
            wait_times_mean.append(np.mean(vcluster.log_task_wait_time[vcluster.num_workers:]))
            zero_wait_fraction.append(float(vcluster.log_zero_wait_tasks) / len(vcluster.task_distribution))

        utils.write_to_file(result_dir + '/analysis/', 'mean_wait_times', policy_file_tag, sys_load, vcluster.task_distribution_name,  wait_times_mean, run_id, is_colocate=is_colocate)
        utils.write_to_file(result_dir + '/analysis/', 'mean_response_times', policy_file_tag, sys_load, vcluster.task_distribution_name,  response_times_mean, run_id, is_colocate=is_colocate)
        utils.write_to_file(result_dir + '/analysis/', 'zero_wait_frac', policy_file_tag, sys_load, vcluster.task_distribution_name,  zero_wait_fraction, run_id, is_colocate=is_colocate)

if __name__ == "__main__":
    arguments = docopt.docopt(__doc__, version='1.0')
    working_dir = arguments['-d']
    # global result_dir
    result_dir = working_dir
    policy = arguments['-p']
    load = float(arguments['-l'])
    k_value = int(arguments['-k'])
    spine_ratio = int(arguments['-r'])
    run_id = arguments['-i']
    task_distribution_name = arguments['-t']
    failure_mode = arguments['-f']
    failed_switch_id = arguments.get('--fid', -1)
    is_centralized = arguments.get('--centralized')
    if failed_switch_id:
        failed_switch_id = int(arguments.get('--fid', -1))
    is_colocate = arguments.get('--colocate', False)
    delayed_updates = arguments.get('--du', True)
    save_all_results = arguments.get('--all', False)
    print(policy)
    print(save_all_results)
    
    data = utils.read_dataset(working_dir, is_colocate)
    run_scheduling(policy, data, k_value, task_distribution_name, load, spine_ratio, run_id, failure_mode, is_colocate, failed_switch_id, expon_arrival=True, is_centralized=is_centralized, delayed_updates=delayed_updates, save_all_results=save_all_results)

