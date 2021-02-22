"""Usage:
multi_layer_lb.py [-d <working_dir>]

multi_layer_lb.py -h | --help
multi_layer_lb.py -v | --version

Arguments:
  -d <working_dir> Directory to save dataset "system_summary.log"
  
Options:
  -h --help  Displays this message
  -v --version  Displays script version
"""

import os
import random
import docopt

from loguru import logger
from utils import *

output_file = 'dataset'

def generate_worker_data():
    data = dict()
    tenants = Tenants(data, num_tenants=num_tenants, min_workers=min_workers, max_workers=max_workers)
    placement = Placement(data, num_pods=num_pods, num_leafs_per_pod=tors_per_pod, num_hosts_per_leaf=hosts_per_tor, max_workers_per_host=max_workers_per_host)
    return data

if __name__ == "__main__":
    arguments = docopt.docopt(__doc__, version='1.0')
    working_dir = arguments.get('-d', './')
    
    logger.add(working_dir + 'summary_system.log', filter=lambda record: record["extra"]["task"] == 'system', level="INFO")
    log_handler_system = logger.bind(task='system')

    log_handler_system.info("\nNumber of hosts: " + str(num_hosts))
    data = generate_worker_data()
    log_handler_system.info("\n"+str(data))
