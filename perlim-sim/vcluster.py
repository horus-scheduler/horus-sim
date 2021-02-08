import os
import random

from loguru import logger
from utils import *

class VirtualCluster:
    def __init__(self, 
        cluster_id,
        worker_start_idx,
        policy,
        host_list,
        load,
        task_distribution,
        target_parition_size=4,
        task_distribution_name='bimodal'):

        self.policy = policy
        self.cluster_id = cluster_id

        self.tor_spine_map = {}
        self.worker_start_idx = worker_start_idx

        self.last_task_arrival = 0.0
        self.task_idx = 0
        
        self.task_distribution = task_distribution

        self.num_workers = len(host_list)
        self.task_distribution_name = task_distribution_name
        self.queue_lens_workers = [0] * self.num_workers
        self.task_lists = [] * self.num_workers
        self.host_list = host_list
        self._get_tor_list_for_hosts(host_list)
        self.tor_id_unique_list = list(set(self.tor_id_list))
        self.num_tors = len(self.tor_id_unique_list)
        self.queue_lens_tors = [0.0] * self.num_tors
        self._get_spine_list_for_tors(target_parition_size, policy)
        self.num_spines = len(self.selected_spine_list)
        
        self.set_inter_arival(load)

        self.num_msg_spine = [0] * self.num_spines  
        self.num_msg_tor = [0] * self.num_tors
        self.switch_state_spine = [] * self.num_spines 
        self.switch_state_tor = [] * self.num_tors

        self.idle_queue_tor = [] * self.num_tors
        self.idle_queue_spine = [] * self.num_spines

        self.known_queue_len_spine = [] * self.num_spines  # For each spine, list of maps between torID and average queueLen if ToR
        self.known_queue_len_tor = [] * self.num_tors # For each tor, list of maps between workerID and queueLen
        
        self.log_queue_len_signal_tors = []  # For analysis only 
        self.log_queue_len_signal_workers = [] 
        self.log_task_wait_time = []
        self.log_task_transfer_time = []
        self.log_decision_type = [] 
        self.log_known_queue_len_spine = []

        for i in range(self.num_workers):
            self.task_lists.append([])
            
        for tor_idx in range(self.num_tors):
            self.idle_queue_tor.append([])
            for worker_idx in range(self.num_workers):
                if host_list[worker_idx] in get_host_range_for_tor(self.tor_id_unique_list[tor_idx]):
                    self.idle_queue_tor[tor_idx].append(worker_idx)
            self.known_queue_len_tor.append({})

        for spine_idx in range(self.num_spines):
            self.idle_queue_spine.append([])
            # Initialization: Tors physicall connected to seleceted pods are added to spine idle list
            spine_pod_idx = int(self.selected_spine_list[spine_idx] / spines_per_pod)
            for tor_idx in range(self.num_tors):
                tor_pod_idx = int(self.tor_id_unique_list[tor_idx] / tors_per_pod)
                if tor_pod_idx == spine_pod_idx:
                    self.idle_queue_spine[spine_idx].append(self.tor_id_unique_list[tor_idx])
                    continue
            self.known_queue_len_spine.append({})
        
        # logger.trace(self.idle_queue_tor)
        # logger.trace(self.selected_spine_list)
        # logger.trace(self.idle_queue_spine)
        #exit(0)

    def set_inter_arival(self, load):
        if self.task_distribution_name == "bimodal":
            mean_task_time = (mean_task_small + mean_task_medium) / 2
        elif self.task_distribution_name == "trimodal":
            mean_task_time = (mean_task_small + mean_task_medium + mean_task_large) / 3
        self.inter_arrival = (mean_task_time / self.num_workers) / load

    def _get_tor_list_for_hosts(self, host_list):
        tor_list = []
        for host_id in host_list:
            tor_list.append(get_tor_idx_for_host(host_id))
        self.tor_id_list = tor_list

    # TODO @parham: Implement spine selection algorithm here.
    # For now it randomly selects spines to be in the scheduling path with fixed L value
    def _get_spine_list_for_tors(self, target_parition_size, policy):
        available_spine_list = []
        selected_spine_list = []
        pod_list = []
        if policy == 'jiq' or policy == 'adaptive' or policy == 'pow_of_k_partitioned':
            for tor_idx in self.tor_id_unique_list:
                pod_idx = int(tor_idx / tors_per_pod)
                # First make sure we add 1 spine for each pod to scheduling path
                connected_spine_list = list(get_spine_range_for_tor(tor_idx))
                if pod_idx not in pod_list:
                    pod_list.append(pod_idx)
                    random_spine = random.choice(connected_spine_list)
                    selected_spine_list.append(random_spine)

                available_spine_list += connected_spine_list
            
            # Remove duplicates
            available_spine_list = list(set(available_spine_list))
            # Remove already selected spines
            for spine_idx in selected_spine_list:
                available_spine_list.remove(spine_idx)

            target_num_spines =  self.num_tors / target_parition_size
            # Randomly add more spines until condition satisfied
            while (len(selected_spine_list) < target_num_spines) and (len(available_spine_list) > 1):
                random_spine = random.choice(available_spine_list)
                available_spine_list.remove(random_spine)
                selected_spine_list.append(random_spine)
            
            if policy == 'pow_of_k_partitioned':
                for tor_id in tor_id_unique_list:
                    tor_pod_id = int(tor_id / tors_per_pod)
                    spines_in_pod = []
                    for spine_id in selected_spine_list:
                        spine_pod_id = int(spine_id / spines_per_pod)
                        if spine_pod_id == tor_pod_id:
                            spines_in_pod.append(spine_id)
                    # Static mapping of ToRs to Spines
                    random_spine = random.choice(spines_in_pod)
                    self.tor_spine_map.update({tor_id:random_spine})

        else:
            for tor_idx in self.tor_id_unique_list:
                connected_spine_list = list(get_spine_range_for_tor(tor_idx))
                selected_spine_list += connected_spine_list
            selected_spine_list = list(set(selected_spine_list))

        logger.trace(selected_spine_list)
        self.partition_size = self.num_tors / len(selected_spine_list)
        self.selected_spine_list = selected_spine_list

