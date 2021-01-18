import numpy.random as nr
import numpy as np
import math
import random 
from multiprocessing import Process, Queue, Value, Array

result_dir = "./results_10/"
num_machines = 100
num_dispatchers = 10

num_tasks = 50000

loads = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6,0.7, 0.8, 0.85, 0.9, 0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99]
#loads = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6,0.7, 0.8, 0.9, 0.95, 0.99]
#loads = [0.9]
task_time_distributions = ['bimodal']

machines = [0] * num_machines

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

def write_to_file_wait_time(policy, load, distribution, results, num_dispatchers = 1):
    metric = 'wait_times'

    filename = policy + '_' + distribution + '_' + 'n' + str(num_machines) + '_m' + str(num_dispatchers) + '_' + metric +  '_' + str(load) + '.csv'
    
    with open(result_dir + filename, 'wb') as output_file:
        for i, value in enumerate(results):
            if i < len(results) - 1:
                output_file.write(str(value) + ', ')
            else:
                output_file.write(str(value))

def write_to_file_decision_type(policy, load, distribution, results, num_dispatchers = 1):
    metric = 'decision_type'

    filename = policy + '_' + distribution + '_' + 'n' + str(num_machines) + '_m' + str(num_dispatchers) + '_' + metric +  '_' + str(load) + '.csv'
    
    with open(result_dir + filename, 'wb') as output_file:
        for i, value in enumerate(results):
            if i < len(results) - 1:
                output_file.write(str(value) + ', ')
            else:
                output_file.write(str(value))

def write_to_file_queue_len_signal(policy, load, distribution, results, num_dispatchers = 1):
    metric = 'queue_lens'

    filename = policy + '_' + distribution + '_' + 'n' + str(num_machines) + '_m' + str(num_dispatchers) + '_' + metric +  '_' + str(load) + '.csv'
    
    with open(result_dir + filename, 'wb') as output_file:
        for i, value in enumerate(results):
            if i < len(results) - 1:
                output_file.write(str(value) + ', ')
            else:
                output_file.write(str(value))

def write_to_file_msg(policy, load, distribution, results, num_dispatchers = 1):
    metric = 'msg_per_sec'

    filename = policy + '_' + distribution + '_' + 'n' + str(num_machines) + '_m' + str(num_dispatchers) + '_' + metric +  '_' + str(load) + '.csv'
    
    with open(result_dir + filename, 'wb') as output_file:
        for i, value in enumerate(results):
            if i < len(results) - 1:
                output_file.write(str(value) + ', ')
            else:
                output_file.write(str(value))

def write_to_file_idle_count(policy, load, distribution, results, num_dispatchers = 1):
    metric = 'idle_count'

    filename = policy + '_' + distribution + '_' + 'n' + str(num_machines) + '_m' + str(num_dispatchers) + '_' + metric +  '_' + str(load) + '.csv'
    
    with open(result_dir + filename, 'wb') as output_file:
        for i, value in enumerate(results):
            if i < len(results) - 1:
                output_file.write(str(value) + ', ')
            else:
                output_file.write(str(value))

def jiq_server_process(idle_queue, num_dispatchers, k, server_idx):
    min_idle_queue = float("inf")
    sample_indices = random.sample(range(0, num_dispatchers), k) # Sample k dispatchers
    #print sample_indices
    for idx in sample_indices:  # Find the sampled dispatcher with min idle queue len
        sample = len(idle_queue[idx])
        if sample < min_idle_queue:
            min_idle_queue = sample
            target_dispatcher = idx
    idle_queue[idx].append(server_idx) # Add server to the idle queue of that dispatcher
    return idle_queue

def adaptive_server_process(idle_queue, known_queue_len, num_dispatchers, k, server_idx):
    min_idle_queue = float("inf")
    sample_indices = random.sample(range(0, num_dispatchers), k) # Sample k dispatchers
    #print sample_indices
    for idx in sample_indices:  # Find the sampled dispatcher with min idle queue len
        sample = len(idle_queue[idx])
        if sample < min_idle_queue:
            min_idle_queue = sample
            target_dispatcher = idx
    idle_queue[idx].append(server_idx) # Add server to the idle queue of that dispatcher
    known_queue_len[idx].clear() # Switched to idle queue
    for d in range(num_dispatchers):
        if server_idx in known_queue_len[d]:
            # print (known_queue_len)
            # print("deleted " + str(server_idx) + " with load: " + str(known_queue_len[d][server_idx]))
            del known_queue_len[d][server_idx]
    return idle_queue, known_queue_len

def process_tasks_fcfs(inter_arrival, task_lists, queue_lens, num_msg=None, msg_per_done=1, idle_queue=None, num_dispatchers=1, k=2, known_queue_len=None):
    for i in range(len(task_lists)):
        while task_lists[i]:    # while there are any tasks in list
            remaining_time = task_lists[i][0] - inter_arrival   # First task in list is being executed
            task_lists[i][0] = max(0, remaining_time) # If remaining time from task is negative another task is could be executed during the interval
            if task_lists[i][0] == 0:   # If finished executing task
                task_lists[i].pop(0)        # Remove from list
                queue_lens[i] -= 1       # Decrement machine queue len
                if idle_queue is None:
                    if (num_msg is not None): # Random and JIQ do not use this line
                        num_msg += msg_per_done # Update queue len 
                else:
                    if known_queue_len is None: #JIQ
                        if queue_lens[i] == 0: # Process for when a server becomes idle 
                            idle_queue = jiq_server_process(idle_queue, num_dispatchers, k, i)
                            num_msg += 1 + k # k msgs for sampling dispatcher idle queues, 1 msg for updating the dispatcher
                    else: # Adaptive
                        for d in range(num_dispatchers):
                            if i in known_queue_len[d]:
                                known_queue_len[d].update({i: queue_lens[i]}) # update SQ signal
                                num_msg += 1
                        if queue_lens[i] == 0: # Process for when a server becomes idle 
                            idle_queue, known_queue_len = adaptive_server_process(idle_queue, known_queue_len, num_dispatchers, k, i)
                            num_msg += 2 + k # k msgs for sampling dispatcher idle queues, 1 msg for updating the dispatcher, 1 msg for removing SQ from other dispatcher

            if remaining_time >= 0:     # Continue loop (processing other tasks) only if remaining time is negative
                break

    return task_lists, queue_lens, num_msg, idle_queue, known_queue_len

def random_uniform(distribution, distribution_name, inter_arrival, sys_load):
    queue_lens = [0] * num_machines
    task_lists = [] * num_machines
    task_wait_time = [] * num_machines
    idle_counts = []

    for i in range(num_machines):
        task_lists.append([])
        task_wait_time.append([])

    for load in distribution:
        #print queue_lens
        num_idles = 0
        for queue_len in queue_lens:
            if queue_len ==0:
                num_idles += 1
        idle_counts.append(num_idles)

        task_lists, queue_lens,_, _, _ = process_tasks_fcfs(inter_arrival, task_lists, queue_lens)

        target_machine = nr.randint(0, num_machines) # Make decision
        
        task_wait_time[target_machine].append(np.sum(task_lists[target_machine])) # Task assigned to target machine should wait at least as long as pending load
        task_lists[target_machine].append(load)
        queue_lens[target_machine] += 1

    flat_task_wait_time = [item for sublist in task_wait_time for item in sublist]
    write_to_file_wait_time('random', sys_load, distribution_name, flat_task_wait_time)
    write_to_file_idle_count('random', sys_load, distribution_name, idle_counts)

def pow_of_k(k, num_dispatchers, distribution, distribution_name, inter_arrival, sys_load):
    queue_lens = [0] * num_machines
    task_lists = [] * num_machines
    task_wait_time = [] * num_machines
    queue_len_signal = [] * num_machines
    num_msg = 0
    idle_avg = 0
    idle_counts = []

    for i in range(num_machines):
        task_lists.append([])
        task_wait_time.append([])
        queue_len_signal.append([])

    for load in distribution: # New task arrive
        #print task_wait_time
        num_idles = 0
        for queue_len in queue_lens:
            if queue_len ==0:
                num_idles += 1
        idle_counts.append(num_idles)
        idle_avg +=  num_idles
        
        task_lists, queue_lens, num_msg, _, _ = process_tasks_fcfs(inter_arrival, task_lists, queue_lens, num_msg, num_dispatchers)

        # Make the decision:
        min_load = float("inf")
        sample_indices = random.sample(range(0, num_machines), k)
        for idx in sample_indices:
            sample = queue_lens[idx]
            if sample < min_load:
                min_load = sample
                target_machine = idx

       
        num_msg += num_dispatchers - 1 # Update queue len for other dispatchers
        task_wait_time[target_machine].append(np.sum(task_lists[target_machine])) # Task assigned to target machine should wait at least as long as pending load
        queue_len_signal[target_machine].append(queue_lens[target_machine])
        task_lists[target_machine].append(load)
        queue_lens[target_machine] += 1

    idle_avg /= len(distribution)
    flat_task_wait_time = [item for sublist in task_wait_time for item in sublist]
    flat_queue_len_signal = [item for sublist in queue_len_signal for item in sublist]
    #task_wait_time = np.array(task_wait_time).flatten()

    print ("Avg. #Idle workers Pow-of-k: " + str(idle_avg))
    print ("#msg Pow-of-k: " + str(num_msg))
    msg_per_sec = (num_msg / (len(distribution) * inter_arrival))*(10**6)
    print ("#msg/s Pow-of-k: " + str((num_msg / (len(distribution) * inter_arrival))*(10**6)))

    write_to_file_wait_time('sparrow_k' + str(k), sys_load, distribution_name,  flat_task_wait_time, num_dispatchers=num_dispatchers)
    write_to_file_queue_len_signal('sparrow_k' + str(k), sys_load, distribution_name,  flat_queue_len_signal, num_dispatchers=num_dispatchers)
    write_to_file_msg('sparrow_k' + str(k), sys_load, distribution_name, [msg_per_sec], num_dispatchers=num_dispatchers)
    write_to_file_idle_count('sparrow_k' + str(k), sys_load, distribution_name, idle_counts, num_dispatchers=num_dispatchers)

    #return np.array(task_wait_time).flatten()[0]

def pow_of_k_partitioned(k, num_dispatchers, distribution, distribution_name, inter_arrival, sys_load): # Change name
    queue_lens = [0] * num_machines
    task_lists = [] * num_machines
    task_wait_time = [] * num_machines
    queue_len_signal = [] * num_machines
    num_msg = 0
    idle_avg = 0
    idle_counts = []
    partition_size = num_machines /  num_dispatchers

    for i in range(num_machines):
        task_lists.append([])
        task_wait_time.append([])
        queue_len_signal.append([])

    for load in distribution:   # New task arrive
        
        num_idles = 0
        for queue_len in queue_lens:
            if queue_len ==0:
                num_idles += 1
        idle_counts.append(num_idles)
        idle_avg +=  num_idles

        task_lists, queue_lens, num_msg, _, _ = process_tasks_fcfs(inter_arrival, task_lists, queue_lens, num_msg)
        
        # Make decision:
        min_load = float("inf")
        dispatcher = random.randrange(num_dispatchers)  # Emulating arrival at a dispatcher randomly
        
        sample_indices = random.sample(range(dispatcher * partition_size, (dispatcher + 1) * partition_size), k) # k samples from workers available to that dispatcher
        #print dispatcher
        # print sample_indices
        
        for idx in sample_indices:
            sample = queue_lens[idx]
            if sample < min_load:
                min_load = sample
                target_machine = idx

        task_wait_time[target_machine].append(np.sum(task_lists[target_machine])) # Task assigned to target machine should wait at least as long as pending load
        queue_len_signal[target_machine].append(queue_lens[target_machine])
        task_lists[target_machine].append(load)
        queue_lens[target_machine] += 1

    idle_avg /= len(distribution)
    flat_task_wait_time = [item for sublist in task_wait_time for item in sublist]
    flat_queue_len_signal = [item for sublist in queue_len_signal for item in sublist]

    #task_wait_time = np.array(task_wait_time).flatten()

    print ("Avg. #Idle workers Pow-of-k Partitioned: " + str(idle_avg))
    print ("#msg Pow-of-k Partitioned: " + str(num_msg))
    print ("#msg/s Pow-of-k Partitioned: " + str((num_msg / (len(distribution) * inter_arrival))*(10**6)))
    msg_per_sec = (num_msg / (len(distribution) * inter_arrival))*(10**6)
    write_to_file_wait_time('racksched_k' + str(k), sys_load, distribution_name, flat_task_wait_time, num_dispatchers=num_dispatchers)
    write_to_file_queue_len_signal('racksched_k' + str(k), sys_load, distribution_name, flat_queue_len_signal, num_dispatchers=num_dispatchers)
    write_to_file_msg('racksched_k' + str(k), sys_load, distribution_name, [msg_per_sec], num_dispatchers=num_dispatchers)
    write_to_file_idle_count('racksched_k' + str(k), sys_load, distribution_name, idle_counts, num_dispatchers=num_dispatchers)

    #return np.array(task_wait_time).flatten()[0]

def jiq(k, num_dispatchers, distribution, distribution_name, inter_arrival, sys_load):
    nr.seed()
    queue_lens = [0] * num_machines
    task_lists = [] * num_machines
    task_wait_time = [] * num_machines
    idle_queue = [] * num_dispatchers
    queue_len_signal = [] * num_machines

    partition_size = num_machines / num_dispatchers

    num_msg = 0
    idle_avg = 0
    idle_counts = []

    for i in range(num_machines):
        task_lists.append([])
        task_wait_time.append([])
        queue_len_signal.append([])

    for i in range(num_dispatchers):
        idle_queue.append(range(i * partition_size, (i + 1) * partition_size))

    #print idle_queue

    for load in distribution:   # New task arrive
        #print queue_lens
        #print "\n List:"
        num_idles = 0
        for queue_len in queue_lens:
            if queue_len ==0:
                num_idles += 1
        idle_counts.append(num_idles)
        idle_avg +=  num_idles
        
        task_lists, queue_lens, num_msg, idle_queue, _ = process_tasks_fcfs(
                inter_arrival,
                task_lists,
                queue_lens, 
                num_msg, 1, 
                idle_queue, 
                num_dispatchers,
                k)
        
        # Make decision:
        dispatcher = random.randrange(num_dispatchers)  # Emulating arrival at a dispatcher randomly
        
        #sample_indices = random.sample(range(dispatcher * partition_size, (dispatcher + 1) * partition_size), k) # k samples from workers available to that dispatcher
        #print dispatcher
        # print sample_indices
        if idle_queue[dispatcher]:  # Dispatcher is aware of some idle servers
            target_machine = idle_queue[dispatcher].pop(0)
        else:   # No idle dispatcher is known, dispatch to a random server
            #print idle_queue
            #print("NOIDLE!")
            target_machine = nr.randint(0, num_machines)
            for idle_workers in idle_queue:
                if target_machine in idle_workers:   # Machine that gets a random-assigned task removes itself from the idle queue it has joined
                    idle_workers.remove(target_machine)
                    num_msg += 1

        task_wait_time[target_machine].append(np.sum(task_lists[target_machine])) # Task assigned to target machine should wait at least as long as pending load
        queue_len_signal[target_machine].append(queue_lens[target_machine])
        task_lists[target_machine].append(load)
        queue_lens[target_machine] += 1
    #task_wait_time = np.array(task_wait_time).flatten()
    idle_avg /= len(distribution)

    flat_task_wait_time = [item for sublist in task_wait_time for item in sublist]
    flat_queue_len_signal = [item for sublist in queue_len_signal for item in sublist]

    print ("Avg. #Idle workers JIQ: " + str(idle_avg))
    print ("#msg JIQ: " + str(num_msg))
    print ("#msg/s JIQ: " + str((num_msg / (len(distribution) * inter_arrival))*(10**6)))
    msg_per_sec = (num_msg / (len(distribution) * inter_arrival))*(10**6)
    write_to_file_wait_time('jiq_k' + str(k), sys_load, distribution_name, flat_task_wait_time, num_dispatchers=num_dispatchers)
    write_to_file_queue_len_signal('jiq_k' + str(k), sys_load, distribution_name, flat_queue_len_signal, num_dispatchers=num_dispatchers)
    write_to_file_msg('jiq_k' + str(k), sys_load, distribution_name, [msg_per_sec], num_dispatchers=num_dispatchers)
    write_to_file_idle_count('jiq_k' + str(k), sys_load, distribution_name, idle_counts, num_dispatchers=num_dispatchers)
    #return np.array(task_wait_time).flatten()[0]

def adaptive(k, num_dispatchers, distribution, distribution_name, inter_arrival, sys_load):
    nr.seed()
    queue_lens = [0] * num_machines
    task_lists = [] * num_machines
    task_wait_time = [] * num_machines
    idle_queue = [] * num_dispatchers
    known_queue_len = [] * num_dispatchers #indices for the machines
    queue_len_signal = [] * num_machines

    decision_type = [] * num_machines
    decision_tag = 0
    partition_size = num_machines / num_dispatchers

    num_msg = 0
    idle_avg = 0
    idle_counts = []
    dummy = 0
    for i in range(num_machines):
        task_lists.append([])
        task_wait_time.append([])
        queue_len_signal.append([])
        decision_type.append([])

    for i in range(num_dispatchers):
        idle_queue.append(range(i * partition_size, (i + 1) * partition_size))
        known_queue_len.append({})

    for task_idx, load in enumerate(distribution):   # New task arrive
        #print queue_lens
        #print "\n List:"
        min_load = float("inf")
        num_idles = 0
        for queue_len in queue_lens:
            if queue_len ==0:
                num_idles += 1
        idle_counts.append(num_idles)
        idle_avg +=  num_idles
        
        task_lists, queue_lens, num_msg, idle_queue, known_queue_len = process_tasks_fcfs(
                inter_arrival,
                task_lists,
                queue_lens, 
                num_msg, 
                1, 
                idle_queue, 
                num_dispatchers,
                k, 
                known_queue_len)
        
        # Make a decision:
        dispatcher = random.randrange(num_dispatchers)  # Emulating arrival at a dispatcher randomly

        #sample_indices = random.sample(range(dispatcher * partition_size, (dispatcher + 1) * partition_size), k) # k samples from workers available to that dispatcher
        #print dispatcher
        # print sample_indices
        if len(idle_queue[dispatcher]) > 0:  # Dispatcher is aware of some idle servers
            # print ("Idle queue: " + str(len(idle_queue[dispatcher])))
            # print (idle_queue)
            target_machine = idle_queue[dispatcher].pop(0)
            
        else:   # No idle server is known, dispatch to a random server    
            already_paired = False
            if (len(known_queue_len[dispatcher]) < partition_size):
                    num_msg += 1
                    random_machine = nr.randint(0, num_machines)
                    for d in range(num_dispatchers):
                        if random_machine in known_queue_len[d]:
                            already_paired = True
                    if not already_paired and queue_lens[random_machine] != 0: # Each server signal should be available at one dispatcher only
                        known_queue_len[dispatcher].update({random_machine: queue_lens[random_machine]}) # Add SQ signal
            if (len(known_queue_len[dispatcher]) > k): # Do shortest queue if enough info available
                sample_machines = random.sample(list(known_queue_len[dispatcher]), k) # k samples from queue lenghts available to that dispatcher
            #     #print (sample_machines)
                
                for machine in sample_machines:
                    sample_queue_len = known_queue_len[dispatcher][machine]
                    if sample_queue_len < min_load:
                        min_load = sample_queue_len
                        target_machine = machine
                decision_tag = 1 # SQ-based decision
                # print ("Target machine: " + str(target_machine))
                # print ("Load: " + str(min_load))
            else:
                target_machine = nr.randint(0, num_machines)
                decision_tag = 2  # Random-based decision
                # for d in range(num_dispatchers):
                #     if target_machine in known_queue_len[d]:
                #         already_paired = True
                # if not already_paired and queue_lens[target_machine] != 0: # Each server signal should be available at one dispatcher only
                #     known_queue_len[dispatcher].update({target_machine: queue_lens[target_machine]}) # Add SQ signal

                for idle_workers in idle_queue:
                    if target_machine in idle_workers:   # Machine that gets a random-assigned task removes itself from the idle queue it has joined
                        idle_workers.remove(target_machine)
                        num_msg += 1
            #print ("\n")
            #print (known_queue_len)
        
        for d in range(num_dispatchers):
            if target_machine in known_queue_len[d]:
                known_queue_len[d].update({target_machine: queue_lens[target_machine]}) # Update SQ signals
                num_msg += 1
        num_msg += 1 # random assigned machine will notify the scheduler about queue_length
        task_wait_time[target_machine].append(np.sum(task_lists[target_machine])) # Task assigned to target machine should wait at least as long as pending load
        # if np.sum(task_lists[target_machine]) > 0:
        #     if decision_type[task_idx]==0:
        #         print ("Conflict! ")
        #         print queue_lens[target_machine]
        #         print target_machine
        queue_len_signal[target_machine].append(queue_lens[target_machine])
        decision_type[target_machine].append(decision_tag)
        task_lists[target_machine].append(load)
        queue_lens[target_machine] += 1
    idle_avg /= len(distribution)

    flat_task_wait_time = [item for sublist in task_wait_time for item in sublist]
    flat_queue_len_signal = [item for sublist in queue_len_signal for item in sublist]
    flat_decision_type = [item for sublist in decision_type for item in sublist]
    print (dummy)
    print ("Avg. #Idle workers Adaptive: " + str(idle_avg))
    print ("#msg Adaptive: " + str(num_msg))
    print ("#msg/s Adaptive: " + str((num_msg / (len(distribution) * inter_arrival))*(10**6)))
    msg_per_sec = (num_msg / (len(distribution) * inter_arrival))*(10**6)
    write_to_file_wait_time('adaptive_k' + str(k), sys_load, distribution_name, flat_task_wait_time, num_dispatchers=num_dispatchers)
    write_to_file_decision_type('adaptive_k' + str(k), sys_load, distribution_name, decision_type, num_dispatchers=num_dispatchers)
    write_to_file_queue_len_signal('adaptive_k' + str(k), sys_load, distribution_name, flat_queue_len_signal, num_dispatchers=num_dispatchers)
    write_to_file_msg('adaptive_k' + str(k), sys_load, distribution_name, [msg_per_sec], num_dispatchers=num_dispatchers)
    write_to_file_idle_count('adaptive_k' + str(k), sys_load, distribution_name, idle_counts, num_dispatchers=num_dispatchers)

def print_result(result):
    print ("\nMax wait: " + str(np.max(result)))
    print ("Avg wait: " + str(np.mean(result)))
    #print("Ideal load:" + str((np.sum(distribution)/ num_machines)))
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
            inter_arrival = (mean_task_time / num_machines) / load

            print ("Inter arrival: " + str(inter_arrival))
            

            # random_proc = Process(target=random_uniform, args=(load_dist, task_distribution_name, inter_arrival, load, ))
            # random_proc.start()
            # #result = random_uniform(load_dist, task_distribution, inter_arrival, load)
            # #print_result(result, task_distribution, load)
            pow_of_k_proc = Process(target=pow_of_k, args=(2, num_dispatchers, load_dist, task_distribution_name, inter_arrival, load, ))
            pow_of_k_proc.start()
            # # oracle_proc = Process(target=pow_of_k, args=(num_machines, num_dispatchers, load_dist, task_distribution_name, inter_arrival, load, ))
            # # oracle_proc.start()
            pow_of_k_partitioned_proc = Process(target=pow_of_k_partitioned, args=(2, num_dispatchers, load_dist, task_distribution_name, inter_arrival, load, ))
            pow_of_k_partitioned_proc.start()
            jiq_proc = Process(target=jiq, args=(2, num_dispatchers, load_dist, task_distribution_name, inter_arrival, load, ))
            jiq_proc.start()
            adaptive_proc = Process(target=adaptive, args=(2, num_dispatchers, load_dist, task_distribution_name, inter_arrival, load, ))
            adaptive_proc.start()

            # pow_of_k(2, num_dispatchers, load_dist, task_distribution_name, inter_arrival, load)
            # pow_of_k_partitioned(2, num_dispatchers, load_dist, task_distribution_name, inter_arrival, load)
            # adaptive(2, num_dispatchers, load_dist, task_distribution_name, inter_arrival, load)
            # jiq(2, num_dispatchers, load_dist, task_distribution_name, inter_arrival, load)
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
# result = pow_of_k(num_machines, load_bimodal)
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


