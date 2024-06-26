"""Usage:
generate_dataset.py -d <working_dir> -t <num_tenants> --min=<min_workers> --max=<max_workers> [--uniform] [--colocate]

generate_dataset.py -h | --help
generate_dataset.py -v | --version

Arguments:
  -d <working_dir> Directory to save dataset "system_summary.log"
  -t <num_tenants>
  --min=<min_workers>
  --max=<max_workers>
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

def generate_worker_data(working_dir, num_tenants, min_workers, max_workers, is_uniform, is_colocate):
    data = dict()
    if (is_uniform):
        worker_dist = 'uniform'
    else:
        worker_dist = 'expon'
    if is_colocate:
        data = read_dataset(working_dir, False)
    else:
        tenants = Tenants(data, worker_dist=worker_dist, num_tenants=num_tenants, min_workers=min_workers, max_workers=max_workers)
    if is_colocate:
        placement = Placement(data, num_pods=num_pods, num_leafs_per_pod=tors_per_pod, num_hosts_per_leaf=hosts_per_tor, max_workers_per_host=max_workers_per_host, dist='colocate-colocate-uniform')
    else:
        placement = Placement(data, num_pods=num_pods, num_leafs_per_pod=tors_per_pod, num_hosts_per_leaf=hosts_per_tor, max_workers_per_host=max_workers_per_host)
    return data

if __name__ == "__main__":
    arguments = docopt.docopt(__doc__, version='1.0')
    working_dir = arguments.get('-d', './')
    min_workers = int(arguments.get('--min', 10))
    max_workers = int(arguments.get('--max', 1000))
    num_tenants = int(arguments.get('-t', 1))
    print (num_tenants)
    is_colocate = arguments.get('--colocate', False)
    is_uniform = arguments.get('--uniform', False)
    print (is_uniform)
    if is_colocate:
        file_path = working_dir + 'summary_system_col.log'
    else:
        file_path = working_dir + 'summary_system.log'

    logger.add(file_path, filter=lambda record: record["extra"]["task"] == 'system', level="INFO")
    log_handler_system = logger.bind(task='system')

    log_handler_system.info("\nNumber of hosts: " + str(num_hosts))
    data = generate_worker_data(working_dir, num_tenants, min_workers, max_workers, is_uniform, is_colocate)
    log_handler_system.info("\n"+str(data))
    
