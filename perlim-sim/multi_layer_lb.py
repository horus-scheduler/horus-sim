import numpy.random as nr
import numpy as np
import math
import random 
from multiprocessing import Process, Queue, Value, Array

result_dir = "./results_layered_1/"

# 100 Machines
# num_pods = 2
# spines_per_pod = 5
# tors_per_pod = 10
# workers_per_tor = 5

num_pods = 2
spines_per_pod = 5
tors_per_pod = 10
workers_per_tor = 5


num_tors = num_pods * tors_per_pod
num_spines = spines_per_pod * num_pods
num_workers = tors_per_pod * num_pods * workers_per_tor

print ("Number of workers: " + str(num_workers))

num_tasks = 50000

loads = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6,0.7, 0.8, 0.85, 0.9, 0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99]
#loads = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6,0.7, 0.8, 0.9, 0.95, 0.99]
#loads = [0.99]
task_time_distributions = ['bimodal']

mean_task_small = 50.0
mean_task_medium = 500.0
mean_task_large = 5000.0

mu = 0.0
sigma = 1.0

log_normal_mean = math.e ** (mu + sigma ** 2 / 2)

load_lognormal = nr.lognormal(mu, sigma, num_tasks)
load_uniform = nr.uniform(0, 2*mean_task_small, num_tasks)

bimodal_small = np.random.normal(mean_task_small, mean_task_small/10, num_tasks/2)
bimodal_medium = np.random.normal(mean_task_medium, mean_task_medium/10, num_tasks/2)
load_bimodal = np.concatenate([bimodal_small, bimodal_medium])

indices = np.arange(load_bimodal.shape[0])
np.random.shuffle(indices)
load_bimodal = load_bimodal[indices]

trimodal_small = np.random.normal(mean_task_small, mean_task_small/10, num_tasks/3)
trimodal_medium = np.random.normal(mean_task_medium, mean_task_medium/10, num_tasks/3)
trimodal_large = np.random.normal(mean_task_large, mean_task_large/10, num_tasks/3)
load_trimodal = np.concatenate([trimodal_small, trimodal_medium, trimodal_large])

indices = np.arange(load_trimodal.shape[0])
np.random.shuffle(indices)
load_trimodal = load_trimodal[indices]

def normalize(load):
    return (load / log_normal_mean) * mean_task

def get_tor_idx_for_worker(worker_idx):
    return int(worker_idx / workers_per_tor)

def get_worker_range_for_tor(tor_idx):
    workers_start_idx = tor_idx * workers_per_tor # Each ToR is has access to workers_per_tor machines
    return range(workers_start_idx, workers_start_idx + workers_per_tor)

def get_tor_partition_range_for_spine(spine_idx): #Used for partitioned pow-of-k SQ
    partition_size = tors_per_pod / spines_per_pod
    tor_start_idx = spine_idx * partition_size
    return range(tor_start_idx, tor_start_idx + partition_size)

def write_to_file_wait_time(policy, load, distribution, results, num_spines = 1):
    metric = 'wait_times'

    filename = policy + '_' + distribution + '_' + 'n' + str(num_workers) + '_m' + str(num_spines) + '_' + metric +  '_' + str(load) + '.csv'
    
    with open(result_dir + filename, 'wb') as output_file:
        for i, value in enumerate(results):
            if i < len(results) - 1:
                output_file.write(str(value) + ', ')
            else:
                output_file.write(str(value))

def write_to_file_queue_len_signal(policy, load, distribution, results, num_spines = 1):
    metric = 'queue_lens'

    filename = policy + '_' + distribution + '_' + 'n' + str(num_workers) + '_m' + str(num_spines) + '_' + metric +  '_' + str(load) + '.csv'
    
    with open(result_dir + filename, 'wb') as output_file:
        for i, value in enumerate(results):
            if i < len(results) - 1:
                output_file.write(str(value) + ', ')
            else:
                output_file.write(str(value))

def write_to_file_msg(policy, load, distribution, results, num_spines = 1):
    metric = 'msg_per_sec'

    filename = policy + '_' + distribution + '_' + 'n' + str(num_workers) + '_m' + str(num_spines) + '_' + metric +  '_' + str(load) + '.csv'
    
    with open(result_dir + filename, 'wb') as output_file:
        for i, value in enumerate(results):
            if i < len(results) - 1:
                output_file.write(str(value) + ', ')
            else:
                output_file.write(str(value))

def write_to_file_idle_count(policy, load, distribution, results, num_spines = 1):
    metric = 'idle_count'

    filename = policy + '_' + distribution + '_' + 'n' + str(num_workers) + '_m' + str(num_spines) + '_' + metric +  '_' + str(load) + '.csv'
    
    with open(result_dir + filename, 'wb') as output_file:
        for i, value in enumerate(results):
            if i < len(results) - 1:
                output_file.write(str(value) + ', ')
            else:
                output_file.write(str(value))

def jiq_server_process(idle_queue_tor, idle_queue_spine, num_spines, k, worker_idx):
    min_idle_queue = float("inf")
    sample_indices = random.sample(range(0, num_spines), k) # Sample k dispatchers
    #print sample_indices
    for idx in sample_indices:  # Find the sampled spine with min idle queue len
        sample = len(idle_queue_spine[idx])
        if sample < min_idle_queue:
            min_idle_queue = sample
            target_spine = idx
    tor_idx = get_tor_idx_for_worker(worker_idx)
    idle_queue_tor[tor_idx].append(worker_idx) # Add idle worker to idle queue of ToR
    idle_queue_spine[target_spine].append(tor_idx) # Add ToR to the idle queue of selected spine
    return idle_queue_tor, idle_queue_spine

def adaptive_server_process(idle_queue_tor, idle_queue_spine, known_queue_len_tor, known_queue_len_spine, num_spines, k, worker_idx):
    min_idle_queue = float("inf")
    sample_indices = random.sample(range(0, num_spines), k) # Sample k dispatchers
    #print sample_indices
    for idx in sample_indices:  # Find the sampled spine with min idle queue len (k samples)
        sample = len(idle_queue_spine[idx])
        if sample < min_idle_queue:
            min_idle_queue = sample
            target_spine = idx
    tor_idx = get_tor_idx_for_worker(worker_idx)
    idle_queue_tor[tor_idx].append(worker_idx) # Add idle worker to tor (1 msg)
    idle_queue_spine[target_spine].append(tor_idx) # Add tor to the idle queue of that spine (1 msg)

    #known_queue_len_tor[tor_idx].clear() # Switched to JIQ
    #known_queue_len_spine[target_spine].clear() # Switched to JIQ 
    for spine_idx in range(num_spines):
        if tor_idx in known_queue_len_spine[spine_idx]:
            # print (known_queue_len)
            # print("deleted " + str(server_idx) + " with load: " + str(known_queue_len[d][server_idx]))
            del known_queue_len_spine[spine_idx][tor_idx] # Delete sq entery from previously linked spine (1msg)
    return idle_queue_tor, idle_queue_spine, known_queue_len_tor, known_queue_len_spine

def process_tasks_fcfs(inter_arrival, task_lists, queue_lens_workers, queue_lens_tors, num_msg=None, msg_per_done=1, idle_queue_tor=None, idle_queue_spine=None, num_spines=1, k=2, known_queue_len_tor=None, known_queue_len_spine=None):
    for i in range(len(task_lists)):
        while task_lists[i]:    # while there are any tasks in list
            remaining_time = task_lists[i][0] - inter_arrival   # First task in list is being executed
            task_lists[i][0] = max(0, remaining_time) # If remaining time from task is negative another task is could be executed during the interval
            if task_lists[i][0] == 0:   # If finished executing task
                task_lists[i].pop(0)        # Remove from list
                queue_lens_workers[i] -= 1       # Decrement worker queue len
                tor_idx = get_tor_idx_for_worker(i)
                queue_lens_tors[tor_idx] -= 1.0 / workers_per_tor
                if idle_queue_spine is None: # Random and JIQ do not use this part
                    if (num_msg is not None): 
                        num_msg += msg_per_done # Update queue len for higher level scheduers
                else: #JIQ and adaptive
                    if known_queue_len_spine is None: # JIQ
                        if queue_lens_workers[i] == 0: # Process for when a server becomes idle 
                            idle_queue_tor, idle_queue_spine = jiq_server_process(idle_queue_tor, idle_queue_spine, num_spines, k, i)
                            num_msg += 2 + k # k msgs for sampling spine idle queues, 1 msg for updating tor idle queue, 1 msg for updating spine idle queue
                    else: # Adaptive
                        if i in known_queue_len_tor[tor_idx]: # Update queue len of worker at ToR
                            known_queue_len_tor[tor_idx].update({i: queue_lens_workers[i]})  
                            num_msg += 1
                        for spine_idx in range(num_spines): # ToR that is paired with a spine, will update the signal 
                            if tor_idx in known_queue_len_spine[spine_idx]:
                                known_queue_len_spine[spine_idx].update({tor_idx: queue_lens_tors[tor_idx]}) # Update SQ signals
                        if queue_lens_workers[i] == 0: # Process for when a server becomes idle 
                            idle_queue_tor, idle_queue_spine, known_queue_len_tor, known_queue_len_spine = adaptive_server_process(idle_queue_tor, idle_queue_spine, known_queue_len_tor, known_queue_len_spine, num_spines, k, i)
                            num_msg += 3 + k # k msgs for sampling dispatcher idle queues, 1 msg for updating the dispatcher, 1 msg for removing SQ from other dispatcher
            if remaining_time >= 0:     # Continue loop (processing other tasks) only if remaining time is negative
                break

    return task_lists, queue_lens_workers, queue_lens_tors, num_msg, idle_queue_tor, idle_queue_spine, known_queue_len_tor, known_queue_len_spine

def random_uniform(distribution, distribution_name, inter_arrival, sys_load):
    queue_lens_workers = [0] * num_workers
    queue_lens_tors = [0.0] * num_tors
    task_lists = [] * num_workers
    task_wait_time = [] * num_workers
    idle_counts = []

    for i in range(num_workers):
        task_lists.append([])
        task_wait_time.append([])

    for load in distribution:
        #print queue_lens_workers
        num_idles = 0
        for queue_len in queue_lens_workers:
            if queue_len ==0:
                num_idles += 1
        idle_counts.append(num_idles)

        task_lists, queue_lens_workers, queue_lens_tors, _, _, _, _, _ = process_tasks_fcfs(inter_arrival, task_lists, queue_lens_workers, queue_lens_tors)

        target_worker = nr.randint(0, num_workers) # Make decision
        task_wait_time[target_worker].append(np.sum(task_lists[target_worker])) # Task assigned to target worker should wait at least as long as pending load
        task_lists[target_worker].append(load)
        queue_lens_workers[target_worker] += 1

    flat_task_wait_time = [item for sublist in task_wait_time for item in sublist]
    
    write_to_file_wait_time('random', sys_load, distribution_name, flat_task_wait_time)
    write_to_file_idle_count('random', sys_load, distribution_name, idle_counts)

def pow_of_k(k, num_spines, distribution, distribution_name, inter_arrival, sys_load):
    queue_lens_workers = [0] * num_workers
    queue_lens_tors = [0.0] * num_tors

    task_lists = [] * num_workers
    task_wait_time = [] * num_workers
    queue_len_signal_workers = [] * num_workers
    num_msg = 0
    idle_avg = 0
    idle_counts = []

    for i in range(num_workers):
        task_lists.append([])
        task_wait_time.append([])
        queue_len_signal_workers.append([])

    for load in distribution: # New task arrive
        #print task_wait_time
        num_idles = 0
        for queue_len in queue_lens_workers:
            if queue_len ==0:
                num_idles += 1
        idle_counts.append(num_idles)
        idle_avg +=  num_idles
        
        task_lists, queue_lens_workers, queue_lens_tors, num_msg, _, _, _, _ = process_tasks_fcfs(inter_arrival, task_lists, queue_lens_workers, queue_lens_tors, num_msg, num_spines)

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

        task_wait_time[target_worker].append(np.sum(task_lists[target_worker])) # Task assigned to target worker should wait at least as long as pending load
        queue_len_signal_workers[target_worker].append(queue_lens_workers[target_worker])
        queue_lens_workers[target_worker] += 1
        queue_lens_tors[target_tor] += 1.0 / workers_per_tor # Assuming tors report average queue length of workers
        num_msg += num_spines # Update queue len for other spines
        task_lists[target_worker].append(load)
        
    idle_avg /= len(distribution)
    flat_task_wait_time = [item for sublist in task_wait_time for item in sublist]
    flat_queue_len_signal = [item for sublist in queue_len_signal_workers for item in sublist]
    #task_wait_time = np.array(task_wait_time).flatten()

    print ("Avg. #Idle workers Pow-of-k: " + str(idle_avg))
    print ("#msg Pow-of-k: " + str(num_msg))
    msg_per_sec = (num_msg / (len(distribution) * inter_arrival))*(10**6)
    print ("#msg/s Pow-of-k: " + str((num_msg / (len(distribution) * inter_arrival))*(10**6)))

    write_to_file_wait_time('sparrow_k' + str(k), sys_load, distribution_name,  flat_task_wait_time, num_spines=num_spines)
    write_to_file_queue_len_signal('sparrow_k' + str(k), sys_load, distribution_name,  flat_queue_len_signal, num_spines=num_spines)
    write_to_file_msg('sparrow_k' + str(k), sys_load, distribution_name, [msg_per_sec], num_spines=num_spines)
    write_to_file_idle_count('sparrow_k' + str(k), sys_load, distribution_name, idle_counts, num_spines=num_spines)

    #return np.array(task_wait_time).flatten()[0]

def pow_of_k_partitioned(k, num_spines, distribution, distribution_name, inter_arrival, sys_load): # Change name
    queue_lens_workers = [0] * num_workers
    queue_lens_tors = [0.0] * num_tors

    task_lists = [] * num_workers
    task_wait_time = [] * num_workers
    queue_len_signal_workers = [] * num_workers
    num_msg = 0
    idle_avg = 0
    idle_counts = []

    for i in range(num_workers):
        task_lists.append([])
        task_wait_time.append([])
        queue_len_signal_workers.append([])

    for load in distribution:   # New task arrive
        
        num_idles = 0
        for queue_len in queue_lens_workers:
            if queue_len ==0:
                num_idles += 1
        idle_counts.append(num_idles)
        idle_avg +=  num_idles

        task_lists, queue_lens_workers, queue_lens_tors, num_msg, _, _, _, _ = process_tasks_fcfs(inter_arrival, task_lists, queue_lens_workers, queue_lens_tors, num_msg)
        
        # Make decision at Spine level:
        min_load = float("inf")
        target_spine = random.randrange(num_spines)  # Emulating arrival at a spine randomly
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

        
        queue_lens_tors[target_tor] += 1.0 / workers_per_tor # Assuming tors report average queue length of workers
        task_wait_time[target_worker].append(np.sum(task_lists[target_worker])) # Task assigned to target worker should wait at least as long as pending load
        queue_len_signal_workers[target_worker].append(queue_lens_workers[target_worker])
        queue_lens_workers[target_worker] += 1
        task_lists[target_worker].append(load)

    idle_avg /= len(distribution)
    flat_task_wait_time = [item for sublist in task_wait_time for item in sublist]
    flat_queue_len_signal = [item for sublist in queue_len_signal_workers for item in sublist]

    #task_wait_time = np.array(task_wait_time).flatten()

    print ("Avg. #Idle workers Pow-of-k Partitioned: " + str(idle_avg))
    print ("#msg Pow-of-k Partitioned: " + str(num_msg))
    print ("#msg/s Pow-of-k Partitioned: " + str((num_msg / (len(distribution) * inter_arrival))*(10**6)))
    msg_per_sec = (num_msg / (len(distribution) * inter_arrival))*(10**6)
    write_to_file_wait_time('racksched_k' + str(k), sys_load, distribution_name, flat_task_wait_time, num_spines=num_spines)
    write_to_file_queue_len_signal('racksched_k' + str(k), sys_load, distribution_name, flat_queue_len_signal, num_spines=num_spines)
    write_to_file_msg('racksched_k' + str(k), sys_load, distribution_name, [msg_per_sec], num_spines=num_spines)
    write_to_file_idle_count('racksched_k' + str(k), sys_load, distribution_name, idle_counts, num_spines=num_spines)

    #return np.array(task_wait_time).flatten()[0]

def jiq(k, num_spines, distribution, distribution_name, inter_arrival, sys_load):
    nr.seed()
    queue_lens_workers = [0] * num_workers
    queue_lens_tors = [0.0] * num_tors

    task_lists = [] * num_workers
    task_wait_time = [] * num_workers

    idle_queue_tor = [] * num_tors
    idle_queue_spine = [] * num_spines
    
    queue_len_signal = [] * num_workers

    partition_size = num_workers / num_spines

    num_msg = 0
    idle_avg = 0
    idle_counts = []

    for i in range(num_workers):
        task_lists.append([])
        task_wait_time.append([])
        queue_len_signal.append([])

    for spine_idx in range(num_spines):
        idle_queue_spine.append(get_tor_partition_range_for_spine(spine_idx))
    
    for tor_idx in range(num_tors):
        idle_queue_tor.append(get_worker_range_for_tor(tor_idx))
    #print idle_queue_tor
    
    for load in distribution:   # New task arrive
        #print queue_lens_workers
        #print "\n List:"
        num_idles = 0
        for queue_len in queue_lens_workers:
            if queue_len ==0:
                num_idles += 1
        idle_counts.append(num_idles)
        idle_avg +=  num_idles
        #print(idle_queue_spine)
        
        task_lists, queue_lens_workers, queue_lens_tors, num_msg, idle_queue_tor, idle_queue_spine, _, _ = process_tasks_fcfs(
                inter_arrival,
                task_lists,
                queue_lens_workers,
                queue_lens_tors,
                num_msg, 
                1, 
                idle_queue_tor,
                idle_queue_spine, 
                num_spines,
                k)
        
        target_spine = random.randrange(num_spines)  # Emulating arrival at a spine switch randomly
        
        # Make decision at spine level:
        if idle_queue_spine[target_spine]:  # Spine is aware of some tors with idle wokrers
            target_tor = idle_queue_spine[target_spine].pop(0)
        else:   # No tor with idle worker is known, dispatch to a random tor
            #target_tor = random.choice(get_tor_partition_range_for_spine(target_spine)) Limit to pod
            target_tor = nr.randint(0, num_tors) # Can forward to any ToR

            for idle_tors in idle_queue_spine:
                if target_tor in idle_tors:   # Tor was previously presented as idle to one of spines
                    if len(idle_queue_tor[target_tor]) <= 1: # After sending this tor is no longer idle and removes itself from that spine's list
                        idle_tors.remove(target_tor)
                        num_msg += 1

        # Make decision at tor level:           
        if idle_queue_tor[target_tor]: # Tor is aware of some idle workers
            target_worker = idle_queue_tor[target_tor].pop(0)
        else:
            target_worker = nr.randint(0, num_workers)
            if target_worker in idle_queue_tor[target_tor]:
                idle_queue_tor[target_tor].remove(target_worker)

        task_wait_time[target_worker].append(np.sum(task_lists[target_worker])) # Task assigned to target worker should wait at least as long as pending load
        queue_len_signal[target_worker].append(queue_lens_workers[target_worker])
        queue_lens_workers[target_worker] += 1
        task_lists[target_worker].append(load)

    #task_wait_time = np.array(task_wait_time).flatten()
    idle_avg /= len(distribution)

    flat_task_wait_time = [item for sublist in task_wait_time for item in sublist]
    flat_queue_len_signal = [item for sublist in queue_len_signal for item in sublist]

    print ("Avg. #Idle workers JIQ: " + str(idle_avg))
    print ("#msg JIQ: " + str(num_msg))
    print ("#msg/s JIQ: " + str((num_msg / (len(distribution) * inter_arrival))*(10**6)))
    msg_per_sec = (num_msg / (len(distribution) * inter_arrival))*(10**6)
    write_to_file_wait_time('jiq_k' + str(k), sys_load, distribution_name, flat_task_wait_time, num_spines=num_spines)
    write_to_file_queue_len_signal('jiq_k' + str(k), sys_load, distribution_name, flat_queue_len_signal, num_spines=num_spines)
    write_to_file_msg('jiq_k' + str(k), sys_load, distribution_name, [msg_per_sec], num_spines=num_spines)
    write_to_file_idle_count('jiq_k' + str(k), sys_load, distribution_name, idle_counts, num_spines=num_spines)
    #return np.array(task_wait_time).flatten()[0]

def adaptive(k, num_spines, distribution, distribution_name, inter_arrival, sys_load):
    nr.seed()
    queue_lens_workers = [0] * num_workers
    queue_lens_tors = [0.0] * num_tors

    task_lists = [] * num_workers
    task_wait_time = [] * num_workers
    
    idle_queue_tor = [] * num_tors
    idle_queue_spine = [] * num_spines

    known_queue_len_spine = [] * num_spines  # For each spine, list of maps between torID and average queueLen if ToR
    known_queue_len_tor = [] * num_tors # For each tor, list of maps between workerID and queueLen
    
    queue_len_signal = [] * num_workers # For analysis only 

    partition_size_spine = num_tors / num_spines

    num_msg = 0
    idle_avg = 0
    idle_counts = []

    for i in range(num_workers):
        task_lists.append([])
        task_wait_time.append([])
        queue_len_signal.append([])

    for spine_idx in range(num_spines):
        idle_queue_spine.append(get_tor_partition_range_for_spine(spine_idx))
        known_queue_len_spine.append({})

    for tor_idx in range(num_tors):
        idle_queue_tor.append(get_worker_range_for_tor(tor_idx))
        known_queue_len_tor.append({})

    for load in distribution:   # New task arrive
        # For analsis only:
        min_load = float("inf")
        num_idles = 0
        for queue_len in queue_lens_workers:
            if queue_len ==0:
                num_idles += 1
        idle_counts.append(num_idles)
        idle_avg +=  num_idles
        
        # Process tasks (time passed)
        task_lists, queue_lens_workers, queue_lens_tors, num_msg, idle_queue_tor, idle_queue_spine, known_queue_len_tor, known_queue_len_spine = process_tasks_fcfs(
                inter_arrival,
                task_lists,
                queue_lens_workers, 
                queue_lens_tors, 
                num_msg, 1, 
                idle_queue_tor, 
                idle_queue_spine, 
                num_spines,
                k, 
                known_queue_len_tor, 
                known_queue_len_spine
                )
        
        # Make decision at spine layer:
        target_spine = random.randrange(num_spines)  # Emulating arrival at a spine switch randomly
        
        if len(idle_queue_spine[target_spine]) > 0:  # Spine is aware of some tors with idle servers
            target_tor = idle_queue_spine[target_spine].pop(0)
            
        else:   # No tor with idle server is known
            already_paired = False
            sq_update = False
            if (len(known_queue_len_spine[target_spine]) < partition_size_spine): # Scheduer still trying to get more queue len info
                    num_msg += 1
                    random_tor = nr.randint(0, num_tors)
                    for spine_idx in range(num_spines):
                        if random_tor in known_queue_len_spine[spine_idx]:
                            already_paired = True
                    if len(idle_queue_tor[random_tor]) > 0: # If it knows idle servers, it's already paired with another spine (registered in their Idle Queue)
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
            else: # Randomly select a ToR from all of the available servers
                target_tor = nr.randint(0, num_tors)
                # for spine_idx in range(num_spines):
                #     if target_tor in known_queue_len_spine[spine_idx]:
                #         already_paired = True
                # if len(idle_queue_tor[target_tor]) > 0:
                #     already_paired = True
                # if not already_paired: # Each tor queue len should be available at one spine only
                #     known_queue_len_spine[target_spine].update({target_tor: queue_lens_tors[target_tor]}) # Add SQ signal
            if sq_update:
                known_queue_len_spine[target_spine].update({random_tor: queue_lens_tors[random_tor]}) # Add SQ signal
            for idle_tor_list in idle_queue_spine:
                if target_tor in idle_tor_list:   # tor that gets a random-assigned task removes itself from the idle queue it has joined
                    idle_tor_list.remove(target_tor)
                    num_msg += 1
            
        # Make decision at ToR layer:
        min_load = float("inf")
        worker_indices = get_worker_range_for_tor(target_tor)
        if len(idle_queue_tor[target_tor]) > 0:  # Tor is aware of some idle workers
            target_worker = idle_queue_tor[target_tor].pop(0)

        else: # No idle worker
            already_paired = False
            sq_update = False
            if (len(known_queue_len_tor[target_tor]) < len(worker_indices)): # Tor scheduer still trying to get more queue len info
                    num_msg += 1
                    random_worker = random.choice(worker_indices)
                    known_queue_len_tor[target_tor].update({random_worker: queue_lens_workers[random_worker]}) # Add SQ signal
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
                #known_queue_len_tor[target_tor].update({target_worker: queue_lens_workers[target_worker]}) # Add SQ signal
            if sq_update:
                known_queue_len_tor[target_tor].update({random_worker: queue_lens_workers[random_worker]}) # Add SQ signal
        task_wait_time[target_worker].append(np.sum(task_lists[target_worker])) # Task assigned to target worker should wait at least as long as pending load
        queue_len_signal[target_worker].append(queue_lens_workers[target_worker])
        task_lists[target_worker].append(load)
        queue_lens_workers[target_worker] += 1
        if known_queue_len_tor[target_tor]:
            queue_lens_tors[target_tor] += 1.0 / len(known_queue_len_tor[target_tor]) # Increase average at ToR
        
        if target_worker in known_queue_len_tor[target_tor]: # Update queue len of worker at ToR
            known_queue_len_tor[target_tor].update({target_worker: queue_lens_workers[target_worker]})  
        
        for spine_idx in range(num_spines): # ToR that is paired with a spine, will update the signal 
            if target_tor in known_queue_len_spine[spine_idx]:
                known_queue_len_spine[spine_idx].update({target_tor: queue_lens_tors[target_tor]}) # Update SQ signals
                
    #task_wait_time = np.array(task_wait_time).flatten()
    idle_avg /= len(distribution)

    flat_task_wait_time = [item for sublist in task_wait_time for item in sublist]
    flat_queue_len_signal = [item for sublist in queue_len_signal for item in sublist]

    print ("Avg. #Idle workers Adaptive: " + str(idle_avg))
    print ("#msg Adaptive: " + str(num_msg))
    print ("#msg/s Adaptive: " + str((num_msg / (len(distribution) * inter_arrival))*(10**6)))
    msg_per_sec = (num_msg / (len(distribution) * inter_arrival))*(10**6)
    write_to_file_wait_time('adaptive_k' + str(k), sys_load, distribution_name, flat_task_wait_time, num_spines=num_spines)
    write_to_file_queue_len_signal('adaptive_k' + str(k), sys_load, distribution_name, flat_queue_len_signal, num_spines=num_spines)
    write_to_file_msg('adaptive_k' + str(k), sys_load, distribution_name, [msg_per_sec], num_spines=num_spines)
    write_to_file_idle_count('adaptive_k' + str(k), sys_load, distribution_name, idle_counts, num_spines=num_spines)

def print_result(result):
    print ("\nMax wait: " + str(np.max(result)))
    print ("Avg wait: " + str(np.mean(result)))
    #print("Ideal load:" + str((np.sum(distribution)/ num_workers)))
    print ("50 Percentile: " + str(np.percentile(result, 50)))
    print ("75 Percentile: " + str(np.percentile(result, 75)))
    print ("90 Percentile: " + str(np.percentile(result, 90)))
    print ("99 Percentile: " + str(np.percentile(result, 99)))

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
            
            # random_proc = Process(target=random_uniform, args=(load_dist, task_distribution_name, inter_arrival, load, ))
            # random_proc.start()
            # #result = random_uniform(load_dist, task_distribution, inter_arrival, load)
            # #print_result(result, task_distribution, load)
            pow_of_k_proc = Process(target=pow_of_k, args=(2, num_spines, load_dist, task_distribution_name, inter_arrival, load, ))
            pow_of_k_proc.start()
            pow_of_k_partitioned_proc = Process(target=pow_of_k_partitioned, args=(2, num_spines, load_dist, task_distribution_name, inter_arrival, load, ))
            pow_of_k_partitioned_proc.start()
            jiq_proc = Process(target=jiq, args=(2, num_spines, load_dist, task_distribution_name, inter_arrival, load, ))
            jiq_proc.start()
            # pow_of_k(2, num_spines, load_dist, task_distribution_name, inter_arrival, load)
            # pow_of_k_partitioned(2, num_spines, load_dist, task_distribution_name, inter_arrival, load)
            # # adaptive(2, num_spines, load_dist, task_distribution_name, inter_arrival, load)
            # # jiq(2, num_spines, load_dist, task_distribution_name, inter_arrival, load)

            adaptive_proc = Process(target=adaptive, args=(2, num_spines, load_dist, task_distribution_name, inter_arrival, load, ))
            adaptive_proc.start()
            #print result

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


