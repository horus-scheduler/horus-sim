#!/bin/bash
dist=$1
project_path=/home/pyassini/projects/def-hefeeda/pyassini/project-sched/in-network-scheduling/perlim-sim

working_dir=./result_l5_k2/
k_value=2
ratio=5

JOBID1_1=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist

JOBID1_2=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist

JOBID1_3=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

JOBID1_4=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.99 $k_value $ratio $dist

JOB_CLEAN_ID1=$(sbatch --dependency=afterok:$JOBID1_1:$JOBID1_2:$JOBID1_3:$JOBID1_4 --parsable $project_path/scripts/cleanup_job_cedar.sh $working_dir $dist)
#####################
working_dir=./result_l5_k4/
k_value=4
ratio=5

JOBID2_1=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist

JOBID2_2=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist

JOBID2_3=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

JOBID2_4=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.99 $k_value $ratio $dist

JOB_CLEAN_ID2=$(sbatch --dependency=afterok:$JOBID2_1:$JOBID2_2:$JOBID2_3:$JOBID2_4 --parsable $project_path/scripts/cleanup_job_cedar.sh $working_dir $dist)
##################
working_dir=./result_l5_k8/
k_value=8
ratio=5

JOBID3_1=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist

JOBID3_2=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist

JOBID3_3=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

JOBID3_4=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist

JOB_CLEAN_ID3=$(sbatch --dependency=afterok:$JOBID3_1:$JOBID3_2:$JOBID3_3:$JOBID3_4 --parsable $project_path/scripts/cleanup_job_cedar.sh $working_dir $dist)
##################
working_dir=./result_l10_k2/
k_value=2
ratio=10

JOBID4_1=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist

JOBID4_2=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist

JOBID4_3=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

JOBID4_4=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist

JOB_CLEAN_ID4=$(sbatch --dependency=afterok:$JOBID4_1:$JOBID4_2:$JOBID4_3:$JOBID4_4 --parsable $project_path/scripts/cleanup_job_cedar.sh $working_dir $dist)
##########
working_dir=./result_l10_k4/
k_value=4
ratio=10

JOBID5_1=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist

JOBID5_2=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist

JOBID5_3=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

JOBID5_4=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist

JOB_CLEAN_ID5=$(sbatch --dependency=afterok:$JOBID5_1:$JOBID5_2:$JOBID5_3:$JOBID5_4 --parsable $project_path/scripts/cleanup_job_cedar.sh $working_dir $dist)
##########
working_dir=./result_l10_k8/
k_value=8
ratio=10

JOBID6_1=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist

JOBID6_2=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist

JOBID6_3=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

JOBID6_4=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist

JOB_CLEAN_ID6=$(sbatch --dependency=afterok:$JOBID6_1:$JOBID6_2:$JOBID6_3:$JOBID6_4 --parsable $project_path/scripts/cleanup_job_cedar.sh $working_dir $dist)
##############
working_dir=./result_l20_k2/
k_value=2
ratio=20

JOBID7_1=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist

JOBID7_2=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist

JOBID7_3=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

JOBID7_4=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist

JOB_CLEAN_ID7=$(sbatch --dependency=afterok:$JOBID7_1:$JOBID7_2:$JOBID7_3:$JOBID7_4 --parsable $project_path/scripts/cleanup_job_cedar.sh $working_dir $dist)
##############
working_dir=./result_l20_k4/
k_value=4
ratio=20

JOBID8_1=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist

JOBID8_2=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist

JOBID8_3=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

JOBID8_4=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist

JOB_CLEAN_ID8=$(sbatch --dependency=afterok:$JOBID8_1:$JOBID8_2:$JOBID8_3:$JOBID8_4 --parsable $project_path/scripts/cleanup_job_cedar.sh $working_dir $dist)
################
working_dir=./result_l20_k8/
k_value=8
ratio=20

JOBID9_1=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist

JOBID9_2=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist

JOBID9_3=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

JOBID9_4=$(sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist)
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist
sbatch --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist

JOB_CLEAN_ID9=$(sbatch --dependency=afterok:$JOBID9_1:$JOBID9_2:$JOBID9_3:$JOBID9_4 --parsable $project_path/scripts/cleanup_job_cedar.sh $working_dir $dist)
###########################################################################################################
working_dir=./result_l15_k2/
k_value=2
ratio=15
JOBID10_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist

JOBID10_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist

JOBID10_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

JOBID10_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.99 $k_value $ratio $dist

JOB_CLEAN_ID9=$(sbatch --dependency=afterok:$JOBID9_1:$JOBID9_2:$JOBID9_3:$JOBID9_4 --parsable $project_path/scripts/cleanup_job_cedar.sh $working_dir $dist)

#########
working_dir=./result_l15_k4/
k_value=4
ratio=15
JOBID11_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist

JOBID11_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist

JOBID11_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

JOBID11_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.99 $k_value $ratio $dist

#######
working_dir=./result_l15_k8/
k_value=8
ratio=15
JOBID12_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist

JOBID12_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist

JOBID12_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

JOBID12_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.99 $k_value $ratio $dist

##################
working_dir=./result_l25_k2/
k_value=2
ratio=25
JOBID13_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist

JOBID13_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist

JOBID13_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

JOBID13_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.99 $k_value $ratio $dist

##############
working_dir=./result_l25_k4/
k_value=4
ratio=25
JOBID14_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist

JOBID14_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist

JOBID14_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

JOBID14_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.99 $k_value $ratio $dist

#############
working_dir=./result_l25_k8/
k_value=8
ratio=25
JOBID15_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k 0.99 $k_value $ratio $dist

JOBID15_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir pow_of_k_partitioned 0.99 $k_value $ratio $dist

JOBID15_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir jiq 0.99 $k_value $ratio $dist

JOBID15_1=$(sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.1 $k_value $ratio $dist)
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.3 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.5 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.7 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.9 $k_value $ratio $dist
sbatch --dependency=afterok:$JOB_CLEAN_ID9 --parsable $project_path/scripts/sim_job_cedar.sh $working_dir adaptive 0.99 $k_value $ratio $dist

