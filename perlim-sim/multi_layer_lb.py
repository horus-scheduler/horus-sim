"""Usage:
multi_layer_lb.py -d <working_dir> -p <policy> -l <load> -k <k_value> -r <spine_ratio>  -t <task_distribution> -i <id> -f <failure_mode> [--fid <failed_switch_id>] [--colocate] 

multi_layer_lb.py -h | --help
multi_layer_lb.py -v | --version

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

from utils import *
from vcluster import VirtualCluster, Event
from task import Task
from latency_model import LatencyModel
from spine_selector import SpineSelector

FWD_TIME_TICKS = 1 # Number of 0.1us ticks to pass in sim steps...
LOG_PROGRESS_INTERVAL = 60 # Dump some progress info periodically (in seconds)
result_dir = "./"
FAILURE_TIME_TICK = 100

counter = itertools.count()     # unique sequence count
event_queue = []

def report_cluster_results(log_handler, policy_file_tag, sys_load, vcluster, run_id, is_colocate=False):
    log_handler.info(policy_file_tag + ' Finished cluster with ID:' + str(vcluster.cluster_id) +' wait_times @' + str(sys_load) + ':\n' +  str(pd.Series(vcluster.log_task_wait_time).describe()))
    log_handler.info(policy_file_tag + ' Finished cluster with ID:' + str(vcluster.cluster_id) + ' transfer_times @' + str(sys_load) + ':\n' +  str(pd.Series(vcluster.log_task_transfer_time).describe()))
    write_to_file(result_dir, 'wait_times', policy_file_tag, sys_load, vcluster.task_distribution_name,  vcluster.log_task_wait_time, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)
    write_to_file(result_dir, 'transfer_times', policy_file_tag, sys_load, vcluster.task_distribution_name, vcluster.log_task_transfer_time, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)
    write_to_file(result_dir, 'idle_count', policy_file_tag, sys_load, vcluster.task_distribution_name, vcluster.idle_counts, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)
    write_to_file(result_dir, 'queue_lens', policy_file_tag, sys_load, vcluster.task_distribution_name,  vcluster.log_queue_len_signal_workers, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)
    if vcluster.policy == 'adaptive' or vcluster.policy == 'jiq':
            write_to_file(result_dir, 'decision_type', policy_file_tag, sys_load, vcluster.task_distribution_name, vcluster.log_decision_type, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)

def calculate_num_state(policy, switch_state_tor, switch_state_spine, vcluster, vcluster_list):
    for spine_id in range(num_spines):
        # We append the switches with updated number of states to the global switch_state_spine[spine_idx]
        total_states_spine_switch = 0
        for vcluster_x in vcluster_list:
            if spine_id in vcluster_x.selected_spine_list:
                spine_idx = vcluster_x.selected_spine_list.index(spine_id)
                if policy == 'pow_of_k':
                    total_states_spine_switch += vcluster_x.num_tors
                elif policy == 'pow_of_k_partitioned':
                    total_states_spine_switch += len(vcluster_x.spine_tor_map[spine_idx])
                elif policy == 'jiq':
                    total_states_spine_switch += len(vcluster_x.idle_queue_spine[spine_idx])
                elif policy == 'adaptive':
                    total_states_spine_switch += len(vcluster_x.idle_queue_spine[spine_idx])
                    total_states_spine_switch += len(vcluster_x.known_queue_len_spine[spine_idx])

        switch_state_spine[spine_id].append(total_states_spine_switch)

    for tor_id in range(num_tors):
        total_states_tor_switch = 0
        for vcluster_x in vcluster_list:
            if tor_id in vcluster_x.tor_id_unique_list:
                tor_idx = vcluster_x.tor_id_unique_list.index(tor_id)
                if policy == 'pow_of_k' or policy == 'pow_of_k_partitioned':
                    total_states_tor_switch += vcluster_x.tor_id_list.count(tor_id)
                elif policy == 'jiq':
                    total_states_tor_switch += len(vcluster_x.idle_queue_tor[tor_idx])
                elif policy  == 'adaptive':
                    #total_states_tor_switch += len(vcluster_x.idle_queue_tor[tor_idx])
                    total_states_tor_switch += vcluster_x.tor_id_list.count(tor_id)
        switch_state_tor[tor_id].append(total_states_tor_switch)

    return switch_state_tor, switch_state_spine

def process_network(in_transit_tasks, ticks_passed):
    arrived_tasks = []
    if not in_transit_tasks:
        return in_transit_tasks, arrived_tasks

    for task in in_transit_tasks:
        task.network_time -= ticks_passed
        if task.network_time <= 0:
            arrived_tasks.append(task)

    in_transit_tasks = [t for t in in_transit_tasks if t.network_time > 0]

    return in_transit_tasks, arrived_tasks

def jiq_server_process(vcluster, num_msg_tor, num_msg_spine, k, worker_idx, tor_idx):
    min_idle_queue = float("inf")
    if len(vcluster.idle_queue_tor[tor_idx])==1: # Tor just became aware of idle workers and add itself to a spine
        sample_indices = random.sample(range(0, vcluster.num_spines), min(k, vcluster.num_spines)) # Sample k spines
        #print sample_indices
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
    num_msg_tor[tor_id] += 1    #1 msg for updating tor idle queue
    
    return vcluster, num_msg_tor, num_msg_spine

def adaptive_server_process(vcluster, num_msg_tor, num_msg_spine, k, worker_idx, tor_idx):
    vcluster.idle_queue_tor[tor_idx].append(worker_idx)
    tor_id = vcluster.tor_id_unique_list[tor_idx]
    # Add idle worker to tor (1 msg) for removing SQ from ToR (and also adds the server to IQ of ToR)
    num_msg_tor[tor_id] += 1 # 

    if len(vcluster.idle_queue_tor[tor_idx])==1: # Tor just became aware of idle workers and add itself to a spine
        sample_indices = random.sample(range(0, vcluster.num_spines), min(k, vcluster.num_spines)) # Sample k dispatchers
        min_idle_queue = float("inf")
        for idx in sample_indices:  # Find the sampled spine with min idle queue len (k msgs)
            sampled_value = len(vcluster.idle_queue_spine[idx])
            sampled_spine_id = vcluster.selected_spine_list[idx]

            num_msg_spine[sampled_spine_id] += 1
            if sampled_value < min_idle_queue:
                min_idle_queue = sampled_value
                target_spine_idx = idx

        # Add tor to the idle queue of that spine (1 msg)
        vcluster.idle_queue_spine[target_spine_idx].append(tor_idx) 
        target_spine_id = vcluster.selected_spine_list[target_spine_idx]
        num_msg_spine[target_spine_id] += 1 # for updating the spine idle queue
    
        # TODO @parham: Another config as discussed in documents is to switch to JIQ and remove all SQs when an idle queue available
        # Uncomment below!
        vcluster.known_queue_len_spine[target_spine_idx].clear() # Switched to JIQ

    for spine_idx in range(vcluster.num_spines):
        if tor_idx in vcluster.known_queue_len_spine[spine_idx]:
            # print (known_queue_len)
            # print("deleted " + str(server_idx) + " with load: " + str(known_queue_len[d][server_idx]))
            del vcluster.known_queue_len_spine[spine_idx][tor_idx] # Delete sq entery from previously linked spine (1msg)
            spine_id = vcluster.selected_spine_list[spine_idx]
            num_msg_spine[spine_id] += 1 # for removing SQ from other dispatcher
    
    return  vcluster, num_msg_tor, num_msg_spine

def process_tasks_fcfs(
    finished_task,
    num_msg_tor=None,
    num_msg_spine=None,
    k=2
    ):
    
    i = finished_task.target_worker
    vcluster = finished_task.vcluster
    
    #  finished executing task
    vcluster.task_lists[i].pop(0)        # Remove from list
    vcluster.queue_lens_workers[i] -= 1       # Decrement worker queue len

    tor_id = get_tor_id_for_host(vcluster.host_list[i])
    # Conversion for mapping to cluster's local lists
    tor_idx = finished_task.target_tor

    vcluster.queue_lens_tors[tor_idx] = calculate_tor_queue_len(tor_id, vcluster.queue_lens_workers, vcluster.host_list)
    if (vcluster.policy == 'pow_of_k') or (vcluster.policy == 'pow_of_k_partitioned'): # Random and JIQ do not use this part
        num_msg_tor[tor_id] += 1 # Update worker queuelen at ToR
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
                vcluster, num_msg_tor, num_msg_spine = jiq_server_process(
                    vcluster, 
                    num_msg_tor,
                    num_msg_spine,
                    k,
                    i,
                    tor_idx)
        elif vcluster.policy == 'adaptive': # Adaptive
            if vcluster.queue_lens_workers[i] == 0: # Process for when a server becomes idle 
                vcluster, num_msg_tor, num_msg_spine = adaptive_server_process(
                    vcluster,
                    num_msg_tor,
                    num_msg_spine,
                    k,
                    i,
                    tor_idx)
            else:
                num_msg_tor[tor_id] += 1 
                for spine_idx in range(vcluster.num_spines): # ToR that is paired with a spine, will update the signal 
                    if tor_idx in vcluster.known_queue_len_spine[spine_idx]:
                        # TODO @parham: Here the ToR should report the *known* queue lens or ToR keeps all of the queue lens
                        vcluster.known_queue_len_spine[spine_idx].update({tor_idx: vcluster.queue_lens_tors[tor_idx]}) # Update SQ signals
                        spine_id = vcluster.selected_spine_list[spine_idx]
                        num_msg_spine[spine_id] += 1

    return num_msg_tor, num_msg_spine

def schedule_task_random(new_task, target_spine): 
    target_tor = random.randrange(new_task.vcluster.num_tors) # Dummy, not used in random as it randomly selects the *workers* don't care about ToRs
    target_worker = nr.randint(0, new_task.vcluster.num_workers) # Make decision
    
    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task

def schedule_task_pow_of_k(new_task, k, target_spine):
    vcluster = new_task.vcluster
    num_spines = vcluster.num_spines
    num_tors = vcluster.num_tors
    num_workers = vcluster.num_workers
    queue_lens_tors = vcluster.queue_lens_tors
    queue_lens_workers = vcluster.queue_lens_workers
            
    # Make the decision at spine:
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

    # Make the decision at ToR:
    min_load = float("inf")

    worker_indices = get_worker_indices_for_tor(vcluster.tor_id_unique_list[target_tor], vcluster.host_list)
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
    worker_indices = get_worker_indices_for_tor(vcluster.tor_id_unique_list[target_tor], vcluster.host_list)
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

def schedule_task_jiq(new_task, num_msg_tor, num_msg_spine, target_spine):
    # Make decision at spine level:
    if new_task.vcluster.idle_queue_spine[target_spine]:  # Spine is aware of some tors with idle wokrers
        target_tor = new_task.vcluster.idle_queue_spine[target_spine][0]
        new_task.decision_tag = 0
    else:   # No tor with idle worker is known, dispatch to a random tor
        #target_tor = random.choice(get_tor_partition_range_for_spine(target_spine)) Limit to pod
        target_tor = nr.randint(0, new_task.vcluster.num_tors) # Can forward to any ToR
        new_task.decision_tag = 2
    
    # # Make decision at tor level:
    # if len(new_task.vcluster.idle_queue_tor[target_tor]) <= 1:
    #     if new_task.decision_tag == 0:
    #         new_task.vcluster.idle_queue_spine[target_spine].pop(0) 

    if new_task.vcluster.idle_queue_tor[target_tor]: # Tor is aware of some idle workers
        target_worker = new_task.vcluster.idle_queue_tor[target_tor].pop(0)
    else:
        worker_indices = get_worker_indices_for_tor(new_task.vcluster.tor_id_unique_list[target_tor], new_task.vcluster.host_list)
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
    return new_task, num_msg_tor, num_msg_spine

def schedule_task_adaptive(new_task, k, num_msg_tor, num_msg_spine, target_spine):
    partition_size_spine = new_task.vcluster.partition_size
    
    target_spine_id = new_task.vcluster.selected_spine_list[target_spine]

    # Make decision at spine layer:
    min_load = float("inf")
    if len(new_task.vcluster.idle_queue_spine[target_spine]) > 0:  # Spine is aware of some tors with idle servers
        target_tor = new_task.vcluster.idle_queue_spine[target_spine][0]
        new_task.decision_tag = 0
        # if (new_task.vcluster.cluster_id == 5):
        #     print(new_task.vcluster.idle_queue_spine)
        #     print(new_task.vcluster.known_queue_len_spine)
        #     print(new_task.vcluster.idle_queue_spine)
            
    else:   # No tor with idle server is known
        sq_update = False
        if (len(new_task.vcluster.known_queue_len_spine[target_spine]) < partition_size_spine): # Scheduer still trying to get more queue len info
            num_samples = min(k, new_task.vcluster.num_tors)
            probe_tors = random.sample(range(new_task.vcluster.num_tors), num_samples)

            for random_tor in probe_tors:
                already_paired = False
                for spine_idx in range(new_task.vcluster.num_spines):
                    if random_tor in new_task.vcluster.known_queue_len_spine[spine_idx]:
                        already_paired = True
                # if len(new_task.vcluster.idle_queue_tor[random_tor]) > 0: # If ToR is aware of some idle worker, it's already paired with another spine (registered in their Idle Queue)
                #     already_paired = True
                if not already_paired: # Each tor queue len should be available at one spine only
                    new_task.vcluster.known_queue_len_spine[target_spine].update({random_tor: new_task.vcluster.queue_lens_tors[random_tor]}) # This is to indicate that spine will track queue len of ToR from now on
                    random_tor_id = new_task.vcluster.tor_id_unique_list[random_tor]
                    num_msg_tor[random_tor_id] += 1 # 1 msg sent to ToR
                    num_msg_spine[target_spine_id] += 1 # Reply from tor to add SQ signal
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
            new_task.decision_tag = 1 # SQ-based decision
        else: # Randomly select a ToR from all of the available tors
            target_tor = nr.randint(0, new_task.vcluster.num_tors)
            new_task.decision_tag = 2 # Random-based decision
            num_msg_spine[target_spine_id] += 1 # msg from tor to add SQ signal

    if len(new_task.vcluster.idle_queue_tor[target_tor]) > 0:  # Tor is aware of some idle workers
        target_worker = new_task.vcluster.idle_queue_tor[target_tor].pop(0)

    else: # No idle worker
        min_load = float("inf")
        worker_indices = get_worker_indices_for_tor(new_task.vcluster.tor_id_unique_list[target_tor], new_task.vcluster.host_list)
        num_samples = k
        if len(worker_indices) < k:
            num_samples = len(worker_indices)
        sample_indices = random.sample(worker_indices, num_samples) # Sample from workers connected to that ToR

        for idx in sample_indices:
            sample = new_task.vcluster.queue_lens_workers[idx]
            if sample < min_load:
                min_load = sample
                target_worker = idx

    for spine_idx, idle_tor_list in enumerate(new_task.vcluster.idle_queue_spine):
        if target_tor in idle_tor_list:   # ToR removes itself from the idle queue it has joined
            if len(new_task.vcluster.idle_queue_tor[target_tor]) == 0:
                new_task.vcluster.idle_queue_spine[spine_idx].remove(target_tor)
                spine_id = new_task.vcluster.selected_spine_list[spine_idx]
                num_msg_spine[spine_id] += 1 # "Remove" msg from tor

    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task, num_msg_tor, num_msg_spine

def update_switch_views(scheduled_task, num_msg_spine):
    scheduled_task.vcluster.queue_lens_workers[scheduled_task.target_worker] += 1
    scheduled_task.vcluster.queue_lens_tors[scheduled_task.target_tor] = calculate_tor_queue_len(
            scheduled_task.global_tor_id,
            scheduled_task.vcluster.queue_lens_workers,
            scheduled_task.vcluster.host_list
        )
    if scheduled_task.vcluster.policy == 'pow_of_k':
        for spine_idx in range(scheduled_task.vcluster.num_spines): # Update ToR queue len for all other spines
            if spine_idx != scheduled_task.first_spine:
                spine_id = scheduled_task.vcluster.selected_spine_list[spine_idx]
                num_msg_spine[spine_id] += 1

    elif scheduled_task.vcluster.policy == 'adaptive':
        # ToR that is linked with a spine, will update the signal 
        for spine_idx in range(scheduled_task.vcluster.num_spines): 
            if scheduled_task.target_tor in scheduled_task.vcluster.known_queue_len_spine[spine_idx]:
                scheduled_task.vcluster.known_queue_len_spine[spine_idx].update({scheduled_task.target_tor: scheduled_task.vcluster.queue_lens_tors[scheduled_task.target_tor]}) # Update SQ signals
                spine_id = scheduled_task.vcluster.selected_spine_list[spine_idx]
        scheduled_task.vcluster.log_known_queue_len_spine.append(scheduled_task.vcluster.queue_lens_tors[scheduled_task.target_tor])
        
    return num_msg_spine

def handle_task_delivered(event):
    delivered_task = event.task
    task_waiting_time = np.sum(delivered_task.vcluster.task_lists[delivered_task.target_worker])
    delivered_task.vcluster.log_task_wait_time.append(task_waiting_time) # Task assigned to target worker should wait at least as long as pending load
    delivered_task.vcluster.log_task_transfer_time.append(delivered_task.transfer_time)
    delivered_task.vcluster.log_queue_len_signal_workers.append(delivered_task.vcluster.queue_lens_workers[delivered_task.target_worker])
    delivered_task.vcluster.log_queue_len_signal_tors.append(delivered_task.vcluster.queue_lens_tors[delivered_task.target_tor])
    delivered_task.vcluster.log_decision_type.append(delivered_task.decision_tag)
    
    delivered_task.vcluster.task_lists[delivered_task.target_worker].append(delivered_task.load)
    
    return task_waiting_time

def run_scheduling(policy, data, k, task_distribution_name, sys_load, spine_ratio, run_id, failure_mode, is_colocate, failed_switch_id):
    nr.seed()
    random.seed()
    #heapify(event_queue)
    latency_model = LatencyModel('./')
    spine_selector = SpineSelector(PER_SPINE_CAPACITY)
    controller_pod = random.choice(range(num_pods))

    policy_file_tag = get_policy_file_tag(policy, k)
    
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
            task_distribution_name=task_distribution_name)
        
        # For failure simulations we only process events of the impacted clusters (instead of all vclusters)
        if failure_mode == 'none':
            seq = next(counter)
            event_entry = [0, seq, Event(event_type='new_task', vcluster=vcluster)]
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
            print (vcluster.selected_spine_list)
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

    partition_size_spine = num_tors / num_spines
    
    decision_tag = 0

    num_msg_spine = [0] * num_spines  
    num_msg_tor = [0] * num_tors
    num_task_spine = [0] * num_spines  
    num_task_tor = [0] * num_tors

    switch_state_spine = [] * num_spines 
    switch_state_tor = [] * num_tors

    terminate_experiment = False
    for spine_idx in range(num_spines):
        switch_state_spine.append([0])

    for tor_idx in range(num_tors):
        switch_state_tor.append([0])

    start_time = time.time()

    tick = 0
    
    event_count = 0
    max_event_tick = 0
    # for t, seq, e in event_queue:
    #     print (seq)
    #     print (e.vcluster)
    #     e.print_debug()
    failure_detection_time = 0

    while(cluster_terminate_count < len(vcluster_list)):
        event_tick, count, event = heappop(event_queue)
        event_count += 1
        # print ('\n\n\n\n')
        # event.print_debug()
        # print ('\n\n\n\n')

        # for t, s, e in event_queue:
        #     print (s)
        #     print (e.vcluster)
        #     e.print_debug()
        #print("Got event for vcluster: " + str(event.print_debug()) + " Type: " + str(event.type) + " Time tick: " + str(event_tick))
        
        if event_tick >= max_event_tick:
            max_event_tick = event_tick
        else:
            raise Exception("Got event in past!")
        
        tick = event_tick
        if event.type == 'new_task':
            vcluster = event.vcluster
            vcluster.last_task_arrival = event_tick
            num_idles = calculate_idle_count(vcluster.queue_lens_workers)
            vcluster.idle_counts.append(num_idles)
            load = vcluster.task_distribution[vcluster.task_idx] # Pick new task load (load is execution time)
            new_task = Task(load, vcluster)
            scheduling_failed = False
            # A random client will initiate the request
            client_index = random.randrange(vcluster.num_clients)
            # Simulating arrival of task at a spine randomly
            spine_sched_id = random.choice(vcluster.client_spine_list[client_index])
            spine_shched_index = vcluster.selected_spine_list.index(spine_sched_id)
            
            if failure_happened:
                if spine_sched_id == failed_spine_id: # Task was sent to the failed scheduler
                    vcluster.num_failed_tasks += 1
                    scheduling_failed = True
                else:
                    if not vcluster.failover_converged:
                        vcluster.num_scheduled_tasks += 1
            if not scheduling_failed:
                if vcluster.policy == 'random':
                    scheduled_task = schedule_task_random(new_task, spine_shched_index)

                elif vcluster.policy == 'pow_of_k':
                    scheduled_task = schedule_task_pow_of_k(new_task, k, spine_shched_index)
                    
                elif vcluster.policy == 'pow_of_k_partitioned':
                    scheduled_task = schedule_task_pow_of_k_partitioned(new_task, k, spine_shched_index)

                elif vcluster.policy == 'jiq':
                    scheduled_task, num_msg_tor, num_msg_spine = schedule_task_jiq(
                        new_task,
                        num_msg_tor, 
                        num_msg_spine, 
                        spine_shched_index)

                elif vcluster.policy == 'adaptive':
                    scheduled_task, num_msg_tor, num_msg_spine = schedule_task_adaptive(
                        new_task,
                        k,
                        num_msg_tor, 
                        num_msg_spine, 
                        spine_shched_index)

                num_task_spine[scheduled_task.global_spine_id] += 1
                num_task_tor[scheduled_task.global_tor_id] += 1
                num_msg_spine = update_switch_views(scheduled_task, num_msg_spine)
            
                # Trigger two future events (1) task delivered to worker (2) next task arrive at scheduler
                seq = next(counter)
                event_entry = [tick + scheduled_task.network_time, seq, Event(event_type='delivered', vcluster=vcluster, task=scheduled_task)]
                heappush(event_queue, event_entry)
            if vcluster.task_idx < (len(vcluster.task_distribution) - 1):
                seq = next(counter)
                event_entry = [tick + vcluster.inter_arrival, seq, Event(event_type='new_task', vcluster=vcluster)]
                heappush(event_queue, event_entry)
                vcluster.task_idx += 1
            else:
                cluster_terminate_count += 1
                report_cluster_results(log_handler_experiment, policy_file_tag, sys_load, vcluster, run_id, is_colocate)
                # Report these metrics for the period that all vclusters are running
                if (cluster_terminate_count==1):
                    write_to_file(result_dir, 'task_per_sec_tor', policy_file_tag, sys_load, task_distribution_name, task_per_sec_tor, run_id, is_colocate=is_colocate)
                    write_to_file(result_dir, 'task_per_sec_spine', policy_file_tag, sys_load, task_distribution_name, task_per_sec_spine, run_id, is_colocate=is_colocate)
                    if policy != 'random':
                        write_to_file(result_dir, 'msg_per_sec_tor', policy_file_tag, sys_load, task_distribution_name, msg_per_sec_tor, run_id, is_colocate=is_colocate)
                        write_to_file(result_dir, 'msg_per_sec_spine', policy_file_tag, sys_load, task_distribution_name, msg_per_sec_spine, run_id, is_colocate=is_colocate)

        elif event.type == 'finished':
            num_msg_tor, num_msg_spine = process_tasks_fcfs(
                    finished_task=event.task,
                    num_msg_tor=num_msg_tor,
                    num_msg_spine=num_msg_spine,
                    k=k)

        elif event.type == 'delivered':
            task_waiting_time = handle_task_delivered(event)
            task_finish_time = tick + task_waiting_time + event.task.load
            #print ("Registered: finish_time: " + str(task_finish_time) + " waiting_time: " + str(task_waiting_time) + " load: " + str(delivered_task.load))
            seq = next(counter)
            event_entry = [task_finish_time, seq, Event(event_type='finished', vcluster=event.task.vcluster, task=event.task)]
            heappush(event_queue, event_entry)

            #print arrived_task.target_worker
            # if np.sum(arrived_task.vcluster.task_lists[arrived_task.target_worker]) > 0 and arrived_task.decision_tag == 0:
            #     print("ERROR! Spine :" + str(arrived_task.first_spine) + ", Tor :" + str(arrived_task.target_tor) + ", Worker :" + str(arrived_task.target_worker))
            #     exit(0)
        
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
            event.vcluster.failover_converge_latency = tick - failure_detection_time
            num_converged_vclusters +=1
            if num_converged_vclusters == len(affected_vcluster_list):
                terminate_experiment = True
        elapsed_time = time.time() - start_time
        
        if elapsed_time > LOG_PROGRESS_INTERVAL:
            log_handler_dcn.debug(policy_file_tag + ' progress log @' + str(sys_load) + ' Ticks passed: ' + str(tick) + ' Events processed: ' + str(event_count) + ' Clusters done: ' + str(cluster_terminate_count))
            exp_duration_s = float(tick) / (10**9)
            msg_per_sec_spine = [x / exp_duration_s for x in num_msg_spine]
            msg_per_sec_tor = [x / exp_duration_s for x in num_msg_tor]
            task_per_sec_tor = [x / exp_duration_s for x in num_task_tor]
            task_per_sec_spine = [x / exp_duration_s for x in num_task_spine]
            
            if failure_mode == 'spine':
                failed_tasks = [vcluster.num_failed_tasks for vcluster in affected_vcluster_list]
                scheduled_tasks = [vcluster.num_scheduled_tasks for vcluster in affected_vcluster_list]
                converge_latency = [vcluster.failover_converge_latency for vcluster in affected_vcluster_list]
                affected_clients = [vcluster.num_clients for vcluster in affected_vcluster_list]
                log_handler_dcn.info(policy_file_tag + ' num_failed_tasks @' + str(sys_load) + ' :' +  str(pd.Series(failed_tasks).describe()))
                log_handler_dcn.info(policy_file_tag + ' num_scheduled_tasks @' + str(sys_load) + ' :' +  str(pd.Series(scheduled_tasks).describe()))

            log_handler_dcn.info(policy_file_tag + ' task_per_sec_spine @' + str(sys_load) + ':\n' +  str(pd.Series(task_per_sec_spine).describe()))
            log_handler_dcn.info(policy_file_tag + ' task_per_sec_tor @' + str(sys_load) + ':\n' +  str(pd.Series(task_per_sec_tor).describe()))

            log_handler_dcn.info(policy_file_tag + ' msg_per_sec_spine @' + str(sys_load) + ':\n' +  str(pd.Series(msg_per_sec_spine).describe()))
            log_handler_dcn.info(policy_file_tag + ' msg_per_sec_tor @' + str(sys_load) + ':\n' +  str(pd.Series(msg_per_sec_tor).describe()))    
            start_time = time.time()
            if terminate_experiment:
                break

    exp_duration_s = float(tick) / (10**9)
    msg_per_sec_spine = [x / exp_duration_s for x in num_msg_spine]
    msg_per_sec_tor = [x / exp_duration_s for x in num_msg_tor]
    task_per_sec_tor = [x / exp_duration_s for x in num_task_tor]
    task_per_sec_spine = [x / exp_duration_s for x in num_task_spine]

    if failure_mode == 'spine':
        failed_tasks = [vcluster.num_failed_tasks for vcluster in affected_vcluster_list]
        scheduled_tasks = [vcluster.num_scheduled_tasks for vcluster in affected_vcluster_list]
        converge_latency = [vcluster.failover_converge_latency for vcluster in affected_vcluster_list]
        affected_clients = [vcluster.num_clients for vcluster in affected_vcluster_list]

        write_to_file(result_dir, 'num_failed_tasks', policy_file_tag, sys_load, task_distribution_name, failed_tasks, run_id, is_colocate=is_colocate)
        write_to_file(result_dir, 'num_scheduled_tasks', policy_file_tag, sys_load, task_distribution_name, scheduled_tasks, run_id, is_colocate=is_colocate)
        write_to_file(result_dir, 'converge_latency', policy_file_tag, sys_load, task_distribution_name, converge_latency, run_id, is_colocate=is_colocate)
        write_to_file(result_dir, 'affected_tors', policy_file_tag, sys_load, task_distribution_name, affected_tor_list, run_id, is_colocate=is_colocate)
        write_to_file(result_dir, 'affected_clients', policy_file_tag, sys_load, task_distribution_name, affected_clients, run_id, is_colocate=is_colocate)
    

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
    if failed_switch_id:
        failed_switch_id = int(arguments.get('--fid', -1))
    is_colocate = arguments.get('--colocate', False)
    print(policy)
    
    data = read_dataset(working_dir, is_colocate)
    run_scheduling(policy, data, k_value, task_distribution_name, load, spine_ratio, run_id, failure_mode, is_colocate, failed_switch_id)

