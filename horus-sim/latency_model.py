import random
import pandas as pd
from loguru import logger
import ast
import utils
import numpy as np

LOSS_MODE_UNIFORM = 1
LOSS_MODE_MARKOV = 2

# Markov states
FAIL_STATE = 1
SUCCESS_STATE = 0

class LatencyModel:
    def __init__(self):
        self.loss_probability = 0.0
        self.loss_mode = LOSS_MODE_UNIFORM
        self.latency_hist = []
    @property
    def failure_detection_latency(self):
        return self.get_failure_detection_latency()

    def set_loss_p(self, probability):
        self.loss_probability = probability
    
    def set_loss_mode(self, mode):
        self.loss_mode = mode
    
    def is_pkt_sent(self):
        if self.loss_mode == LOSS_MODE_UNIFORM:
            return random.random() >= self.loss_probability
            
        elif self.loss_mode == LOSS_MODE_MARKOV:
            return self.markov_state_transition()
    
    # Sets the packet loss and burst ratio for markov process.
    def set_markov_params(self, p_loss, burst_ratio):
        self.p_loss = p_loss
        # Ratio: avg. length of consecutive failure / avg. length of consecutive loss in a random network (uniform p)
        self.burst_ratio = burst_ratio
        # Calculating p_f_s (failure to success) and p_s_f(success to failure) in the two-state markov chain
        self.p_f_s = (1 - p_loss) / burst_ratio 
        self.p_s_f = (p_loss * self.p_f_s) / (1 - p_loss)
        self.state = self.SUCCESS_STATE

    # Calculates the new packet loss state based on the
    def markov_state_transition(self):
        if self.state == SUCCESS_STATE:
            if random.random() < self.p_s_f:
                self.state = FAIL_STATE
        if self.state == FAIL_STATE:
            if random.random() < self.p_f_s:
                self.state = SUCCESS_STATE
        return True

    def read_dataset(self, working_dir):
        file_path = working_dir + 'rtt_results.txt'  
        fp = open(file_path)
        lines = fp.readlines()
        data = ast.literal_eval(lines[0])
        self.data = data
        # Using similar distribution to real data but scale it to match the input per hop latency
        if utils.PER_HOP_LATENCY > 0:
            scale_factor = (np.mean(np.array(self.data['rtt_inside_pod_1'])) / utils.PER_HOP_LATENCY)
            self.latency_population = [(val / scale_factor) * utils.TICKS_PER_MICRO_SEC for val in self.data['rtt_inside_pod_1']]
            self.latency_prob = [0.1] * len(self.latency_population)

    def get_failure_detection_latency(self):
        return utils.TICKS_PER_MICRO_SEC * random.choice(self.data['failure_detection_1'])

    def get_notification_to_client_latency(self, controller_pod_idx, client_pod_idx):
        is_in_same_pod = (controller_pod_idx == client_pod_idx)
    
        if (is_in_same_pod):
            return utils.TICKS_PER_MICRO_SEC * (float(random.choice(self.data['rtt_inside_pod_1'])) / 2)
        else:
            use_dcn_1 = random.random() > 0.5
            if use_dcn_1: 
                return utils.TICKS_PER_MICRO_SEC * (float(random.choice(self.data['rtt_dcn_1'])) / 2)
            else:
                return utils.TICKS_PER_MICRO_SEC * (float(random.choice(self.data['rtt_dcn_2'])) / 2)
    
    def get_in_network_delay(self, n_hops):
        tot_latency = 0
        if utils.PER_HOP_LATENCY > 0:
            per_hop_latencies = np.random.choice(self.latency_population, size=n_hops, p=self.latency_prob)
        else:
            per_hop_latencies = [0]
        self.latency_hist.extend(per_hop_latencies)
        for latency in per_hop_latencies:
            tot_latency += latency
        return tot_latency
        
    def get_one_way_latency(self):
        is_in_same_pod = random.random() < (1/utils.num_pods)  # Flip a coin
        if (is_in_same_pod): # RTT in same pod consisting of 8 hops 2*(2*us, 2*ds), estimate each hop and then times 2
            return utils.TICKS_PER_MICRO_SEC * (float(random.choice(self.data['rtt_inside_pod_1'])) / 8) * 2
        else:
            use_dcn_1 = random.random() > 0.5
            if use_dcn_1:  # Inter-pod latency has 12 hops, estimate each hop and then times 3
                return utils.TICKS_PER_MICRO_SEC * ((float(random.choice(self.data['rtt_dcn_1'])) / 12) * 3)
            else:
                return  utils.TICKS_PER_MICRO_SEC * ((float(random.choice(self.data['rtt_dcn_2'])) / 12) * 3)