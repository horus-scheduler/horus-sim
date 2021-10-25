#!/bin/bash

echo $SLURM_ARRAY_TASK_ID

working_dir=$1
k_value=$2
ratio=$3
dist=$4
col=$5
project_path=/home/pyassini/projects/def-hefeeda/pyassini/project-sched/in-network-scheduling/perlim-sim

#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir central_queue 0.1 $k_value $ratio $dist $col
#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir central_queue 0.3 $k_value $ratio $dist $col
#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir central_queue 0.5 $k_value $ratio $dist $col
#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir central_queue 0.7 $k_value $ratio $dist $col
#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir central_queue 0.9 $k_value $ratio $dist $col
#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir central_queue 0.99 $k_value $ratio $dist $col

sbatch $project_path/scripts/sim_job_cedar.sh $working_dir random_pow_of_k 0.1 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir random_pow_of_k 0.2 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir random_pow_of_k 0.3 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir random_pow_of_k 0.4 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir random_pow_of_k 0.5 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir random_pow_of_k 0.6 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir random_pow_of_k 0.7 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir random_pow_of_k 0.8 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir random_pow_of_k 0.9 $k_value $ratio $dist  $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir random_pow_of_k 0.99 $k_value $ratio $dist $col --du

sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.2 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.4 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.6 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.8 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist $col --du
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist $col --du

sbatch $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist $col
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.2 $k_value $ratio $dist $col
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist $col
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.4 $k_value $ratio $dist $col
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist $col
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.6 $k_value $ratio $dist $col
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist $col
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.8 $k_value $ratio $dist $col
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist $col
sbatch $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.99 $k_value $ratio $dist $col

#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist
#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.2 $k_value $ratio $dist
#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.4 $k_value $ratio $dist
#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.6 $k_value $ratio $dist
#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.8 $k_value $ratio $dist
#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

#sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist
# sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.2 $k_value $ratio $dist
# sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
# sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.4 $k_value $ratio $dist
# sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
# sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.6 $k_value $ratio $dist
# sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
# sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.8 $k_value $ratio $dist
# sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
# sbatch $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist