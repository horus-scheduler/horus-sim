import os
import random
import math
from utils import *

WORKER_CLIENT_RATIO = 20

class Event:
    def __init__(self, event_type, vcluster=None, task=None, component_id=None, client_id=None):
        self.type = event_type # A string indicating type of event
        self.vcluster = vcluster # virtual cluster ID for the event
        self.task=task # If the event is about a task, it holds the task object here 
        self.component_id = component_id # ID of the target component that will process this event
        self.client_id = client_id # ID of the client that initially sent the task to system (used in scheduler failure simulations)
    
    def print_debug(self):
        if (self.vcluster):
            return(self.vcluster.cluster_id)

class VirtualCluster:
    def __init__(self, 
        cluster_id,
        worker_start_idx,
        policy,
        host_list,
        load,
        spine_selector,
        target_partition_size=10,
        task_distribution_name='bimodal',
        is_single_layer=False):

        self.is_single_layer = is_single_layer
        self.policy = policy
        self.max_wait_time = 0

        self.cluster_id = cluster_id
        self.spine_selector = spine_selector

        self.tor_spine_map = {}
        self.worker_start_idx = worker_start_idx
        
        self.num_workers = len(host_list)
        self.task_distribution = generate_task_dist(self.num_workers, task_distribution_name)

        self.task_distribution_name = task_distribution_name

        self.host_list = host_list
        self._get_tor_list_for_hosts(host_list)
        self.tor_id_unique_list = list(set(self.tor_id_list))

        self.num_tors = len(self.tor_id_unique_list)
        self.workers_per_tor = [0] * self.num_tors
        self._set_load(load)
        self._get_spine_list_for_tors(target_partition_size, policy)
        self.num_spines = len(self.selected_spine_list)
        self.init_cluster_state()
        # for i, spine_id in enumerate(self.selected_spine_list):
        #     worker_count = 0
        #     for tor_idx in self.spine_tor_map[i]:
        #         worker_count += len(self.idle_queue_tor[tor_idx])
        self.init_failure_params()

    def set_client_controller_latency(self, index, latency_ticks):
        if self.max_controller_latency < latency_ticks:
            self.max_controller_latency = latency_ticks
        self.client_controller_latency[index] = latency_ticks

    def init_failure_params(self):
        self.num_clients = max(1, int(self.num_workers / WORKER_CLIENT_RATIO))
        self.client_pods = [int(random.choice(self.tor_id_unique_list) / tors_per_pod) for i in range(self.num_clients)]
        self.client_controller_latency = [0] * self.num_clients
        self.client_notified = [False] * self.num_clients
        self.client_spine_list = [] * self.num_clients
        for client_idx in range(self.num_clients):
            self.client_spine_list.append(self.selected_spine_list.copy())

        self.max_controller_latency = 0
        self.num_failed_tasks = 0
        self.num_scheduled_tasks = 0
        self.failover_converged = False
        self.failover_converge_latency = 0

    def init_cluster_state(self):
        self.queue_lens_tors = [0.0] * self.num_tors
        self.last_task_arrival = 0.0
        self.task_idx = 0
        
        self.arrival_delay_exponential = random.expovariate(1.0 / self.inter_arrival)

        self.queue_lens_workers = [0] * self.num_workers
        self.task_lists = [] * self.num_workers
        self.curr_task_start_time = [0] * self.num_workers
        self.idle_queue_tor = [] * self.num_tors
        self.idle_queue_spine = [] * self.num_spines
        self.tor_idle_link = [-1] * self.num_tors # This is a single value representing the Index of linked idle spine for each leaf (stored at leaf switch) 

        if self.policy == 'central_queue':
            self.falcon_queue = []

        self.known_queue_len_spine = [] * self.num_spines  # For each spine, list of maps between torID and average queueLen if ToR
        self.load_track_leafs = [] * self.num_spines
        self.log_queue_len_signal_tors = []  # For analysis only 
        self.log_queue_len_signal_workers = [] 
        self.log_task_wait_time = []
        self.log_response_time = []
        self.log_task_transfer_time = []
        self.log_decision_type = [] 
        self.log_known_queue_len_spine = []
        self.log_zero_wait_tasks = 0
        self.log_total_tasks = 0
        self.idle_counts = []
        self.log_msg_sq = 0
        self.log_msg_iq_sample = 0
        self.log_msg_iq_link = 0
        self.log_msg_other = 0

        for tor_idx in range(self.num_tors):
            self.workers_per_tor[tor_idx] = get_num_workers_in_rack(self.tor_id_unique_list[tor_idx], self.host_list)

        for spine_idx in range(self.num_spines):
            self.idle_queue_spine.append([])
            self.known_queue_len_spine.append({})
            self.load_track_leafs.append([])

        for spine_idx in range(self.num_spines):
            for tor_idx in self.spine_tor_map[spine_idx]:
                self.known_queue_len_spine[spine_idx].update({tor_idx: 0}) # This is to indicate that spine will track queue len of ToR from now on    

        #print (self.known_queue_len_spine)
        
        for i in range(self.num_workers):
            self.task_lists.append([])

        if (self.is_single_layer):
            for spine_idx in range(self.num_spines):
                for worker_idx in range(self.num_workers):
                    self.idle_queue_spine[spine_idx].append(worker_idx)
        else:
            for tor_idx in range(self.num_tors):
                self.idle_queue_tor.append([])
                for worker_idx in range(self.num_workers):
                    if self.host_list[worker_idx] in get_host_range_for_tor(self.tor_id_unique_list[tor_idx]):
                        self.idle_queue_tor[tor_idx].append(worker_idx)
                
            
            added_tor_idx = 0
            # Add tors to idle list of spines in Roundrobin
            while (added_tor_idx < self.num_tors):
                for i, spine_id in enumerate(self.selected_spine_list):
                    if added_tor_idx == self.num_tors:
                        break
                    self.idle_queue_spine[i].append(added_tor_idx)
                    self.tor_idle_link[added_tor_idx] = i 
                    added_tor_idx += 1

            # print ("Cluster ID: " + str(self.cluster_id) + " num Tors: " + str(self.num_tors))
            # print (self.selected_spine_list)
            # for tor_idx, tor_id in enumerate(self.tor_id_unique_list):
            #     print("TOR ID: " + str(tor_id) + " num workers: " + str(len(self.idle_queue_tor[tor_idx])))
            
            # print(self.idle_queue_tor)
            # print(self.tor_id_unique_list)
            # print(self.idle_queue_spine)
            #print('\n')
  
    def _set_load(self, load):
        self.load = load
        if self.task_distribution_name == "bimodal":
            mean_task_time = (mean_task_small + mean_task_medium) / 2
        elif self.task_distribution_name == "trimodal":
            mean_task_time = (mean_task_small + mean_task_medium + mean_task_large) / 3
        elif self.task_distribution_name == "exponential":
            mean_task_time = mean_exp_task
        
        self.min_inter_arrival = (mean_task_time / self.num_workers)
        self.inter_arrival = self.min_inter_arrival / load    
        
    def _get_tor_list_for_hosts(self, host_list):
        tor_list = []
        for host_id in host_list:
            tor_list.append(get_tor_id_for_host(host_id))
        
        self.tor_id_list = tor_list

    # TODO @parham: Implement spine selection algorithm here.
    # For now it randomly selects spines to be in the scheduling path with fixed L value
    def _get_spine_list_for_tors(self, target_partition_size, policy, replication_factor=2):
        available_spine_list = []
        selected_spine_list = []
        pod_list = []
        tor_id_unique_list = []
        max_pkt_per_sec = ((1.0/self.min_inter_arrival) * (10**6) * TICKS_PER_MICRO_SEC) * 2
        
        if self.policy == 'central_queue':
            self.selected_spine_list = [0]
            return
        if (target_partition_size != 0):
            #target_partition_size = max(4, target_partition_size)
            target_num_spines = max(int(self.num_tors / target_partition_size), 1)
            # if (target_num_spines == 1) and (self.num_tors >= 4*replication_factor):
            #     target_num_spines = replication_factor
        else:
            if (self.num_tors >= 4*replication_factor):
                target_num_spines = replication_factor
            else:
                target_num_spines = math.ceil(replication_factor/4)

        if self.is_single_layer: # In this case, we simulate a flat, centralized scheduler only single switch will be in charge
            self.selected_spine_list = [0] 
            self.partition_size =  int(math.ceil(self.num_workers / len(self.selected_spine_list)))
            
        else:
            self.selected_spine_list = self.spine_selector.select_spines(self.tor_id_unique_list, target_num_spines, max_pkt_per_sec)
            self.partition_size = int(math.ceil(self.num_tors / len(self.selected_spine_list)))
    
        self.spine_tor_map = {}
        mapped_tor_idx = 0
        for i, spine_id in enumerate(self.selected_spine_list):
            self.spine_tor_map.update({i:[]})
        
        while (mapped_tor_idx < self.num_tors):
            for i, spine_id in enumerate(self.selected_spine_list):
                if mapped_tor_idx == self.num_tors:
                    break
                self.tor_spine_map.update({mapped_tor_idx : i})
                self.spine_tor_map[i].append(mapped_tor_idx)
                mapped_tor_idx += 1
        

            # print(len(self.tor_id_unique_list))
            # print(self.tor_id_unique_list)
            # print(self.spine_tor_map)
            # print(self.tor_spine_map)
            #print("cluster_id :" + str(self.cluster_id) + " spines: " +str(self.selected_spine_list))        
        return

