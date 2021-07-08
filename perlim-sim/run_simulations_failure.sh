#!/bin/bash

working_dir=$1
k_value=$2
ratio=$3
id=$4
failure_mode=$5
id_max=$6

run_id=0
while [ $run_id -le 4 ]
	do
		rand=$(shuf -i 1-$id_max -n 1)
		#rand=177
		echo Failed Switch ID: $rand

		python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.1 -k $k_value -r $ratio -t bimodal -i $run_id -f $failure_mode --fid $rand 
		if [ $? != 0 ];
			then
				echo "exit 1"
				continue
			fi
		echo $run_id
		python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.2 -k $k_value -r $ratio -t bimodal -i $run_id -f $failure_mode --fid $rand &
		python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.3 -k $k_value -r $ratio -t bimodal -i $run_id -f $failure_mode --fid $rand &
		python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.4 -k $k_value -r $ratio -t bimodal -i $run_id -f $failure_mode --fid $rand &
		python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.5 -k $k_value -r $ratio -t bimodal -i $run_id -f $failure_mode --fid $rand &
		python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.6 -k $k_value -r $ratio -t bimodal -i $run_id -f $failure_mode --fid $rand &
		python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.7 -k $k_value -r $ratio -t bimodal -i $run_id -f $failure_mode --fid $rand &
		python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.8 -k $k_value -r $ratio -t bimodal -i $run_id -f $failure_mode --fid $rand &
		python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.9 -k $k_value -r $ratio -t bimodal -i $run_id -f $failure_mode --fid $rand &
		python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.95 -k $k_value -r $ratio -t bimodal -i $run_id -f $failure_mode --fid $rand &
		python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.99 -k $k_value -r $ratio -t bimodal -i $run_id -f $failure_mode --fid $rand &
		python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 1.0 -k $k_value -r $ratio -t bimodal -i $run_id -f $failure_mode --fid $rand &
		run_id=$(( $run_id + 1 ))
done