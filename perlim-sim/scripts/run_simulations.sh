#!/bin/bash

working_dir=$1
id=$2

python3 multi_layer_lb.py -d $working_dir/ -p pow_of_k -l 0.1 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p pow_of_k -l 0.3 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p pow_of_k -l 0.5 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p pow_of_k -l 0.7 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p pow_of_k -l 0.9 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p pow_of_k -l 0.99 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p jiq -l 0.1 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p jiq -l 0.3 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p jiq -l 0.5 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p jiq -l 0.7 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p jiq -l 0.9 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p jiq -l 0.99 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.1 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.3 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.5 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.7 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.9 -k 2 -r 10 -t bimodal -i $id &

python3 multi_layer_lb.py -d $working_dir/ -p adaptive -l 0.99 -k 2 -r 10 -t bimodal -i $id &