"""Usage:
single_layer_lb.py -d <working_dir> -p <policy> -l <load> -k <k_value>  -t <task_distribution> -i <id> [--colocate]

single_layer_lb.py -h | --help
single_layer_lb.py -v | --version

Arguments:
  -d <working_dir> Directory containing dataset which is also used for result files
  -p <policy>  Scheduling policy to simulate (pow_of_k|pow_of_k_partitioned|jiq|adaptive)
  -l <load> System load
  -k <k_value> K: number of samples each switch takes for making decisions
  -i <run_id> Run ID used for multiple runs of single dataset
  -t <task_distribution> Distribution name for generated tasks (bimodal|trimodal)
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

from utils import *
from vcluster import VirtualCluster
from task import Task

#FWD_TIME_TICKS = 0.0015 # Number of 0.1us ticks to pass in sim steps...
FWD_TIME_TICKS = 0.002 # Number of 0.1us ticks to pass in sim steps...
LOG_PROGRESS_INTERVAL = 600 # Dump some progress info periodically (in seconds)
result_dir = "./"
exp_running_time_ms = 3

def report_cluster_results(log_handler, policy_file_tag, sys_load, vcluster, run_id, is_colocate=False):
    log_handler.info(policy_file_tag + ' Finished cluster with ID:' + str(vcluster.cluster_id) +' wait_times @' + str(sys_load) + ':\n' +  str(pd.Series(vcluster.log_task_wait_time).describe()))
    log_handler.info(policy_file_tag + ' Finished cluster with ID:' + str(vcluster.cluster_id) + ' transfer_times @' + str(sys_load) + ':\n' +  str(pd.Series(vcluster.log_task_transfer_time).describe()))
    write_to_file(result_dir, 'wait_times', policy_file_tag, sys_load, vcluster.task_distribution_name,  vcluster.log_task_wait_time, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)
    write_to_file(result_dir, 'transfer_times', policy_file_tag, sys_load, vcluster.task_distribution_name, vcluster.log_task_transfer_time, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)
    write_to_file(result_dir, 'idle_count', policy_file_tag, sys_load, vcluster.task_distribution_name, vcluster.idle_counts, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)
    write_to_file(result_dir, 'queue_lens', policy_file_tag, sys_load, vcluster.task_distribution_name,  vcluster.log_queue_len_signal_workers, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)
    if vcluster.policy == 'adaptive' or vcluster.policy == 'jiq':
            write_to_file(result_dir, 'decision_type', policy_file_tag, sys_load, vcluster.task_distribution_name, vcluster.log_decision_type, run_id, cluster_id=vcluster.cluster_id, is_colocate=is_colocate)
 
def calculate_num_state(policy, switch_state_spine, vcluster, vcluster_list):
    for spine_id in range(1):
        # We append the switches with updated number of states to the global switch_state_spine[spine_idx]
        total_states_spine_switch = 0
        for vcluster_x in vcluster_list:
            if spine_id in vcluster_x.selected_spine_list:
                spine_idx = vcluster_x.selected_spine_list.index(spine_id)
                if policy == 'pow_of_k':
                    total_states_spine_switch += vcluster_x.num_workers
                elif policy == 'jiq':
                    total_states_spine_switch += len(vcluster_x.idle_queue_spine[spine_idx])
                elif policy == 'adaptive':
                    total_states_spine_switch += len(vcluster_x.idle_queue_spine[spine_idx])
                    total_states_spine_switch += vcluster_x.num_workers
        switch_state_spine[spine_id].append(total_states_spine_switch)
    return switch_state_spine

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

def jiq_server_process(vcluster, num_msg_tor, num_msg_spine, k, worker_idx):
    min_idle_queue = float("inf")

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
    return vcluster, num_msg_tor, num_msg_spine

# In centralized simulations idle process for server in adaptive is identical to jiq
def adaptive_server_process(vcluster, num_msg_tor, num_msg_spine, k, worker_idx):
    min_idle_queue = float("inf")

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
    return vcluster, num_msg_tor, num_msg_spine

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
                # Conversion for mapping to cluster's local lists
                
                if (vcluster.policy == 'pow_of_k'): # Random and JIQ do not use this part
                    if vcluster.policy == 'pow_of_k':
                        # Update worker queue len at all of the spines
                        for spine_id in vcluster.selected_spine_list:
                            num_msg_spine[spine_id] += 1 

                else: #JIQ and adaptive
                    if vcluster.policy == 'jiq': # JIQ
                        if vcluster.queue_lens_workers[i] == 0: # Process for when a server becomes idle 
                            vcluster, num_msg_tor, num_msg_spine = jiq_server_process(
                                vcluster, 
                                num_msg_tor,
                                num_msg_spine,
                                k,
                                i)
                    elif vcluster.policy == 'adaptive': # Adaptive
                        if vcluster.queue_lens_workers[i] == 0: # Process for when a server becomes idle 
                            vcluster, num_msg_tor, num_msg_spine = adaptive_server_process(
                                vcluster,
                                num_msg_tor,
                                num_msg_spine,
                                k,
                                i)
                        else:
                            for spine_id in vcluster.selected_spine_list:
                                num_msg_spine[spine_id] += 1  
            if remaining_time >= 0:     # Continue loop (processing other tasks) only if remaining time is negative
                break
    return num_msg_tor, num_msg_spine

def schedule_task_random(new_task):
    # Simulating arrival at a spine randomly
    target_spine = random.randrange(new_task.vcluster.num_spines)  
    
    target_tor = random.randrange(new_task.vcluster.num_tors) # Dummy, not used in random as it randomly selects the *workers* don't care about ToRs
    target_worker = nr.randint(0, new_task.vcluster.num_workers) # Make decision
    
    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task

def schedule_task_pow_of_k(new_task, k):
    vcluster = new_task.vcluster
    num_spines = vcluster.num_spines
    num_workers = vcluster.num_workers
    queue_lens_workers = vcluster.queue_lens_workers

    target_spine = 0  # Simulating arrival at the centralized spine scheduler
            
    # Make the decision at spine:
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

    target_tor = vcluster.tor_id_unique_list.index(get_tor_id_for_host(vcluster.host_list[target_worker]))
    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task

def schedule_task_jiq(new_task, num_msg_tor, num_msg_spine):
    target_spine = 0  # Simulating arrival at the centralized spine scheduler
            
    if new_task.vcluster.idle_queue_spine[target_spine]: # Spine scheduler is aware of some idle workers
        target_worker = new_task.vcluster.idle_queue_spine[target_spine].pop(0)
    else:
        worker_indices = range(0, new_task.vcluster.num_workers)
        target_worker = random.choice(worker_indices)

    target_tor = new_task.vcluster.tor_id_unique_list.index(get_tor_id_for_host(new_task.vcluster.host_list[target_worker]))
    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task, num_msg_tor, num_msg_spine

def schedule_task_adaptive(new_task, k, num_msg_tor, num_msg_spine):
    vcluster = new_task.vcluster
    num_spines = vcluster.num_spines
    num_workers = vcluster.num_workers
    queue_lens_workers = vcluster.queue_lens_workers
    
    target_spine = 0  # Simulating arrival at the centralized spine scheduler
    target_spine_id = new_task.vcluster.selected_spine_list[target_spine]

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

    target_tor = new_task.vcluster.tor_id_unique_list.index(get_tor_id_for_host(new_task.vcluster.host_list[target_worker]))
    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task, num_msg_tor, num_msg_spine

def update_switch_views(scheduled_task):
    scheduled_task.vcluster.queue_lens_workers[scheduled_task.target_worker] += 1

def run_scheduling(policy, data, k, task_distribution_name, sys_load, run_id, is_colocate):
    nr.seed()
    random.seed()
    start_time = time.time()

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
    worker_start_idx = 0 # Used for mapping local worker_id to global_worker_id
    
    
    if task_distribution_name == "bimodal":
            mean_task_time = (mean_task_small + mean_task_medium) / 2
    elif task_distribution_name == "trimodal":
        mean_task_time = (mean_task_small + mean_task_medium + mean_task_large) / 3
    elif task_distribution_name == "exponential":
        mean_task_time = mean_exp_task
    
    FWD_TIME_TICKS = ((mean_task_time / num_total_workers) / sys_load) / 2 # double the maximum frequency to capture all events

    for t in range(len(tenants_maps)):
        host_list = tenants_maps[t]['worker_to_host_map']
        cluster_id = tenants_maps[t]['app_id']
        
        vcluster = VirtualCluster(cluster_id,
            worker_start_idx,
            policy,
            host_list,
            sys_load,
            task_distribution_name=task_distribution_name, 
            is_single_layer=True)

        vcluster_list.append(vcluster)
        worker_start_idx += tenants_maps[t]['worker_count']
    #print ("MIN: " + str(min_inter_arrival))
    in_transit_tasks = []
    
    decision_tag = 0

    num_msg_spine = [0] * 1  
    num_msg_per_sec_spine = [] * 1  
    num_task_per_sec_spine = [] * 1
    num_msg_tor = [0] * num_tors
    num_task_spine = [0] * 1  
    switch_state_spine = [] * 1 
    switch_state_tor = [] * num_tors
    
    last_num_msg_spine = num_msg_spine.copy()
    last_num_task_spine = num_task_spine.copy()

    for spine_idx in range(1):
        switch_state_spine.append([0])
        num_msg_per_sec_spine.append([])
        num_task_per_sec_spine.append([])
    elapsed_ticks=0
    tick = 0
    while(cluster_terminate_count < len(vcluster_list)):
        for vcluster in vcluster_list:  
            num_msg_tor, num_msg_spine = process_tasks_fcfs(
                    vcluster=vcluster,
                    ticks_passed=FWD_TIME_TICKS,
                    num_msg_tor=num_msg_tor,
                    num_msg_spine=num_msg_spine,
                    k=k)

        in_transit_tasks, arrived_tasks = process_network(in_transit_tasks, ticks_passed=FWD_TIME_TICKS)

        for arrived_task in arrived_tasks:
            arrived_task.vcluster.log_task_wait_time.append(np.sum(arrived_task.vcluster.task_lists[arrived_task.target_worker])) # Task assigned to target worker should wait at least as long as pending load
            arrived_task.vcluster.log_task_transfer_time.append(arrived_task.transfer_time)
            arrived_task.vcluster.log_queue_len_signal_workers.append(arrived_task.vcluster.queue_lens_workers[arrived_task.target_worker])
            arrived_task.vcluster.log_decision_type.append(arrived_task.decision_tag)
            arrived_task.vcluster.task_lists[arrived_task.target_worker].append(arrived_task.load)

        # A service might have different number of workers, so its Max Load will be different than others.
        # Process each service independently based on its load:
        for vcluster in vcluster_list:
            if (tick - vcluster.last_task_arrival) > vcluster.inter_arrival and vcluster.task_idx < len(vcluster.task_distribution): # New task arrives
                vcluster.last_task_arrival = tick

                num_idles = calculate_idle_count(vcluster.queue_lens_workers)
                vcluster.idle_counts.append(num_idles)
                
                load = vcluster.task_distribution[vcluster.task_idx] # Pick new task load (load is execution time)
                new_task = Task(load, vcluster)
                
                if policy == 'random':
                    scheduled_task = schedule_task_random(new_task)

                elif policy == 'pow_of_k':
                    scheduled_task = schedule_task_pow_of_k(new_task, k)
                    
                elif policy == 'pow_of_k_partitioned':
                    scheduled_task = schedule_task_pow_of_k_partitioned(new_task, k)

                elif policy == 'jiq':
                    scheduled_task, num_msg_tor, num_msg_spine = schedule_task_jiq(
                        new_task,
                        num_msg_tor, 
                        num_msg_spine)

                elif policy == 'adaptive':
                    scheduled_task, num_msg_tor, num_msg_spine = schedule_task_adaptive(
                        new_task,
                        k,
                        num_msg_tor, 
                        num_msg_spine)
                    
                num_task_spine[scheduled_task.global_spine_id] += 1

                update_switch_views(scheduled_task)
                in_transit_tasks.append(scheduled_task)
                vcluster.task_idx += 1
                if (vcluster.task_idx == len(vcluster.task_distribution) - 1):
                    cluster_terminate_count += 1
                    #report_cluster_results(log_handler_experiment, policy_file_tag, sys_load, vcluster, run_id, is_colocate)
                    if cluster_terminate_count == 1: # When the first cluster finishes executing we report the DCN wide results
                        exp_duration_s = float(tick) / (10**7)
                        msg_per_sec_spine = [x / exp_duration_s for x in num_msg_spine]
                        #print switch_state_spine
                        max_state_spine = [max(x, default=0) for x in switch_state_spine]
                        
                        mean_state_spine = [np.nanmean(x) for x in switch_state_spine if x]
                        max_state_tor = [max(x, default=0) for x in switch_state_tor]
                        mean_state_tor = [np.nanmean(x) for x in switch_state_tor if x]
                        task_per_sec_spine = [x / exp_duration_s for x in num_task_spine]
                        write_to_file(result_dir, 'task_per_sec_spine', policy_file_tag, sys_load, task_distribution_name, num_task_per_sec_spine[0], run_id, is_colocate=is_colocate)
                        if policy != 'random':
                            write_to_file(result_dir, 'switch_state_spine_mean', policy_file_tag, sys_load, task_distribution_name,  mean_state_spine, run_id, is_colocate=is_colocate)
                            write_to_file(result_dir, 'switch_state_tor_mean', policy_file_tag, sys_load, task_distribution_name,  mean_state_tor, run_id, is_colocate=is_colocate)
                            write_to_file(result_dir, 'switch_state_spine_max', policy_file_tag, sys_load, task_distribution_name,  max_state_spine, run_id, is_colocate=is_colocate)
                            write_to_file(result_dir, 'switch_state_tor_max', policy_file_tag, sys_load, task_distribution_name,  max_state_tor, run_id, is_colocate=is_colocate)
                            write_to_file(result_dir, 'msg_per_sec_spine', policy_file_tag, sys_load, task_distribution_name, num_msg_per_sec_spine[0], run_id, is_colocate=is_colocate)                   
                
        tick += FWD_TIME_TICKS
        
        #  Take samples to capture fluctuations
        if (tick - elapsed_ticks >= 100): # every 10 us
            elapsed_ticks = tick

            # range should be over all of the spines here in centralized we assume only 1 spine scheduler at index 0
            num_msg_per_sec_spine[0].append((10**5) * (num_msg_spine[0] - last_num_msg_spine[0]))
            num_task_per_sec_spine[0].append((10**5) * (num_task_spine[0]- last_num_task_spine[0]))
            last_num_msg_spine = num_msg_spine.copy()
            last_num_task_spine = num_task_spine.copy()
        
        if (tick >= (exp_running_time_ms * 10**4)): # Terminate and write results to file
            exp_duration_s = float(tick) / (10**7)
            switch_state_spine = calculate_num_state(
                            policy,
                            switch_state_spine,
                            vcluster,
                            vcluster_list)

            msg_per_sec_spine = [x / exp_duration_s for x in num_msg_spine]
            #print switch_state_spine
            max_state_spine = [max(x, default=0) for x in switch_state_spine]
            mean_state_spine = [np.nanmean(x) for x in switch_state_spine if x]
            max_state_tor = [max(x, default=0) for x in switch_state_tor]
            mean_state_tor = [np.nanmean(x) for x in switch_state_tor if x]
            task_per_sec_spine = [x / exp_duration_s for x in num_task_spine]
            
            write_to_file(result_dir, 'task_per_sec_spine', policy_file_tag, sys_load, task_distribution_name, num_task_per_sec_spine[0], run_id, is_colocate=is_colocate)
            
            if policy != 'random':
                write_to_file(result_dir, 'switch_state_spine_mean', policy_file_tag, sys_load, task_distribution_name,  mean_state_spine, run_id, is_colocate=is_colocate)
                write_to_file(result_dir, 'switch_state_tor_mean', policy_file_tag, sys_load, task_distribution_name,  mean_state_tor, run_id, is_colocate=is_colocate)
                write_to_file(result_dir, 'switch_state_spine_max', policy_file_tag, sys_load, task_distribution_name,  max_state_spine, run_id, is_colocate=is_colocate)
                write_to_file(result_dir, 'switch_state_tor_max', policy_file_tag, sys_load, task_distribution_name,  max_state_tor, run_id, is_colocate=is_colocate)
                write_to_file(result_dir, 'msg_per_sec_spine', policy_file_tag, sys_load, task_distribution_name, num_msg_per_sec_spine[0], run_id, is_colocate=is_colocate)     
            exit(0)
        elapsed_time_log = time.time() - start_time

        if elapsed_time_log > LOG_PROGRESS_INTERVAL:
            log_handler_dcn.debug(policy_file_tag + ' progress log @' + str(sys_load) + ' Ticks passed: ' + str(tick) + ' Clusters done: ' + str(cluster_terminate_count))
            exp_duration_s = float(tick) / (10**7)
            max_state_spine = [max(x, default=0) for x in switch_state_spine]
            max_state_tor = [max(x, default=0) for x in switch_state_tor]
            msg_per_sec_spine = [x / exp_duration_s for x in num_msg_spine]
            
            task_per_sec_spine = [x / exp_duration_s for x in num_task_spine]

            log_handler_dcn.info(policy_file_tag + ' task_per_sec_spine @' + str(sys_load) + ':\n' +  str(pd.Series(num_task_per_sec_spine[0]).describe()))

            log_handler_dcn.info(policy_file_tag + ' switch_state_spine_max @' + str(sys_load) + ':\n' +  str(pd.Series(max_state_spine).describe()))
            log_handler_dcn.info(policy_file_tag + ' msg_per_sec_spine @' + str(sys_load) + ':\n' +  str(pd.Series(num_msg_per_sec_spine[0]).describe()))
            start_time = time.time()

if __name__ == "__main__":
    arguments = docopt.docopt(__doc__, version='1.0')
    working_dir = arguments['-d']
    # global result_dir
    result_dir = working_dir
    policy = arguments['-p']
    load = float(arguments['-l'])
    k_value = int(arguments['-k'])
    run_id = arguments['-i']
    task_distribution_name = arguments['-t']
    
    is_colocate = arguments.get('--colocate', False)

    print (policy)
    data = read_dataset(working_dir, is_colocate)
    run_scheduling(policy, data, k_value, task_distribution_name, load, run_id, is_colocate)

