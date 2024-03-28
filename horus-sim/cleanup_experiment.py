"""Usage:
cleanup_experiment.py -d <working_dir> -t <task_distribution> [--colocate]

cleanup_experiment.py -h | --help
cleanup_experiment.py -v | --version

Arguments:
  -d <working_dir> Directory containing dataset which is also used for result files
  -t <task_distribution> Distribution name for generated tasks (bimodal|trimodal)
Options:
  -h --help  Displays this message
  -v --version  Displays script version
"""
import numpy.random as nr
import numpy as np
import math
import random 
import sys
import pandas as pd
import time
from multiprocessing import Process, Queue, Value, Array
from loguru import logger
import docopt
import shutil
import os

from utils import *
from task import Task

FWD_TIME_TICKS = 0.5 # Number of 0.1us ticks to pass in sim steps...
LOG_PROGRESS_INTERVAL = 600 # Dump some progress info periodically (in seconds)
result_dir = "./"
project_path="/home/pyassini/projects/def-hefeeda/pyassini/project-sched/in-network-scheduling/perlim-sim"

if __name__ == "__main__":
    arguments = docopt.docopt(__doc__, version='1.0')
    working_dir = arguments['-d']
    # global result_dir
    task_distribution_name = arguments['-t']
    is_colocate = arguments.get('--colocate', False)
    
    if is_colocate:
        arch_name = 'archive_' +  working_dir.replace('/', '') + '_col_' + task_distribution_name 
    else:
        arch_name = 'archive_' +  working_dir.replace('/', '') + '_' + task_distribution_name
    shutil.make_archive(arch_name, 'gztar', project_path + working_dir)
    shutil.rmtree(project_path + working_dir)
    os.mkdir(project_path + working_dir)
    shutil.copyfile(project_path + '/summary_system.log', project_path + working_dir + '/summary_system.log')
    shutil.copyfile(project_path + './summary_system_col.log', project_path + working_dir + '/summary_system_col.log')
