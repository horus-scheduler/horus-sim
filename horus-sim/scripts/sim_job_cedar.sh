#!/bin/bash
#SBATCH --mem-per-cpu=24G
#SBATCH --time=48:00:00
#SBATCH --account=def-hefeeda
#SBATCH --mail-user=pyassini@sfu.ca
#SBATCH --array=0-0
#SBATCH --mail-type=FAIL

working_dir=$1
policy=$2
load=$3
k_value=$4
ratio=$5
dist=$6
col=$7
du=$8
project_path=/home/pyassini/projects/def-hefeeda/pyassini/project-sched/in-network-scheduling/perlim-sim

module load python/3.6
source /home/pyassini/projects/def-hefeeda/pyassini/project-sched/cedar/env/bin/activate

python $project_path/simulator.py -d $project_path/$working_dir/ -p $policy -l $load -k $k_value -r $ratio -t $dist -i 0 -f none $col $du