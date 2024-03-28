import os
import random
import sys
import math
import csv
import numpy.random as nr
import numpy as np
import ast
from tenants import Tenants
from placement import Placement
import fcntl

TICKS_PER_MICRO_SEC = 1000

# Mean per-hop delay (us)
PER_HOP_LATENCY = 1
LOSS_PROBABILITY = 0.0

max_workers_per_host = 64

num_pods = 48
num_spines = int(num_pods * num_pods / 2)
num_tors = int(num_pods * num_pods / 2)
spines_per_pod = int(num_spines / num_pods)
tors_per_pod = int(num_tors / num_pods)
hosts_per_tor = 24

num_hosts = tors_per_pod * num_pods * hosts_per_tor

PER_SPINE_CAPACITY = 2e8 # Assumed #Pkts/sec allocated for scheduling on each switch

cross_pod_assignment = True 

task_time_distributions = ['bimodal']

# Task durations in ns
mean_exp_task = 100 * TICKS_PER_MICRO_SEC

# Each tick is 0.1us so task load values are in 0.1us
mean_task_small = 50 * TICKS_PER_MICRO_SEC
mean_task_medium = 500 * TICKS_PER_MICRO_SEC
mean_task_large = 5000 * TICKS_PER_MICRO_SEC

mu = 0.0
sigma = 1.0

# Hop delays in ns
LINK_DELAY_TOR = range(1000, 10000)
LINK_DELAY_SPINE = range(1000, 10000) 
LINK_DELAY_CORE = range(1000, 10000)

NUM_TASK_PER_WORKER = 160
FALCON_QUEUE_SLOTS = 128000
FALCON_RETRY_INTERVAL = 100 * TICKS_PER_MICRO_SEC

def read_dataset(working_dir, is_colocate=False):
    if is_colocate:
        file_path = working_dir + 'summary_system_col.log'
    else:
        file_path = working_dir + 'summary_system.log'

    fp = open(file_path)
    lines = fp.readlines()
    data = ast.literal_eval(lines[3])
    return dict(data)

def generate_task_dist(num_workers, distribution_name=None):
    log_normal_mean = math.e ** (mu + sigma ** 2 / 2)

    # Choose total taks amount relative to number of workers
    # This is to make sure every cluster is running for same amount of *time* in our experiments
    # E.g 1 worker executes 10 tasks per second, at full load we 100 tasks means 10 second experiment
    # Now if there are 10 workers in vcluster with same tasks, at full load 1000 tasks means 10 second experiment (shorter inter-arrivals at full load)
    num_tasks = NUM_TASK_PER_WORKER * num_workers
    
    load_lognormal = nr.lognormal(mu, sigma, num_tasks)
    load_uniform = nr.uniform(0, 2*mean_task_small, num_tasks)

    bimodal_small = np.random.normal(mean_task_small, mean_task_small/10, int(num_tasks/2))
    bimodal_medium = np.random.normal(mean_task_medium, mean_task_medium/10, int(num_tasks/2))
    load_bimodal = np.concatenate([bimodal_small, bimodal_medium])

    indices = np.arange(load_bimodal.shape[0])
    np.random.shuffle(indices)
    load_bimodal = load_bimodal[indices]

    trimodal_small = np.random.normal(mean_task_small, mean_task_small/10, int(num_tasks/3))
    trimodal_medium = np.random.normal(mean_task_medium, mean_task_medium/10, int(num_tasks/3))
    trimodal_large = np.random.normal(mean_task_large, mean_task_large/10, int(num_tasks/3))
    load_trimodal = np.concatenate([trimodal_small, trimodal_medium, trimodal_large])

    indices = np.arange(load_trimodal.shape[0])
    np.random.shuffle(indices)

    load_trimodal = load_trimodal[indices]
    if distribution_name == 'bimodal':
        return load_bimodal
    elif distribution_name == 'trimodal':
        return load_trimodal
    elif distribution_name == 'exponential':
        load_exponential = np.round(np.random.exponential(mean_exp_task, num_tasks), 5)
        return load_exponential

def get_tor_id_for_host(host_id):
    return int(host_id / hosts_per_tor)

def get_host_range_for_tor(tor_idx):
    hosts_start_idx = tor_idx * hosts_per_tor # Each ToR is has access to workers_per_tor machines
    return range(hosts_start_idx, hosts_start_idx + hosts_per_tor)

#Used for partitioned pow-of-k 
def get_tor_partition_range_for_spine(spine_idx): 
    partition_size = int(tors_per_pod / spines_per_pod)
    tor_start_idx = spine_idx * partition_size
    return range(tor_start_idx, tor_start_idx + partition_size)

def get_spine_idx_for_tor(tor_idx):
    partition_size = tors_per_pod / spines_per_pod
    return int(tor_idx / partition_size)

def get_spine_range_for_tor(tor_idx):
    pod_idx_for_tor = int(tor_idx / tors_per_pod)
    spine_start_idx = pod_idx_for_tor * spines_per_pod
    return range(spine_start_idx, spine_start_idx + spines_per_pod)

# ToR and spines in the same pod are connected otherwise path is: src leaf->local spine->core->dst spine
def get_tor_spine_hops(tor_idx, spine_idx):
    return 1 if get_spine_idx_for_tor(tor_idx) == spine_idx else 3

def calculate_tor_queue_len(tor_id, queue_lens_workers, host_list):
    host_range = get_host_range_for_tor(tor_id)
    sum_queue_len = 0
    num_workers_in_tor = 0
    worker_list = get_worker_indices_for_tor(tor_id, host_list)
    #print(f"Calculating tor queue len, worker list: {worker_list}")
    for idx in worker_list:
        sum_queue_len += queue_lens_workers[idx]
        
    return float(sum_queue_len) / len(worker_list)

def get_worker_indices_for_tor(tor_id, host_list):
    host_range = get_host_range_for_tor(tor_id)
    workers_list = []
    for idx, host in enumerate(host_list):
        if (host >= host_range[0]) and (host <= host_range[-1]): # Host of worker connected to ToR
            workers_list.append(idx)
    return workers_list

def get_num_workers_in_rack(tor_id, host_list):
    worker_list = get_worker_indices_for_tor(tor_id, host_list)
    return len(worker_list)

def calculate_idle_count(queue_lens_workers):
    num_idles = 0
    for queue_len in queue_lens_workers:
        if queue_len ==0:
            num_idles += 1
    return num_idles

def get_policy_file_tag(policy, k):
    if policy == 'random_pow_of_k':
        policy_file_tag = 'random_racksched_k' + str(k)
    if policy == 'central_queue':
        policy_file_tag = 'falcon'
    elif policy == 'pow_of_k':
        policy_file_tag = 'racksched_k' + str(k)
    elif policy == 'pow_of_k_partitioned':
        policy_file_tag = 'racksched_partitioned_k' + str(k)
    elif policy == 'jiq':
        policy_file_tag = 'jiq_k' + str(k)
    elif policy == 'adaptive':
        policy_file_tag = 'adaptive_k' + str(k)
    policy_file_tag += '_l' + str(LOSS_PROBABILITY) + '_d' + str(PER_HOP_LATENCY)
    return policy_file_tag

# Selects the smallest value among samples 
def select_sample(input_list, sample_indices):
    min_load = float("inf")
    for idx in sample_indices:
        sample = input_list[idx]
        if sample < min_load:
            min_load = sample
            target_child = idx

    return target_child

def write_to_file(working_dir, metric, policy, load, distribution, results, run_id, cluster_id=None, is_colocate=False, append=False):
    open_opts = 'wb'
    run_id = 0
    if append:
        open_opts = 'ab'
    open_opts = 'wb'
    if cluster_id != None:
        filename = policy + '_' + distribution + '_' + metric +  '_' + str(load) +  '_c' + str(cluster_id) + '_r' + str(run_id) + '.csv'
    else:
        filename = policy + '_' + distribution + '_' + metric +  '_' + str(load) + '_r' + str(run_id) + '.csv'
    np_array = np.array(results)
    with open(working_dir + filename, open_opts) as output_file:
        fcntl.flock(output_file, fcntl.LOCK_EX)
        np.savetxt(output_file, [np_array], delimiter=', ', fmt='%.2f')
        fcntl.flock(output_file, fcntl.LOCK_UN)
        
        
