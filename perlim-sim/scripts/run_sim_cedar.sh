#!/bin/bash

echo $SLURM_ARRAY_TASK_ID

working_dir=$1
k_value=$2
ratio=$3

sbatch sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio

sbatch sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio

sbatch sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio

sbatch sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio
sbatch sim_job_cedar.sh $working_dir adaptive 0.99 $k_value $ratio