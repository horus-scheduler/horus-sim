#!/bin/bash
#SBATCH --mem-per-cpu=2G
#SBATCH --time=6:00:00
#SBATCH --account=def-hefeeda
#SBATCH --mail-user=pyassini@sfu.ca

working_dir=$1
dist=$2
project_path=/home/pyassini/projects/def-hefeeda/pyassini/project-sched/in-network-scheduling/perlim-sim

module load python/3.6
source /home/pyassini/projects/def-hefeeda/pyassini/project-sched/cedar/env/bin/activate

python $project_path/cleanup_experiment.py -d $project_path/$working_dir/ -t dist --colocate
