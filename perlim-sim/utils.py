import os
import random
import sys
import math
import csv
import numpy.random as nr
import numpy as np
from loguru import logger

from tenants import Tenants
from placement import Placement

result_dir = "./results_scale_0/"

num_tenants = 3000
num_pods = 48
num_spines = int(num_pods * num_pods / 2)
num_tors = int(num_pods * num_pods / 2)

spines_per_pod = int(num_spines / num_pods)
tors_per_pod = int(num_tors / num_pods)
hosts_per_tor = 24
num_hosts = tors_per_pod * num_pods * hosts_per_tor

cross_pod_assignment = False 
logger.info("Number of hosts: " + str(num_hosts))

logger.add(result_dir + 'summary.log', level='INFO')
data = dict()
tenants = Tenants(data, num_tenants=num_tenants, min_workers=10, max_workers=2000)
placement = Placement(data, num_pods=num_pods, num_leafs_per_pod=tors_per_pod, num_hosts_per_leaf=hosts_per_tor, max_workers_per_host=16)
logger.info(data)
logger.info('Generating tenants is done')

#loads = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6,0.7, 0.8, 0.85, 0.9, 0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99]
loads = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99]
#loads = [0.4]
task_time_distributions = ['bimodal']

#num_tasks = 6000
num_ticks = 500000000

# Each tick is 0.1us so task load values are in 0.1us
mean_task_small = 500.0
mean_task_medium = 5000.0
mean_task_large = 50000.0

mu = 0.0
sigma = 1.0

#Assuming each tick is 0.1 us
LINK_DELAY_TOR = range(40, 100)
LINK_DELAY_SPINE = range(30, 60) 
LINK_DELAY_CORE = range(20 , 40)

# LINK_DELAY_TOR = range(0, 1)
# LINK_DELAY_SPINE = range(0, 1) 
# LINK_DELAY_CORE = range(0 , 1)


def generate_task_dist(num_workers, distribution_name=None):
    log_normal_mean = math.e ** (mu + sigma ** 2 / 2)

    # TODO @parham: Should we set number of tasks in each cluster?
    # Choose total taks amount relative to number of workers
    num_tasks = 40 * num_workers
    
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
        return log_trimodal

def get_tor_id_for_host(host_id):
    return int(host_id / hosts_per_tor)

def get_host_range_for_tor(tor_idx):
    hosts_start_idx = tor_idx * hosts_per_tor # Each ToR is has access to workers_per_tor machines
    return range(hosts_start_idx, hosts_start_idx + hosts_per_tor)

#Used for partitioned pow-of-k SQ
def get_tor_partition_range_for_spine(spine_idx): 
    partition_size = int(tors_per_pod / spines_per_pod)
    tor_start_idx = spine_idx * partition_size
    return range(tor_start_idx, tor_start_idx + partition_size)

def get_spine_idx_for_tor(tor_idx):
    print (spines_per_pod)
    partition_size = tors_per_pod / spines_per_pod
    return int(tor_idx / partition_size)

def get_spine_range_for_tor(tor_idx):
    pod_idx_for_tor = int(tor_idx / tors_per_pod)
    spine_start_idx = pod_idx_for_tor * spines_per_pod
    return range(spine_start_idx, spine_start_idx + spines_per_pod)

def calculate_tor_queue_len(tor_id, queue_lens_workers, host_list):
    host_range = get_host_range_for_tor(tor_id)
    sum_queue_len = 0
    num_workers_in_tor = 0
    for idx, host in enumerate(host_list):
        if host in host_range: # Host connected to ToR so will consider this in calculations
            sum_queue_len += queue_lens_workers[idx]
            num_workers_in_tor += 1
    return float(sum_queue_len) / num_workers_in_tor

def get_worker_indices_for_tor(tor_id, host_list):
    host_range = get_host_range_for_tor(tor_id)
    workers_list = []
    for idx, host in enumerate(host_list):
        if host in host_range: # Host of worker connected to ToR
            workers_list.append(idx)
            
    return workers_list

def calculate_network_time(first_spine, target_host):
    # At leaast 2 hop from spine to worker
    network_time = random.sample(LINK_DELAY_TOR, 1)[0] + random.sample(LINK_DELAY_SPINE, 1)[0] 
    connected_tors = get_tor_partition_range_for_spine(first_spine)
    target_tor = get_tor_id_for_host(target_host)
    
    # print ("First spine: " + str(first_spine))
    # print ("Target worker: " + str(target_worker))
    # print ("Connected tors: " )
    #print connected_tors

    if target_tor not in connected_tors: # 2x Core-spine delay
        network_time += random.sample(LINK_DELAY_CORE, 1)[0]
        network_time += random.sample(LINK_DELAY_CORE, 1)[0]
    #print ("Network time: " + str(network_time))
    return network_time

def calculate_num_hops(first_spine, target_host):
    connected_tors = get_tor_partition_range_for_spine(first_spine)
    target_tor = get_tor_id_for_host(target_host)
    num_hops = 2
    if target_tor not in connected_tors: # 2x Core-spine delay
        num_hops += 1
    return num_hops


def calculate_idle_count(queue_lens_workers):
    num_idles = 0
    for queue_len in queue_lens_workers:
        if queue_len ==0:
            num_idles += 1
    return num_idles

def write_to_file(metric, policy, load, distribution, results):
    filename = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_t' + str(num_tenants) + '_' +metric +  '_' + str(load) + '.csv'
    np_array = np.array(results)
    with open(result_dir + filename, 'wb') as output_file:
        #writer = csv.writer(output_file, delimiter=',')
        #writer.writerow(np_array)
        np.savetxt(output_file, [np_array], delimiter=', ', fmt='%.2f')
        #np.savetxt(output_file, np_array, delimiter=",")
        