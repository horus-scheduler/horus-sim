import numpy.random as nr
import numpy as np
import math
import random 

from utils import *

class Task:
    def __init__(self, load, vcluster, arrive_tick): 
        self.vcluster = vcluster
        self.task_idx = vcluster.task_idx
        self.load = load
        self.decision_tag = 0 
        self.arrive_time = arrive_tick

    def calculate_network_time(self, first_spine, target_host):
        # At least 2 hop from spine to worker
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

    def calculate_num_hops(self, first_spine, target_host):
        connected_tors = get_tor_partition_range_for_spine(first_spine)
        target_tor = get_tor_id_for_host(target_host)
        num_hops = 2
        if target_tor not in connected_tors: # 2x Core-spine delay
            num_hops += 1
        return num_hops

    def set_decision(self, first_spine, target_tor, target_worker): 
        self.target_worker = target_worker
        self.target_tor = target_tor
        self.first_spine = first_spine

        self.global_worker_id = self.vcluster.worker_start_idx + target_worker 
        self.global_host_id = self.vcluster.host_list[target_worker]
        self.global_spine_id = self.vcluster.selected_spine_list[first_spine]
        self.global_tor_id = self.vcluster.tor_id_unique_list[target_tor]


        self.network_time = self.calculate_network_time(self.global_spine_id, self.global_host_id) 
        self.num_hops = self.calculate_num_hops(self.global_spine_id, self.global_host_id)
        self.transfer_time = self.network_time

