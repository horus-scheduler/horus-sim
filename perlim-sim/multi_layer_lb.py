import numpy.random as nr
import numpy as np
import math
import random 
import sys
from multiprocessing import Process, Queue, Value, Array
from loguru import logger


from utils import *
from vcluster import VirtualCluster

# 100 Machines M=2
# num_pods = 2
# spines_per_pod = 5
# tors_per_pod = 10
# hosts_per_tor = 5

# 200 Machines M=5
# num_pods = 4
# spines_per_pod = 1
# tors_per_pod = 5
# workers_per_tor = 10

# 200 Machines M=5

# 10 Machines M=2
# num_pods = 1
# spines_per_pod = 2
# tors_per_pod = 5
# workers_per_tor = 2

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

class Task:  
    def __init__(self, task_id, load, vcluster): 
        self.vcluster = vcluster
        self.task_id = vcluster.task_id
        self.load = load
        self.decision_tag = 0 

    def set_decision(self, first_spine, target_tor, target_worker): 
        self.target_worker = target_worker
        self.target_tor = target_tor
        self.first_spine = first_spine

        self.global_worker_id = self.vcluster.worker_start_idx + target_worker 
        self.global_host_id = self.vcluster.host_list[target_worker]
        self.global_spine_id = self.vcluster.selected_spine_list[first_spine]
        self.global_tor_id = self.vcluster.tor_id_unique_list[target_tor]

        self.network_time = calculate_network_time(first_spine, target_worker) # This one changes during process
        self.num_hops = calculate_num_hops(first_spine, target_worker)
        self.transfer_time = self.network_time

def jiq_server_process(vcluster, num_msg_tor, num_msg_spine, num_spines, k, worker_idx, tor_idx):
    min_idle_queue = float("inf")
    sample_indices = random.sample(range(0, vcluster.num_spines), k) # Sample k spines
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
        if tor_idx in idle_queue_spine[spine_idx]:
            already_paired = True

    if not already_paired:
        idle_queue_spine[target_spine_idx].append(tor_idx) # Add ToR to the idle queue of selected spine
        target_spine_id = vcluster.selected_spine_list[target_spine_idx]
        num_msg_spine[target_spine_id] += 1 # 1 msg for updating spine idle queue
    return vcluster, num_msg_tor, num_msg_spine

def adaptive_server_process(idle_queue_tor, idle_queue_spine, known_queue_len_tor, known_queue_len_spine, num_msg_tor, num_msg_spine, num_spines, k, worker_idx):
    min_idle_queue = float("inf")
    sample_indices = random.sample(range(0, num_spines), k) # Sample k dispatchers
    #print sample_indices
    for idx in sample_indices:  # Find the sampled spine with min idle queue len (k msgs)
        sample = len(idle_queue_spine[idx])
        num_msg_spine[idx] += 1
        if sample < min_idle_queue:
            min_idle_queue = sample
            target_spine = idx
    tor_idx = get_tor_idx_for_worker(worker_idx)
    idle_queue_tor[tor_idx].append(worker_idx) # Add idle worker to tor (1 msg)
    num_msg_tor[tor_idx] += 1 # for removing SQ from ToR (and also adds the server to IQ of ToR)

    # TODO @parham: Remove idle worker from list of SQ signals? Uncomment below!
    # if worker_idx in known_queue_len_tor[tor_idx]:
    #     del known_queue_len_tor[tor_idx][worker_idx] # Remove sq entery from tor
    idle_queue_spine[target_spine].append(tor_idx) # Add tor to the idle queue of that spine (1 msg)
    num_msg_spine[target_spine] += 1 # for updating the spine idle queue
    
    # TODO @parham: Another config as discussed in documents is to switch to JIQ and remove all SQs when an idle queue available
    # Uncomment below!
    #known_queue_len_tor[tor_idx].clear() # Switched to JIQ
    #known_queue_len_spine[target_spine].clear() # Switched to JIQ

    for spine_idx in range(num_spines):
        if tor_idx in known_queue_len_spine[spine_idx]:
            # print (known_queue_len)
            # print("deleted " + str(server_idx) + " with load: " + str(known_queue_len[d][server_idx]))
            del known_queue_len_spine[spine_idx][tor_idx] # Delete sq entery from previously linked spine (1msg)
            num_msg_spine[spine_idx] += 1 # for removing SQ from other dispatcher
    return idle_queue_tor, idle_queue_spine, known_queue_len_tor, known_queue_len_spine, num_msg_tor, num_msg_spine

def process_tasks_fcfs(
    policy,
    inter_arrival,
    task_lists,
    queue_lens_workers,
    queue_lens_tors,
    num_msg_tor=None,
    num_msg_spine=None,
    msg_per_done=1,
    idle_queue_tor=None,
    idle_queue_spine=None,
    num_spines=1,
    k=2,
    known_queue_len_tor=None,
    known_queue_len_spine=None
    ):
    
    task_lists = vcluster.task_lists
    inter_arrival = vcluster.inter_arrival
    queue_lens_workers = vcluster.queue_lens_workers
    queue_lens_tors = vcluster.queue_lens_tors
    host_list = vcluster.host_list
    # num_msg_tor = vcluster.num_msg_tor
    # num_msg_spine = vcluster.num_msg_spine
    num_spines = vcluster.num_spines

    for i in range(len(task_lists)):
        while task_lists[i]:    # while there are any tasks in list
            remaining_time = task_lists[i][0] - inter_arrival   # First task in list is being executed
            task_lists[i][0] = max(0, remaining_time) # If remaining time from task is negative another task is could be executed during the interval
            if task_lists[i][0] == 0:   # If finished executing task
                task_lists[i].pop(0)        # Remove from list
                queue_lens_workers[i] -= 1       # Decrement worker queue len

                tor_id = get_tor_idx_for_host(host_list[i])
                # Conversion for mapping to cluster's local lists
                tor_idx = vcluster.tor_id_unique_list.index(tor_id)

                queue_lens_tors[tor_idx] = calculate_tor_queue_len(tor_id, queue_lens_workers, host_list)

                # if queue_lens_tors[tor_idx] < 0:
                #     print ("ERROR")
                #     print("Tor: " + str(tor_idx) + "worker: " + str(i))
                if (policy == 'pow_of_k') or (policy == 'pow_of_k_partitioned'): # Random and JIQ do not use this part
                    num_msg_tor[tor_id] += 1 # Update worker queuelen at ToR
                    if policy == 'pow_of_k':
                        # Update ToR queue len at all of the spines
                        for spine_id in vcluster.selected_spine_list:
                            num_msg_spine[spine_id] += 1 
                    else: # Only update the designated spine
                        mapped_spine = vcluster.tor_spine_map[tor_idx]
                        num_msg_spine[mapped_spine] += 1
                else: #JIQ and adaptive
                    if policy == 'jiq': # JIQ
                        if queue_lens_workers[i] == 0: # Process for when a server becomes idle 
                            vcluster, num_msg_tor, num_msg_spine = jiq_server_process(
                                vcluster, 
                                num_msg_tor,
                                num_msg_spine,
                                num_spines,
                                k,
                                i,
                                tor_idx)
                    elif policy == 'adaptive': # Adaptive
                        if queue_lens_workers[i] == 0: # Process for when a server becomes idle 
                            idle_queue_tor, idle_queue_spine, known_queue_len_tor, known_queue_len_spine, num_msg_tor, num_msg_spine = adaptive_server_process(
                                idle_queue_tor,
                                idle_queue_spine,
                                known_queue_len_tor,
                                known_queue_len_spine,
                                num_msg_tor,
                                num_msg_spine,
                                num_spines,
                                k,
                                i)
                        else:
                            if i in known_queue_len_tor[tor_idx]: # Update queue len of worker at ToR
                                known_queue_len_tor[tor_idx].update({i: queue_lens_workers[i]})  
                                num_msg_tor[tor_idx] += 1 
                            for spine_idx in range(num_spines): # ToR that is paired with a spine, will update the signal 
                                if tor_idx in known_queue_len_spine[spine_idx]:
                                    known_queue_len_spine[spine_idx].update({tor_idx: queue_lens_tors[tor_idx]}) # Update SQ signals
                                    num_msg_spine[spine_idx] += 1
                        
            if remaining_time >= 0:     # Continue loop (processing other tasks) only if remaining time is negative
                break

    return task_lists, queue_lens_workers, queue_lens_tors, num_msg_tor, num_msg_spine, idle_queue_tor, idle_queue_spine, known_queue_len_tor, known_queue_len_spine

def schedule_task_random(new_task):
    # Emulating arrival at a spine randomly
    target_spine = random.randrange(new_task.vcluster.num_spines)  
    
    target_tor = random.randrange(new_task.vcluster.num_tors) # Dummy, not used in random as it randomly selects the *workers* don't care about ToRs
    target_worker = nr.randint(0, new_task.vcluster.num_workers) # Make decision
    
    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task

def schedule_task_pow_of_k(new_task, k, queue_lens_workers, queue_lens_tors):
    target_spine = random.randrange(num_spines)  # Emulating arrival at a spine randomly
            
    # Make the decision at spine:
    min_load = float("inf")
    sample_indices = random.sample(range(0, num_tors), k) # Info about all tors available at every spine
    for idx in sample_indices:
        sample = queue_lens_tors[idx]
        if sample < min_load:
            min_load = sample
            target_tor = idx

    # Make the decision at ToR:
    min_load = float("inf")
    worker_indices = get_worker_range_for_tor(target_tor)
    sample_indices = random.sample(worker_indices, k) # Sample from workers connected to that ToR
    for idx in sample_indices:
        sample = queue_lens_workers[idx]
        if sample < min_load:
            min_load = sample
            target_worker = idx

    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task

def schedule_task_pow_of_k_partitioned(new_task, k, queue_lens_workers, queue_lens_tors):
    target_spine = random.randrange(num_spines)  # Emulating arrival at a spine randomly
    # Make decision at Spine level:
    min_load = float("inf")
    tor_indices = get_tor_partition_range_for_spine(target_spine)
    sample_indices = random.sample(tor_indices, k) # k samples from tors available to that spine
    
    for idx in sample_indices:
        sample = queue_lens_tors[idx]
        if sample < min_load:
            min_load = sample
            target_tor = idx

    # Make the decision at ToR:
    min_load = float("inf")
    worker_indices = get_worker_range_for_tor(target_tor)
    sample_indices = random.sample(worker_indices, k) # Sample from workers connected to that ToR
    for idx in sample_indices:
        sample = queue_lens_workers[idx]
        if sample < min_load:
            min_load = sample
            target_worker = idx
    
    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task

def schedule_task_jiq(new_task, queue_lens_workers, queue_lens_tors, idle_queue_tor, idle_queue_spine, num_msg_tor, num_msg_spine):
    target_spine = random.randrange(num_spines)  # Emulating arrival at a spine switch randomly
            
    # Make decision at spine level:
    if idle_queue_spine[target_spine]:  # Spine is aware of some tors with idle wokrers
        target_tor = idle_queue_spine[target_spine].pop(0)
    else:   # No tor with idle worker is known, dispatch to a random tor
        #target_tor = random.choice(get_tor_partition_range_for_spine(target_spine)) Limit to pod
        target_tor = nr.randint(0, num_tors) # Can forward to any ToR

        for spine_idx, idle_tors in enumerate(idle_queue_spine):
            if target_tor in idle_tors:   # Tor was previously presented as idle to one of spines
                if len(idle_queue_tor[target_tor]) <= 1: # After sending this, tor is no longer idle and removes itself from that spine's list
                    idle_tors.remove(target_tor)
                    num_msg_spine[spine_idx] += 1

    # Make decision at tor level:           
    if idle_queue_tor[target_tor]: # Tor is aware of some idle workers
        target_worker = idle_queue_tor[target_tor].pop(0)
    else:
        target_worker = nr.randint(0, num_workers)
        if target_worker in idle_queue_tor[target_tor]:
            idle_queue_tor[target_tor].remove(target_worker)

    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task, idle_queue_tor, idle_queue_spine, num_msg_tor, num_msg_spine

def schedule_task_adaptive(new_task, k, queue_lens_workers, queue_lens_tors, idle_queue_tor, idle_queue_spine, known_queue_len_tor, known_queue_len_spine, num_msg_tor, num_msg_spine):
    partition_size_spine = num_tors / num_spines
    # Make decision at spine layer:
    target_spine = random.randrange(num_spines)  # Emulating arrival at a spine switch randomly
    
    if len(idle_queue_spine[target_spine]) > 0:  # Spine is aware of some tors with idle servers
        target_tor = idle_queue_spine[target_spine].pop(0)
        new_task.decision_tag = 0
    else:   # No tor with idle server is known
        already_paired = False
        sq_update = False
        if (len(known_queue_len_spine[target_spine]) < partition_size_spine): # Scheduer still trying to get more queue len info
                
                random_tor = nr.randint(0, num_tors)
                for spine_idx in range(num_spines):
                    if random_tor in known_queue_len_spine[spine_idx]:
                        already_paired = True
                if len(idle_queue_tor[random_tor]) > 0: # If ToR is aware of some idle worker, it's already paired with another spine (registered in their Idle Queue)
                    already_paired = True

                if not already_paired: # Each tor queue len should be available at one spine only
                    sq_update = True

        if (len(known_queue_len_spine[target_spine]) > k): # Do shortest queue if enough info available    
            sample_tors = random.sample(list(known_queue_len_spine[target_spine]), k) # k samples from ToR queue lenghts available to that spine
            #print (sample_workers)
            for tor_idx in sample_tors:
                sample_queue_len = known_queue_len_spine[target_spine][tor_idx]
                if sample_queue_len < min_load:
                    min_load = sample_queue_len
                    target_tor = tor_idx
            new_task.decision_tag = 1 # SQ-based decision
        else: # Randomly select a ToR from all of the available servers
            target_tor = nr.randint(0, num_tors)
            # for spine_idx in range(num_spines):
            #     if target_tor in known_queue_len_spine[spine_idx]:
            #         already_paired = True
            # if len(idle_queue_tor[target_tor]) > 0:
            #     already_paired = True
            # if not already_paired: # Each tor queue len should be available at one spine only
            #     known_queue_len_spine[target_spine].update({target_tor: None}) # Add SQ signal
            #     num_msg_spine += 1 # Reply from tor to add SQ signal
            new_task.decision_tag = 2 # Random-based decision
        if sq_update:
            known_queue_len_spine[target_spine].update({random_tor: float("inf")}) # This is to indicate that spine will track queue len of ToR from now on
            num_msg_tor[random_tor] += 1 # 1 msg sent to ToR

            if known_queue_len_tor[target_tor]: # Any SQ signal available to ToR at the time
                sum_known_signals = 0
                for worker in known_queue_len_tor[target_tor]:
                    sum_known_signals += known_queue_len_tor[target_tor][worker]
                    avg_known_queue_len = float(sum_known_signals) / len(known_queue_len_tor[target_tor]) 
                known_queue_len_spine[target_spine].update({random_tor: avg_known_queue_len}) # Add SQ signal
            num_msg_spine[target_spine] += 1 # msg from tor to add SQ signal

        for spine_idx, idle_tor_list in enumerate(idle_queue_spine):
            if target_tor in idle_tor_list:   # tor that gets a random-assigned task removes itself from the idle queue it has joined
                idle_tor_list.remove(target_tor)
                num_msg_spine[spine_idx] += 1 # "Remove" msg from tor
        
    # Make decision at ToR layer:
    min_load = float("inf")
    worker_indices = get_worker_range_for_tor(target_tor)
    if len(idle_queue_tor[target_tor]) > 0:  # Tor is aware of some idle workers
        target_worker = idle_queue_tor[target_tor].pop(0)

    else: # No idle worker
        already_paired = False
        sq_update = False
        if (len(known_queue_len_tor[target_tor]) < len(worker_indices)): # Tor scheduer still trying to get more queue len info
                num_msg_tor[target_tor] += 1 # Requesting for SQ signal
                random_worker = random.choice(worker_indices)
                sq_update = True
        if (len(known_queue_len_tor[target_tor]) > k): # Shortest queue if enough info is available
            sample_workers = random.sample(list(known_queue_len_tor[target_tor]), k) # k samples from worker queue lenghts available
            for worker_idx in sample_workers:
                sample_queue_len = known_queue_len_tor[target_tor][worker_idx]
                if sample_queue_len < min_load:
                    min_load = sample_queue_len
                    target_worker = worker_idx
            
        else: # Randomly select a worker from all of the available workers
            target_worker = random.choice(worker_indices)
            #known_queue_len_tor[target_tor].update({target_worker: None}) # Add SQ signal
        if sq_update:
            known_queue_len_tor[target_tor].update({random_worker: queue_lens_workers[target_worker]}) # Add SQ signal
            num_msg_tor[target_tor] += 1 # msg adding SQ signal

    new_task.set_decision(target_spine, target_tor, target_worker)
    return new_task, idle_queue_tor, idle_queue_spine, known_queue_len_tor, known_queue_len_spine, num_msg_tor, num_msg_spine

def run_scheduling(policy, k, num_spines, distribution, distribution_name, inter_arrival, sys_load):
    nr.seed()
    random.seed()
    
    vcluster_list = []


    tenants = data['tenants']
    tenants_maps = tenants['maps']
    worker_start_idx = 0 # Used for mapping local worker_id to global_worker_id
    for t in range(len(tenants_maps)):
        host_list = tenants_maps[t]['worker_to_host_map']
        cluster_id = tenants_maps[t]['app_id']
        vcluster = VirtualCluster(cluster_id, worker_start_idx, policy, host_list, sys_load, distribution)
        vcluster_list.append(vcluster)

        worker_start_idx += tenants_maps[t]['worker_count']

    queue_lens_workers = [0] * num_workers
    queue_lens_tors = [0.0] * num_tors

    task_lists = [] * num_workers
    
    #idle_queue_tor = [] * num_tors
    #idle_queue_spine = [] * num_spines

    #known_queue_len_spine = [] * num_spines  # For each spine, list of maps between torID and average queueLen if ToR
    #known_queue_len_tor = [] * num_tors # For each tor, list of maps between workerID and queueLen
    
    log_queue_len_signal_tors = []  # For analysis only 
    log_queue_len_signal_workers = [] 
    log_task_wait_time = []
    log_task_transfer_time = []
    log_decision_type = [] 
    log_known_queue_len_spine = []

    in_transit_tasks = []

    partition_size_spine = num_tors / num_spines
    
    decision_tag = 0

    aggregate_num_msg_spine = [0] * num_spines  
    aggregate_num_msg_tor = [0] * num_tors
    aggregate_switch_state_spine = [] * num_spines 
    aggregate_switch_state_tor = [] * num_tors

    num_msg = 0
    idle_avg = 0
    idle_counts = []

    # for i in range(num_workers):
    #     task_lists.append([])
    
    for spine_idx in range(num_spines):
        # idle_queue_spine.append(get_tor_partition_range_for_spine(spine_idx))
        # known_queue_len_spine.append({})
        switch_state_spine.append([])

    for tor_idx in range(num_tors):
        # idle_queue_tor.append(get_worker_range_for_tor(tor_idx))
        # known_queue_len_tor.append({})
        switch_state_tor.append([])

    #last_task_arrival = 0.0
    #task_idx = 0
    for tick in range(num_ticks):    
        task_lists, queue_lens_workers, queue_lens_tors, num_msg_tor, num_msg_spine, idle_queue_tor, idle_queue_spine, known_queue_len_tor, known_queue_len_spine = process_tasks_fcfs(
                policy,
                1,
                task_lists,
                queue_lens_workers, 
                queue_lens_tors, 
                num_msg_tor,
                num_msg_spine,
                1, 
                idle_queue_tor, 
                idle_queue_spine, 
                num_spines,
                k, 
                known_queue_len_tor, 
                known_queue_len_spine
                )
        in_transit_tasks, arrived_tasks = process_network(in_transit_tasks, ticks_passed=1)

        for arrived_task in arrived_tasks:
            #print arrived_task.target_worker
            log_task_wait_time.append(np.sum(task_lists[arrived_task.target_worker])) # Task assigned to target worker should wait at least as long as pending load
            log_task_transfer_time.append(arrived_task.transfer_time)
            log_queue_len_signal_workers.append(queue_lens_workers[arrived_task.target_worker])
            log_queue_len_signal_tors.append(queue_lens_tors[arrived_task.target_tor])
            log_decision_type.append(arrived_task.decision_tag)
            queue_lens_workers[arrived_task.target_worker] += 1
            queue_lens_tors[arrived_task.target_tor] = calculate_tor_queue_len(arrived_task.target_tor, queue_lens_workers) # queue_lens_tors not used by algorithm
            task_lists[arrived_task.target_worker].append(arrived_task.load)
            if policy == 'pow_of_k':
                for spine_idx in range(num_spines): # Update ToR queue len for all other spines
                    if spine_idx != arrived_task.first_spine:
                        num_msg_spine[arrived_task.first_spine] += 1

            elif policy == 'adaptive':
                if arrived_task.target_worker in known_queue_len_tor[arrived_task.target_tor]: # Update queue len of worker at ToR
                    known_queue_len_tor[arrived_task.target_tor].update({arrived_task.target_worker: queue_lens_workers[arrived_task.target_worker]}) 
                
                if known_queue_len_tor[arrived_task.target_tor]: # Some SQ signal available at ToR
                    sum_known_signals = 0
                    for worker in known_queue_len_tor[arrived_task.target_tor]:
                        sum_known_signals += known_queue_len_tor[arrived_task.target_tor][worker]
                    avg_known_queue_len = float(sum_known_signals) / len(known_queue_len_tor[arrived_task.target_tor]) 
                    
                    for spine_idx in range(num_spines): # ToR that is linked with a spine, will update the signal 
                        if arrived_task.target_tor in known_queue_len_spine[spine_idx]:
                            known_queue_len_spine[spine_idx].update({arrived_task.target_tor: avg_known_queue_len}) # Update SQ signals
                            num_msg_spine[spine_idx] += 1
                    log_known_queue_len_spine.append(avg_known_queue_len)
                else:
                    log_known_queue_len_spine.append(0)
        
        # A service might have different number of workers, so its Max Load will be different than others.
        # Process each service independently based on its load:
        for vcluster in vcluster_list:
            if (tick - vcluster.last_task_arrival) > vcluster.inter_arrival and vcluster.task_idx < len(vcluster.distribution): # New task arrives
                vcluster.last_task_arrival = tick

                num_idles = calculate_idle_count(queue_lens_workers)
                idle_counts.append(num_idles)
                
                load = vcluster.distribution[vcluster.task_idx] # Pick new task load
                new_task = Task(load, vcluster)
                
                if policy == 'random':
                    scheduled_task = schedule_task_random(new_task)

                elif policy == 'pow_of_k':
                    scheduled_task = schedule_task_pow_of_k(new_task, k, queue_lens_workers, queue_lens_tors)
                    for spine_idx in range(num_spines):
                        switch_state_spine[spine_idx].append(num_tors)
                    for tor_idx in range(num_tors):
                        switch_state_tor[tor_idx].append(workers_per_tor)
                    
                elif policy == 'pow_of_k_partitioned':
                    scheduled_task = schedule_task_pow_of_k_partitioned(new_task, k, queue_lens_workers, queue_lens_tors)
                    for spine_idx in range(num_spines):
                        switch_state_spine[spine_idx].append(partition_size_spine)
                    for tor_idx in range(num_tors):
                        switch_state_tor[tor_idx].append(workers_per_tor)

                elif policy == 'jiq':
                    scheduled_task, idle_queue_tor, idle_queue_spine, num_msg_tor, num_msg_spine = schedule_task_jiq(
                        new_task,
                        queue_lens_workers,
                        queue_lens_tors,
                        idle_queue_tor,
                        idle_queue_spine,
                        num_msg_tor, 
                        num_msg_spine)
                    switch_state_tor, switch_state_spine = calculate_num_state(
                        switch_state_tor,
                        switch_state_spine,
                        primary_signal_tor=idle_queue_tor,
                        primary_signal_spine=idle_queue_spine)
                elif policy == 'adaptive':
                    scheduled_task, idle_queue_tor, idle_queue_spine, known_queue_len_tor, known_queue_len_spine, num_msg_tor, num_msg_spine = schedule_task_adaptive(
                        new_task,
                        k,
                        queue_lens_workers,
                        queue_lens_tors,
                        idle_queue_tor,
                        idle_queue_spine,
                        known_queue_len_tor,
                        known_queue_len_spine,
                        num_msg_tor, 
                        num_msg_spine)
                    switch_state_tor, switch_state_spine = calculate_num_state(
                        switch_state_tor,
                        switch_state_spine,
                        primary_signal_tor=idle_queue_tor,
                        primary_signal_spine=idle_queue_spine,
                        secondary_signal_tor=known_queue_len_tor,
                        secondary_signal_spine=known_queue_len_spine)
                in_transit_tasks.append(scheduled_task)
                vcluster.task_idx += 1


    if policy == 'random':
        policy_file_tag = policy
    elif policy == 'pow_of_k':
        policy_file_tag = 'sparrow_k' + str(k)
    elif policy == 'pow_of_k_partitioned':
        policy_file_tag = 'racksched_k' + str(k)
    elif policy == 'jiq':
        policy_file_tag = 'jiq_k' + str(k)
    elif policy == 'adaptive':
        policy_file_tag = 'adaptive_k' + str(k)

    exp_duration_s = float((len(distribution) * inter_arrival)) / (10**6)
    msg_per_sec_spine = [x / exp_duration_s for x in num_msg_spine]
    msg_per_sec_tor = [x / exp_duration_s for x in num_msg_spine]
    #print switch_state_spine
    
    max_state_spine = [max(x) for x in switch_state_spine]
    mean_state_spine = [np.mean(x) for x in switch_state_spine]
    max_state_tor = [max(x) for x in switch_state_tor]
    mean_state_tor = [np.mean(x) for x in switch_state_tor]
    #print mean_state_tor
    # exit(0)
    write_to_file('wait_times', policy_file_tag, sys_load, distribution_name,  log_task_wait_time, num_spines=num_spines)
    write_to_file('transfer_times', policy_file_tag, sys_load, distribution_name, log_task_transfer_time, num_spines=num_spines)
    write_to_file('idle_count', policy_file_tag, sys_load, distribution_name, idle_counts, num_spines=num_spines)
    if policy != 'random':
        write_to_file('switch_state_spine_mean', policy_file_tag, sys_load, distribution_name,  mean_state_spine, num_spines=num_spines)
        write_to_file('switch_state_tor_mean', policy_file_tag, sys_load, distribution_name,  mean_state_tor, num_spines=num_spines)
        write_to_file('switch_state_spine_max', policy_file_tag, sys_load, distribution_name,  max_state_spine, num_spines=num_spines)
        write_to_file('switch_state_tor_max', policy_file_tag, sys_load, distribution_name,  max_state_tor, num_spines=num_spines)
        write_to_file('queue_lens', policy_file_tag, sys_load, distribution_name,  log_queue_len_signal_workers, num_spines=num_spines)
        write_to_file('msg_per_sec_tor', policy_file_tag, sys_load, distribution_name, msg_per_sec_tor, num_spines=num_spines)
        write_to_file('msg_per_sec_spine', policy_file_tag, sys_load, distribution_name, msg_per_sec_spine, num_spines=num_spines)
        if policy == 'adaptive':
            write_to_file('decision_type', policy_file_tag, sys_load, distribution_name, log_decision_type, num_spines=num_spines)
    return log_task_wait_time

def run_simulations():
    for task_distribution_name in task_time_distributions:
        print (task_distribution_name + " task distribution\n")
        if task_distribution_name == 'bimodal':
            load_dist = load_bimodal
        elif task_distribution_name == 'trimodal':
            load_dist = load_trimodal
        for load in loads:
            print ("\nLoad: " + str(load))
            if task_distribution_name == "bimodal":
                mean_task_time = (mean_task_small + mean_task_medium) / 2
            elif task_distribution_name == "trimodal":
                mean_task_time = (mean_task_small + mean_task_medium + mean_task_large) / 3
            inter_arrival = (mean_task_time / num_workers) / load

            print ("Inter arrival: " + str(inter_arrival))

            # random_proc = Process(target=run_scheduling, args=('random', 2, num_spines, load_dist, task_distribution_name, inter_arrival, load, ))
            # random_proc.start()

            # pow_of_k_proc = Process(target=run_scheduling, args=('pow_of_k', 2, num_spines, load_dist, task_distribution_name, inter_arrival, load, ))
            # pow_of_k_proc.start()

            # pow_of_k_partitioned_proc = Process(target=run_scheduling, args=('pow_of_k_partitioned', 2, num_spines, load_dist, task_distribution_name, inter_arrival, load, ))
            # pow_of_k_partitioned_proc.start()

            # jiq_proc = Process(target=run_scheduling, args=('jiq', 2, num_spines, load_dist, task_distribution_name, inter_arrival, load, ))
            # jiq_proc.start()

            adaptive_proc = Process(target=run_scheduling, args=('adaptive', 2, num_spines, load_dist, task_distribution_name, inter_arrival, load, ))
            adaptive_proc.start()

run_simulations()
# print ("\nRandom Bimodal:")
# result = random(load_bimodal)
# print_result(result, load_bimodal)

# print ("\nPow-of-2 Bimodal: ")
# result = pow_of_k(2, 4, load_bimodal)
# print_result(result, load_bimodal)

# print ("\nPow-of-2 Partitioned Bimodal:")
# result = pow_of_k_partitioned(2, 4, load_bimodal)
# print_result(result, load_bimodal)

# print ("\nJIQ Bimodal:")
# result = jiq(2, 4, load_bimodal)
# print_result(result, load_bimodal)

# print ("\nRandom Trimodal:")
# result = random(load_trimodal)
# print_result(result, load_trimodal)

# print ("\nJSQ Bimodal:")
# result = pow_of_k(num_workers, load_bimodal)
# print_result(result, load_bimodal)

# print ("\nPow-of-2 Trimodal:")
# result = pow_of_k(2, 4, load_trimodal)
# print_result(result, load_trimodal)

# print ("\nPow-of-2 Partitioned Trimodal:")
# result = pow_of_k_partitioned(2, 4, load_trimodal)
# print_result(result, load_trimodal)

# print ("\nJIQ Trimodal:")
# result = jiq(2, 4, load_trimodal)
# print_result(result, load_trimodal)


