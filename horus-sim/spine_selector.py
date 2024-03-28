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
        self.spine_rack_count = {}
        
        for spine_id in range(num_spines):
            self.spine_throughput_capacity[spine_id] = per_spine_capacity
            self.spine_rack_count[spine_id] = 0

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
        available_spine_rack_count = {}
        for spine_id in available_spine_list:
            available_spine_capacity[spine_id] = self.spine_throughput_capacity[spine_id]
            available_spine_rack_count[spine_id] = self.spine_rack_count[spine_id]
        # print (available_spine_list)
        # print (available_spine_capacity)
        # print (available_spine_rack_count)

        # If not enough capacity available, additional spine scheduler will be added
        can_be_placed = False
        while (can_be_placed == False):
            #top_available_spines = heapq.nlargest(target_num_spines, available_spine_capacity, key=available_spine_capacity.get)
            spine_candidates = {} # The spines in pods that can handle pkt rate
            for spine_id in available_spine_capacity:
                if available_spine_capacity[spine_id] >= per_spine_pkt_per_sec:
                    spine_candidates[spine_id] = available_spine_capacity[spine_id]
            
            if len(spine_candidates) < target_num_spines: # There are not enough spines with the requested capacity
                if (target_num_spines < max_num_spines): 
                    target_num_spines += 1    # Distribute to more spines
                    per_spine_pkt_per_sec = int(max_pkt_per_sec/target_num_spines)
                else:
                    print("Spine count will exceed the max_spine schedulers \n")
                    break
            else:
                can_be_placed = True
        
        # Select the ones that have most
        top_candidate_spines = heapq.nsmallest(target_num_spines, available_spine_rack_count, key=available_spine_rack_count.get)
        #print(target_num_spines)
        
        for spine_id in top_candidate_spines:
            self.spine_rack_count[spine_id] += len(tor_id_unique_list)
            self.spine_throughput_capacity[spine_id] -= per_spine_pkt_per_sec
            selected_spine_list.append(spine_id)
        #print (self.spine_rack_count)
        # print ("Selected the spines :")
        # print (selected_spine_list)
        # print("\n\n")
        return selected_spine_list

