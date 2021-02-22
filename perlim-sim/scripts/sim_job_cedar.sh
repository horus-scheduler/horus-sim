#!/bin/bash
#SBATCH --mem-per-cpu=2G
#SBATCH --time=12:00:00
#SBATCH --account=def-hefeeda
#SBATCH --mail-user=pyassini@sfu.ca
#SBATCH --array=0-4

working_dir=$1
policy=$2
load=$3
k_value=$4
ratio=$5

python multi_layer_lb.py -d $working_dir/ -p $policy -l $load -k $k_value -r $ratio -t bimodal -i $SLURM_ARRAY_TASK_ID &
