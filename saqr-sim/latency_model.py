import random
import pandas as pd
from loguru import logger
import ast
from utils import *

class LatencyModel:
    def __init__(self, working_dir):
        self.data = self.read_dataset(working_dir)
        self.failure_detection_latency = self.get_failure_detection_latency()

    def read_dataset(self, working_dir):
        file_path = working_dir + 'rtt_results.txt'  
        fp = open(file_path)
        lines = fp.readlines()
        data = ast.literal_eval(lines[0])
        return dict(data)

    def get_failure_detection_latency(self):
        return TICKS_PER_MICRO_SEC * random.choice(self.data['failure_detection_1'])

    def get_notification_to_client_latency(self, controller_pod_idx, client_pod_idx):
        is_in_same_pod = (controller_pod_idx == client_pod_idx)
    
        if (is_in_same_pod):
            return TICKS_PER_MICRO_SEC * (float(random.choice(self.data['rtt_inside_pod_1'])) / 2)
        else:
            use_dcn_1 = random.random() > 0.5
            if use_dcn_1: 
                return TICKS_PER_MICRO_SEC * (float(random.choice(self.data['rtt_dcn_1'])) / 2)
            else:
                return TICKS_PER_MICRO_SEC * (float(random.choice(self.data['rtt_dcn_2'])) / 2)

    def get_one_way_latency(self):
        is_in_same_pod = random.random() < (1/num_pods)  # Flip a coin
        if (is_in_same_pod): # RTT in same pod consisting of 8 hops 2*(2*us, 2*ds), estimate each hop and then times 2
            return TICKS_PER_MICRO_SEC * (float(random.choice(self.data['rtt_inside_pod_1'])) / 8) * 2
        else:
            use_dcn_1 = random.random() > 0.5
            if use_dcn_1:  # Inter-pod latency has 12 hops, estimate each hop and then times 3
                return TICKS_PER_MICRO_SEC * ((float(random.choice(self.data['rtt_dcn_1'])) / 12) * 3)
            else:
                return  TICKS_PER_MICRO_SEC * ((float(random.choice(self.data['rtt_dcn_2'])) / 12) * 3)