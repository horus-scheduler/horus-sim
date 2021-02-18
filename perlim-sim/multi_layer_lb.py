import numpy.random as nr
import numpy as np
import math
import random 
import sys
import pandas as pd
import time
from multiprocessing import Process, Queue, Value, Array
from loguru import logger

from utils import *
from vcluster import VirtualCluster
from task import Task

LOG_PROGRESS_INTERVAL = 420 # Dump some progress info periodically (in seconds)

def report_cluster_results(log_handler, policy_file_tag, sys_load, vcluster):
    log_handler.info(policy_file_tag + ' Finished cluster with ID:' + str(vcluster.cluster_id) +' wait_times @' + str(sys_load) + ':\n' +  str(pd.Series(vcluster.log_task_wait_time).describe()))
    log_handler.info(policy_file_tag + ' Finished cluster with ID:' + str(vcluster.cluster_id) + ' transfer_times @' + str(sys_load) + ':\n' +  str(pd.Series(vcluster.log_task_transfer_time).describe()))
    write_to_file('wait_times', policy_file_tag, sys_load, vcluster.task_distribution_name,  vcluster.log_task_wait_time, cluster_id=vcluster.cluster_id)
    write_to_file('transfer_times', policy_file_tag, sys_load, vcluster.task_distribution_name, vcluster.log_task_transfer_time, cluster_id=vcluster.cluster_id)
    write_to_file('idle_count', policy_file_tag, sys_load, vcluster.task_distribution_name, vcluster.idle_counts, cluster_id=vcluster.cluster_id)
    write_to_file('queue_lens', policy_file_tag, sys_load, vcluster.task_distribution_name,  vcluster.log_queue_len_signal_workers, cluster_id=vcluster.cluster_id)
    if vcluster.policy == 'adaptive':
            write_to_file('decision_type', policy_file_tag, sys_load, vcluster.task_distribution_name, vcluster.log_decision_type, cluster_id=vcluster.cluster_id)

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
                    total_states_tor_switch += len(vcluster_x.idle_queue_tor[tor_idx])
                    total_states_tor_switch += len(vcluster_x.known_queue_len_tor[tor_idx])
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
    
    sample_indices = random.sample(range(0, vcluster.num_spines), min(k, vcluster.num_spines)) # Sample k spines
    #print sample_indices
    for idx in sample_indices:  # Find the sampled spine with min idle queue len
        sampled_value = len(vcluster.idle_queue_spine[idx])
        sampled_spine_id = vcluster.selected_spine_list[idx]

        num_msg_spine[sampled_spine_id] += 1   # total k msgs for sampling spine idle queues
        if sampled_value < min_idle_queue:
            min_idle_queue = sampled_value
            target_spine_idx = idx

    vcluster.idle_queue_tor[tor_idx].append(worker_idx) # Add idle worker to idle queue of ToR
    tor_id = vcluster.tor_id_unique_list[tor_idx]

    num_msg_tor[tor_id] += 1    #1 msg for updating tor idle queue
    
    already_paired = False
    for spine_idx in range(vcluster.num_spines):
        if tor_idx in vcluster.idle_queue_spine[spine_idx]:
            already_paired = True

    if not already_paired:
        vcluster.idle_queue_spine[target_spine_idx].append(tor_idx) # Add ToR to the idle queue of selected spine
        target_spine_id = vcluster.selected_spine_list[target_spine_idx]
        num_msg_spine[target_spine_id] += 1 # 1 msg for updating spine idle queue
    return vcluster, num_msg_tor, num_msg_spine

def adaptive_server_process(vcluster, num_msg_tor, num_msg_spine, k, worker_idx, tor_idx):
    vcluster.idle_queue_tor[tor_idx].append(worker_idx)
    tor_id = vcluster.tor_id_unique_list[tor_idx]
    # Add idle worker to tor (1 msg) for removing SQ from ToR (and also adds the server to IQ of ToR)
    num_msg_tor[tor_id] += 1 # 

    # TODO @parham: Remove idle worker from list of SQ signals? Uncomment below!
    if worker_idx in vcluster.known_queue_len_tor[tor_idx]:
        del vcluster.known_queue_len_tor[tor_idx][worker_idx] # Remove sq entery from tor

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
        vcluster.known_queue_len_tor[tor_idx].clear() # Switched to JIQ
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
    vcluster,
    ticks_passed=1,
    num_msg_tor=None,
    num_msg_spine=None,
    k=2
    ):
    for i in range(len(vcluster.task_lists)):
        while vcluster.task_lists[i]:    # while there are any tasks in list
            remaining_time = vcluster.task_lists[i][0] - ticks_passed   # First task in list is being executed
            vcluster.task_lists[i][0] = max(0, remaining_time) # If remaining time from task is negative another task is could be executed during the interval
            if vcluster.task_lists[i][0] == 0:   # If finished executing task
                vcluster.task_lists[i].pop(0)        # Remove from list
                vcluster.queue_lens_workers[i] -= 1       # Decrement worker queue len

                tor_id = get_tor_id_for_host(vcluster.host_list[i])
                # Conversion for mapping to cluster's local lists
                tor_idx = vcluster.tor_id_unique_list.index(tor_id)

                vcluster.queue_lens_tors[tor_idx] = calculate_tor_queue_len(tor_id, vcluster.queue_lens_workers, vcluster.host_list)

                # if queue_lens_tors[tor_idx] < 0:
                #     print ("ERROR")
                #     print("Tor: " + str(tor_idx) + "worker: " + str(i))
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
                            if i in vcluster.known_queue_len_tor[tor_idx]: # Update queue len of worker at ToR
                                vcluster.known_queue_len_tor[tor_idx].update({i: vcluster.queue_lens_workers[i]})  
                                tor_id = vcluster.tor_id_unique_list[tor_idx]
                                num_msg_tor[tor_id] += 1 
                            for spine_idx in range(vcluster.num_spines): # ToR that is paired with a spine, will update the signal 
                                if tor_idx in vcluster.known_queue_len_spine[spine_idx]:
                                    # TODO @parham: Here the ToR should report the *known* queue lens or ToR keeps all of the queue lens
                                    vcluster.known_queue_len_spine[spine_idx].update({tor_idx: vcluster.queue_lens_tors[tor_idx]}) # Update SQ signals
                                    spine_id = vcluster.selected_spine_list[spine_idx]
                                    num_msg_spine[spine_id] += 1

            if remaining_time >= 0:     # Continue loop (processing other tasks) only if remaining time is negative
                break

    return num_msg_tor, num_msg_spine

def schedule_task_random(new_task):
    # Emulating arrival at a spine randomly
    target_spine = random.randrange(new_task.vcluster.num_spines)  
    
    target_tor = random.randrange(new_task.vcluster.num_tors) # Dummy, not used in random as it randomly selects the *workers* don't care about ToRs
    target_worker = nr.randint(0, new_task.vcluster.num_workers) # Make decision
    
    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task

def schedule_task_pow_of_k(new_task, k):
    vcluster = new_task.vcluster
    num_spines = vcluster.num_spines
    num_tors = vcluster.num_tors
    num_workers = vcluster.num_workers
    queue_lens_tors = vcluster.queue_lens_tors
    queue_lens_workers = vcluster.queue_lens_workers

    target_spine = random.randrange(num_spines)  # Emulating arrival at a spine randomly
            
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

def schedule_task_pow_of_k_partitioned(new_task, k):
    vcluster = new_task.vcluster
    num_spines = vcluster.num_spines
    num_tors = vcluster.num_tors
    num_workers = vcluster.num_workers
    queue_lens_tors = vcluster.queue_lens_tors
    queue_lens_workers = vcluster.queue_lens_workers

    target_spine = random.randrange(num_spines)  # Emulating arrival at a spine randomly
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

def schedule_task_jiq(new_task, num_msg_tor, num_msg_spine):
    target_spine = random.randrange(new_task.vcluster.num_spines)  # Emulating arrival at a spine switch randomly
            
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

def schedule_task_adaptive(new_task, k, num_msg_tor, num_msg_spine):
    partition_size_spine = new_task.vcluster.partition_size
    
    target_spine = random.randrange(new_task.vcluster.num_spines)  # Emulating arrival at a spine switch randomly
    target_spine_id = new_task.vcluster.selected_spine_list[target_spine]

    # Make decision at spine layer:
    min_load = float("inf")
    if len(new_task.vcluster.idle_queue_spine[target_spine]) > 0:  # Spine is aware of some tors with idle servers
        target_tor = new_task.vcluster.idle_queue_spine[target_spine][0]
        new_task.decision_tag = 0
    else:   # No tor with idle server is known
        already_paired = False
        sq_update = False
        
        if (len(new_task.vcluster.known_queue_len_spine[target_spine]) >= k): # Do shortest queue if enough info available    
            if (len(new_task.vcluster.known_queue_len_spine[target_spine]) < partition_size_spine): # Scheduer still trying to get more queue len info
                random_tor = nr.randint(0, new_task.vcluster.num_tors)
                for spine_idx in range(new_task.vcluster.num_spines):
                    if random_tor in new_task.vcluster.known_queue_len_spine[spine_idx]:
                        already_paired = True
                if len(new_task.vcluster.idle_queue_tor[random_tor]) > 0: # If ToR is aware of some idle worker, it's already paired with another spine (registered in their Idle Queue)
                    already_paired = True

                if not already_paired: # Each tor queue len should be available at one spine only
                    sq_update = True

            sample_tors = random.sample(list(new_task.vcluster.known_queue_len_spine[target_spine]), k) # k samples from ToR queue lenghts available to that spine
            #print (sample_workers)
            for tor_idx in sample_tors:
                sample_queue_len = new_task.vcluster.known_queue_len_spine[target_spine][tor_idx]
                if sample_queue_len < min_load:
                    min_load = sample_queue_len
                    target_tor = tor_idx
            new_task.decision_tag = 1 # SQ-based decision
        else: # Randomly select a ToR from all of the available tors
            target_tor = nr.randint(0, new_task.vcluster.num_tors)
            for spine_idx in range(new_task.vcluster.num_spines):
                if target_tor in new_task.vcluster.known_queue_len_spine[spine_idx]:
                    already_paired = True
            if len(new_task.vcluster.idle_queue_tor[target_tor]) > 0:
                already_paired = True
            if not already_paired: # Each tor queue len should be available at one spine only
                new_task.vcluster.known_queue_len_spine[target_spine].update({target_tor: 10000}) # Add SQ signal
                num_msg_spine[target_spine_id] += 1 # Reply from tor to add SQ signal
            new_task.decision_tag = 2 # Random-based decision
        if sq_update:
            new_task.vcluster.known_queue_len_spine[target_spine].update({random_tor: 10000}) # This is to indicate that spine will track queue len of ToR from now on
            random_tor_id = new_task.vcluster.tor_id_unique_list[random_tor]
            num_msg_tor[random_tor_id] += 1 # 1 msg sent to ToR

            if new_task.vcluster.known_queue_len_tor[target_tor]: # Any SQ signal available to ToR at the time
                sum_known_signals = 0
                for worker in new_task.vcluster.known_queue_len_tor[target_tor]:
                    sum_known_signals += new_task.vcluster.known_queue_len_tor[target_tor][worker]
                    avg_known_queue_len = float(sum_known_signals) / len(new_task.vcluster.known_queue_len_tor[target_tor]) 
                
                new_task.vcluster.known_queue_len_spine[target_spine].update({random_tor: avg_known_queue_len}) # Add SQ signal
            num_msg_spine[target_spine_id] += 1 # msg from tor to add SQ signal



                
    # Make decision at ToR layer:
    # if len(new_task.vcluster.idle_queue_tor[target_tor]) <= 1:
    #     if new_task.decision_tag ==0:
    #         new_task.vcluster.idle_queue_spine[target_spine].pop(0)
    #     num_msg_spine[target_spine_id] += 1 # ToR informs the spine if it is no longer idle

    min_load = float("inf")
    worker_indices = get_worker_indices_for_tor(new_task.vcluster.tor_id_unique_list[target_tor], new_task.vcluster.host_list)
    
    if len(new_task.vcluster.idle_queue_tor[target_tor]) > 0:  # Tor is aware of some idle workers
        target_worker = new_task.vcluster.idle_queue_tor[target_tor].pop(0)

    else: # No idle worker
        already_paired = False
        sq_update = False
        if (len(new_task.vcluster.known_queue_len_tor[target_tor]) < len(worker_indices)): # Tor scheduer still trying to get more queue len info
                target_tor_id = new_task.vcluster.tor_id_unique_list[target_tor]
                num_msg_tor[target_tor_id] += 1 # Requesting for SQ signal
                random_worker = random.choice(worker_indices)
                sq_update = True
        if (len(new_task.vcluster.known_queue_len_tor[target_tor]) >= k): # Shortest queue if enough info is available
            sample_workers = random.sample(list(new_task.vcluster.known_queue_len_tor[target_tor]), k) # k samples from worker queue lenghts available
            for worker_idx in sample_workers:
                sample_queue_len = new_task.vcluster.known_queue_len_tor[target_tor][worker_idx]
                if sample_queue_len < min_load:
                    min_load = sample_queue_len
                    target_worker = worker_idx
            
        else: # Randomly select a worker from all of the available workers
            target_worker = random.choice(worker_indices)
            #known_queue_len_tor[target_tor].update({target_worker: None}) # Add SQ signal
        if sq_update:
            new_task.vcluster.known_queue_len_tor[target_tor].update({random_worker: new_task.vcluster.queue_lens_workers[target_worker]}) # Add SQ signal
            target_tor_id = new_task.vcluster.tor_id_unique_list[target_tor]
            num_msg_tor[target_tor_id] += 1 # Requesting for SQ signal

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
    scheduled_task.vcluster.host_list)
    if scheduled_task.vcluster.policy == 'pow_of_k':
        for spine_idx in range(scheduled_task.vcluster.num_spines): # Update ToR queue len for all other spines
            if spine_idx != scheduled_task.first_spine:
                spine_id = scheduled_task.vcluster.selected_spine_list[spine_idx]
                num_msg_spine[spine_id] += 1

    elif scheduled_task.vcluster.policy == 'adaptive':
        if scheduled_task.target_worker in scheduled_task.vcluster.known_queue_len_tor[scheduled_task.target_tor]: # Update queue len of worker at ToR
            scheduled_task.vcluster.known_queue_len_tor[scheduled_task.target_tor].update({scheduled_task.target_worker: scheduled_task.vcluster.queue_lens_workers[scheduled_task.target_worker]}) 
        
        if scheduled_task.vcluster.known_queue_len_tor[scheduled_task.target_tor]: # Some SQ signal available at ToR
            sum_known_signals = 0
            for worker in scheduled_task.vcluster.known_queue_len_tor[scheduled_task.target_tor]:
                sum_known_signals += scheduled_task.vcluster.known_queue_len_tor[scheduled_task.target_tor][worker]
            avg_known_queue_len = float(sum_known_signals) / len(scheduled_task.vcluster.known_queue_len_tor[scheduled_task.target_tor]) 
            
            # ToR that is linked with a spine, will update the signal 
            for spine_idx in range(scheduled_task.vcluster.num_spines): 
                if scheduled_task.target_tor in scheduled_task.vcluster.known_queue_len_spine[spine_idx]:
                    scheduled_task.vcluster.known_queue_len_spine[spine_idx].update({scheduled_task.target_tor: avg_known_queue_len}) # Update SQ signals
                    spine_id = scheduled_task.vcluster.selected_spine_list[spine_idx]
                    num_msg_spine[spine_id] += 1
            scheduled_task.vcluster.log_known_queue_len_spine.append(avg_known_queue_len)
        else:
            scheduled_task.vcluster.log_known_queue_len_spine.append(0)
    return num_msg_spine

def run_scheduling(policy, data, k, distribution_name, sys_load):
    nr.seed()
    random.seed()
    start_time = time.time()

    policy_file_tag = get_policy_file_tag(policy, k)
    
    logger_tag_clusters = "summary_clusters_" + policy_file_tag + '_' + str(sys_load) + ".log"
    logger_tag_dcn = "summary_dcn_" + policy_file_tag + '_' + str(sys_load) + ".log"

    logger.add(result_dir + logger_tag_clusters, filter=lambda record: record["extra"]["task"] == logger_tag_clusters)
    log_handler_experiment = logger.bind(task=logger_tag_clusters)

    logger.add(result_dir + logger_tag_dcn, filter=lambda record: record["extra"]["task"] == logger_tag_dcn, level="INFO")
    log_handler_dcn = logger.bind(task=logger_tag_dcn)

    cluster_terminate_count = 0
    vcluster_list = []

    tenants = data['tenants']

    num_total_workers = data['tenants']['worker_count']

    tenants_maps = tenants['maps']
    worker_start_idx = 0 # Used for mapping local worker_id to global_worker_id
    for t in range(len(tenants_maps)):
        host_list = tenants_maps[t]['worker_to_host_map']
        cluster_id = tenants_maps[t]['app_id']
        
        vcluster = VirtualCluster(cluster_id, worker_start_idx, policy, host_list, sys_load)
        vcluster_list.append(vcluster)
        worker_start_idx += tenants_maps[t]['worker_count']
        
    in_transit_tasks = []

    partition_size_spine = num_tors / num_spines
    
    decision_tag = 0

    num_msg_spine = [0] * num_spines  
    num_msg_tor = [0] * num_tors
    switch_state_spine = [] * num_spines 
    switch_state_tor = [] * num_tors

    num_msg = 0
    idle_avg = 0

    # for i in range(num_workers):
    #     task_lists.append([])
    
    for spine_idx in range(num_spines):
        # idle_queue_spine.append(get_tor_partition_range_for_spine(spine_idx))
        # known_queue_len_spine.append({})
        switch_state_spine.append([0])

    for tor_idx in range(num_tors):
        # idle_queue_tor.append(get_worker_range_for_tor(tor_idx))
        # known_queue_len_tor.append({})
        switch_state_tor.append([0])

    #last_task_arrival = 0.0
    #task_idx = 0
    tick = 0
    while(cluster_terminate_count < len(vcluster_list)):
        for vcluster in vcluster_list:  
            num_msg_tor, num_msg_spine = process_tasks_fcfs(
                    vcluster=vcluster,
                    ticks_passed=1,
                    num_msg_tor=num_msg_tor,
                    num_msg_spine=num_msg_spine,
                    k=k)

        in_transit_tasks, arrived_tasks = process_network(in_transit_tasks, ticks_passed=1)

        for arrived_task in arrived_tasks:
            #print arrived_task.target_worker
            # if np.sum(arrived_task.vcluster.task_lists[arrived_task.target_worker]) > 0 and arrived_task.decision_tag == 0:
            #     print("ERROR! Spine :" + str(arrived_task.first_spine) + ", Tor :" + str(arrived_task.target_tor) + ", Worker :" + str(arrived_task.target_worker))
            #     exit(0)
            arrived_task.vcluster.log_task_wait_time.append(np.sum(arrived_task.vcluster.task_lists[arrived_task.target_worker])) # Task assigned to target worker should wait at least as long as pending load
            arrived_task.vcluster.log_task_transfer_time.append(arrived_task.transfer_time)
            arrived_task.vcluster.log_queue_len_signal_workers.append(arrived_task.vcluster.queue_lens_workers[arrived_task.target_worker])
            arrived_task.vcluster.log_queue_len_signal_tors.append(arrived_task.vcluster.queue_lens_tors[arrived_task.target_tor])
            arrived_task.vcluster.log_decision_type.append(arrived_task.decision_tag)

            arrived_task.vcluster.task_lists[arrived_task.target_worker].append(arrived_task.load)

        # A service might have different number of workers, so its Max Load will be different than others.
        # Process each service independently based on its load:
        for vcluster in vcluster_list:
            if (tick - vcluster.last_task_arrival) > vcluster.inter_arrival and vcluster.task_idx < len(vcluster.task_distribution): # New task arrives
                vcluster.last_task_arrival = tick

                num_idles = calculate_idle_count(vcluster.queue_lens_workers)
                vcluster.idle_counts.append(num_idles)
                
                load = vcluster.task_distribution[vcluster.task_idx] # Pick new task load
                new_task = Task(load, vcluster) 
                
                if policy == 'random':
                    scheduled_task = schedule_task_random(new_task)

                elif policy == 'pow_of_k':
                    scheduled_task = schedule_task_pow_of_k(new_task, k)
                    
                elif policy == 'pow_of_k_partitioned':
                    scheduled_task = schedule_task_pow_of_k_partitioned(new_task, k)

                elif policy == 'jiq':
                    # print(vcluster.idle_queue_spine)
                    # print(vcluster.idle_queue_tor)
                    # print(vcluster.known_queue_len_spine)
                    # print(vcluster.known_queue_len_tor)
                    scheduled_task, num_msg_tor, num_msg_spine = schedule_task_jiq(
                        new_task,
                        num_msg_tor, 
                        num_msg_spine)
                    # print(vcluster.queue_lens_tors)
                    # print(vcluster.queue_lens_workers)
                    # print("Spine :" + str(scheduled_task.first_spine) + ", Tor :" + str(scheduled_task.target_tor) + ", Worker :" + str(scheduled_task.target_worker))
                    # print('\n')
                elif policy == 'adaptive':
                    total_spine_knowledge = 0
                    total_idle_tors = 0
                    for entry in vcluster.idle_queue_spine:
                        total_spine_knowledge += len(entry)
                    for entry in vcluster.idle_queue_tor:
                        if len(entry) > 0:
                            total_idle_tors += 1
                    # if total_spine_knowledge != total_idle_tors:
                    #     print("Disaster")
                    #     exit(0)
                    # print(vcluster.idle_queue_spine)
                    # # print(vcluster.idle_queue_tor)
                    # print(vcluster.known_queue_len_spine)
                    # print(vcluster.known_queue_len_tor)
                    scheduled_task, num_msg_tor, num_msg_spine = schedule_task_adaptive(
                        new_task,
                        k,
                        num_msg_tor, 
                        num_msg_spine)
                    #print(vcluster.queue_lens_workers)
                    # print(max(vcluster.queue_lens_workers))
                    # print(vcluster.queue_lens_workers.index(max(vcluster.queue_lens_workers)))

                    # print("Decision: " + str(scheduled_task.decision_tag) + ", Spine: " + str(scheduled_task.first_spine) + ", Tor: " + str(scheduled_task.target_tor) + ", Worker: " + str(scheduled_task.target_worker))
                    # print('\n')
                num_msg_spine = update_switch_views(scheduled_task, num_msg_spine)
                in_transit_tasks.append(scheduled_task)
                vcluster.task_idx += 1
                if (vcluster.task_idx == len(vcluster.task_distribution) - 1):
                    cluster_terminate_count += 1
                    report_cluster_results(log_handler_experiment, policy_file_tag, sys_load, vcluster)

        tick += 1
 
        #  Take samples to capture fluctuations
        if (tick%(int(mean_task_small)) == 0):
            switch_state_tor, switch_state_spine = calculate_num_state(
                            policy,
                            switch_state_tor,
                            switch_state_spine,
                            vcluster,
                            vcluster_list)

        elapsed_time = time.time() - start_time
        
        if elapsed_time > LOG_PROGRESS_INTERVAL:
            log_handler_dcn.debug(policy_file_tag + ' progress log @' + str(sys_load) + ' Ticks passed: ' + str(tick) + ' Clusters done: ' + str(cluster_terminate_count))
            
            exp_duration_s = float(tick) / (10**7)
            max_state_spine = [max(x, default=0) for x in switch_state_spine]
            max_state_tor = [max(x, default=0) for x in switch_state_tor]
            msg_per_sec_spine = [x / exp_duration_s for x in num_msg_spine]
            msg_per_sec_tor = [x / exp_duration_s for x in num_msg_tor]
            log_handler_dcn.info(policy_file_tag + ' switch_state_spine_max @' + str(sys_load) + ':\n' +  str(pd.Series(max_state_spine).describe()))
            log_handler_dcn.info(policy_file_tag + ' switch_state_tor_max @' + str(sys_load) + ':\n' +  str(pd.Series(max_state_tor).describe()))
            log_handler_dcn.info(policy_file_tag + ' msg_per_sec_spine @' + str(sys_load) + ':\n' +  str(pd.Series(msg_per_sec_spine).describe()))
            log_handler_dcn.info(policy_file_tag + ' msg_per_sec_tor @' + str(sys_load) + ':\n' +  str(pd.Series(msg_per_sec_tor).describe()))    
            start_time = time.time()

    exp_duration_s = float(tick) / (10**7)
    msg_per_sec_spine = [x / exp_duration_s for x in num_msg_spine]
    msg_per_sec_tor = [x / exp_duration_s for x in num_msg_tor]
    #print switch_state_spine
    max_state_spine = [max(x, default=0) for x in switch_state_spine]
    
    mean_state_spine = [np.nanmean(x) for x in switch_state_spine if x]
    max_state_tor = [max(x, default=0) for x in switch_state_tor]
    mean_state_tor = [np.nanmean(x) for x in switch_state_tor if x]
    
    if policy != 'random':
        write_to_file('switch_state_spine_mean', policy_file_tag, sys_load, distribution_name,  mean_state_spine)
        write_to_file('switch_state_tor_mean', policy_file_tag, sys_load, distribution_name,  mean_state_tor)
        write_to_file('switch_state_spine_max', policy_file_tag, sys_load, distribution_name,  max_state_spine)
        write_to_file('switch_state_tor_max', policy_file_tag, sys_load, distribution_name,  max_state_tor)
        write_to_file('msg_per_sec_tor', policy_file_tag, sys_load, distribution_name, msg_per_sec_tor)
        write_to_file('msg_per_sec_spine', policy_file_tag, sys_load, distribution_name, msg_per_sec_spine)
    
def run_simulations(data):
    proc_list = []
    for task_distribution_name in task_time_distributions:
        print (task_distribution_name + " task distribution\n")
        for load in loads:
            print ("\nLoad: " + str(load))
            # random_proc = Process(target=run_scheduling, args=('random', 2, num_spines, task_distribution_name, load, ))
            # random_proc.start()

            pow_of_k_proc = Process(target=run_scheduling, args=('pow_of_k', data, 2, task_distribution_name, load, ))
            pow_of_k_proc.start()
            proc_list.append(pow_of_k_proc)

            pow_of_k_partitioned_proc = Process(target=run_scheduling, args=('pow_of_k_partitioned', data, 2, task_distribution_name, load, ))
            pow_of_k_partitioned_proc.start()
            proc_list.append(pow_of_k_partitioned_proc)

            jiq_proc = Process(target=run_scheduling, args=('jiq', data, 2, task_distribution_name, load, ))
            jiq_proc.start()
            proc_list.append(jiq_proc)
            
            adaptive_proc = Process(target=run_scheduling, args=('adaptive', data, 2, task_distribution_name, load, ))
            adaptive_proc.start()
            proc_list.append(adaptive_proc)

if __name__ == "__main__":
    data = read_dataset()
    run_simulations(data)


