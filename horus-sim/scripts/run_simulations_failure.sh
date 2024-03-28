#!/bin/bash

working_dir=$1
k_value=$2
run_id=$3
num_runs=$4
failure_mode=$5
switch_id_max=$6


while [ $run_id -le $num_runs ]
        do
                rand=$(shuf -i 1-$switch_id_max -n 1)
                echo Failed Switch ID: $rand

                python3 simulator.py -d ./result_failure_spine_l10/ -p adaptive -l 1.0 -k $k_value -r 10 -t bimodal -i $run_id -f $failure_mode --fid $r$
                python3 simulator.py -d ./result_failure_spine_l20/ -p adaptive -l 1.0 -k $k_value -r 20 -t bimodal -i $run_id -f $failure_mode --fid $r$
                python3 simulator.py -d ./result_failure_spine_l40/ -p adaptive -l 1.0 -k $k_value -r 40 -t bimodal -i $run_id -f $failure_mode --fid $r$
                run_id=$(( $run_id + 1 ))
done


