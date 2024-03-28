import numpy.random as nr
import numpy as np
import math
import random 

import utils

class Task:
    def __init__(self, latency_model, load, vcluster, arrive_tick): 
        self.vcluster = vcluster
        self.task_idx = vcluster.task_idx
        self.load = load
        self.decision_tag = 0 
        self.transfer_time = 0
        self.network_time = 0 # Per hop
        self.arrive_time = arrive_tick
        self.latency_model = latency_model

    def calculate_num_hops(self, spine_id, tor_id):
        connected_tors = utils.get_tor_partition_range_for_spine(spine_id)
        num_hops = 1
        if tor_id not in connected_tors: # tor-spine + spine-core + core-spine + spine-tor
            num_hops = 4
        return num_hops
        
    def set_decision_spine(self, first_spine, target_tor):
        self.first_spine = first_spine
        self.target_tor = target_tor
        self.global_spine_id = self.vcluster.selected_spine_list[first_spine]
        self.global_tor_id = self.vcluster.tor_id_unique_list[target_tor]
        self.num_hops = self.calculate_num_hops(self.global_spine_id, self.global_tor_id)
        self.network_time = self.latency_model.get_in_network_delay(n_hops=self.num_hops)
        self.transfer_time = self.network_time

    def set_decision_tor(self, target_worker):
        self.target_worker = target_worker
        self.global_worker_id = self.vcluster.worker_start_idx + target_worker
        self.global_host_id = self.vcluster.host_list[target_worker]
        self.network_time = self.latency_model.get_in_network_delay(n_hops=1)
        self.transfer_time += self.network_time

    def set_decision_centralized(self, first_spine, target_tor, target_worker):
        self.first_spine = first_spine
        self.target_tor = target_tor
        self.target_worker = target_worker
        self.global_spine_id = self.vcluster.selected_spine_list[first_spine]
        self.global_tor_id = self.vcluster.tor_id_unique_list[target_tor]
        self.global_host_id = self.vcluster.host_list[target_worker]
        self.global_worker_id = self.vcluster.worker_start_idx + target_worker
        self.num_hops = self.calculate_num_hops(self.global_spine_id, self.global_host_id)
        self.network_time = self.latency_model.get_in_network_delay(n_hops=self.num_hops) + self.latency_model.get_in_network_delay(n_hops=1)
        self.transfer_time = self.network_time