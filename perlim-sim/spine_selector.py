import numpy.random as nr
import numpy as np
import math
import random 
from collections import OrderedDict
from operator import itemgetter 
import heapq
from utils import *

class SpineSelector:
    def __init__(self, per_spine_capacity): 
        self.per_spine_capacity = per_spine_capacity
        self.spine_throughput_capacity = {} # packets per second given to our system for each spine switch
        
        for spine_id in range(num_spines):
            self.spine_throughput_capacity[spine_id] = per_spine_capacity

    def select_spines(self, tor_id_unique_list, target_num_spines, max_pkt_per_sec):
        selected_spine_list = []
        pod_list = []
        available_spine_list = []
        max_num_spines = int(len(tor_id_unique_list) / 2)
        per_spine_pkt_per_sec = int(max_pkt_per_sec/target_num_spines)
        #print(target_num_spines)
        for tor_idx in tor_id_unique_list:
            pod_idx = int(tor_idx / tors_per_pod)
            connected_spine_list = list(get_spine_range_for_tor(tor_idx))
            if pod_idx not in pod_list:
                pod_list.append(pod_idx)
            available_spine_list.extend(connected_spine_list)
        
        # Remove duplicates
        available_spine_list = list(set(available_spine_list))
        available_spine_capacity = {}
        for spine_id in available_spine_list:
            available_spine_capacity[spine_id] = self.spine_throughput_capacity[spine_id]
        
        # If not enough capacity available, additional spine scheduler will be added
        can_be_placed = False
        while (can_be_placed == False):
            top_available_spines = heapq.nlargest(target_num_spines, available_spine_capacity, key=available_spine_capacity.get)
            can_be_placed = True
            for spine_id in top_available_spines:
                if (available_spine_capacity[spine_id] < per_spine_pkt_per_sec):
                    can_be_placed = False
            if can_be_placed == False:
                print("Not enough capacity in the spines of the pods, will use additiona spine... \n")
                if (target_num_spines < max_num_spines):
                    target_num_spines+=1
                    per_spine_pkt_per_sec = int(max_pkt_per_sec/target_num_spines)
                else:
                    print("Spine count will exceed the max_spine schedulers will use the spines anyway \n")
                    break

        #Initially try to add spines in the local pods to scheduling path
        while (len(selected_spine_list) < target_num_spines):
            select_spine_id = self.get_max_capacity_spine(available_spine_capacity)
            available_spine_capacity[select_spine_id] -= per_spine_pkt_per_sec
            self.spine_throughput_capacity[select_spine_id] -= per_spine_pkt_per_sec
            selected_spine_list.append(select_spine_id)

        return selected_spine_list

    def get_max_capacity_spine(self, spine_capacities):
        max_capacity = 0
        for spine_id in spine_capacities.keys():
            if spine_capacities[spine_id] > max_capacity:
                max_capacity = spine_capacities[spine_id]
                selected_spine_id = spine_id
        return selected_spine_id

