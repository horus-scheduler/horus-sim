import numpy.random as nr
import numpy as np
import math
import random 

from utils import *

class Task:
    def __init__(self, load, vcluster): 
        self.vcluster = vcluster
        self.task_idx = vcluster.task_idx
        self.load = load
        self.decision_tag = 0 

    def set_decision(self, first_spine, target_tor, target_worker): 
        self.target_worker = target_worker
        self.target_tor = target_tor
        self.first_spine = first_spine

        self.global_worker_id = self.vcluster.worker_start_idx + target_worker 
        self.global_host_id = self.vcluster.host_list[target_worker]
        self.global_spine_id = self.vcluster.selected_spine_list[first_spine]
        self.global_tor_id = self.vcluster.tor_id_unique_list[target_tor]

        self.network_time = calculate_network_time(self.global_spine_id, self.global_host_id) # This one changes during process
        self.num_hops = calculate_num_hops(self.global_spine_id, self.global_host_id)
        self.transfer_time = self.network_time