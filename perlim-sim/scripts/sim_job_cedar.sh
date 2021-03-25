#!/bin/bash
#SBATCH --mem-per-cpu=4G
#SBATCH --time=30:00:00
#SBATCH --account=def-hefeeda
#SBATCH --mail-user=pyassini@sfu.ca
#SBATCH --array=0-0

working_dir=$1
policy=$2
load=$3
k_value=$4
ratio=$5
project_path=/home/pyassini/projects/def-hefeeda/pyassini/project-sched/in-network-scheduling/perlim-sim

module load python/3.6
source /home/pyassini/projects/def-hefeeda/pyassini/project-sched/cedar/env/bin/activate

python $project_path/multi_layer_lb.py -d $project_path/$working_dir/ -p $policy -l $load -k $k_value -r $ratio -t exponential -i $SLURM_ARRAY_TASK_ID
