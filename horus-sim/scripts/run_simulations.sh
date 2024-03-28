#!/bin/bash

working_dir=$1
k_value=$2
ratio=$3
dist=$4
colocate=$5
id=0

python3 simulator.py -d $working_dir/ -p pow_of_k -l 0.1 -k $k_value -r $ratio -t $dist -i $id  -f none  $colocate --du &
python3 simulator.py -d $working_dir/ -p pow_of_k -l 0.3 -k $k_value -r $ratio -t $dist -i $id  -f none  $colocate --du &
python3 simulator.py -d $working_dir/ -p pow_of_k -l 0.5 -k $k_value -r $ratio -t $dist -i $id  -f none  $colocate --du &
python3 simulator.py -d $working_dir/ -p pow_of_k -l 0.7 -k $k_value -r $ratio -t $dist -i $id  -f none  $colocate --du &
python3 simulator.py -d $working_dir/ -p pow_of_k -l 0.9 -k $k_value -r $ratio -t $dist -i $id  -f none  $colocate --du &
python3 simulator.py -d $working_dir/ -p pow_of_k -l 0.99 -k $k_value -r $ratio -t $dist -i $id  -f none  $colocate --du &

# python3 simulator.py -d $working_dir/ -p pow_of_k -l 0.1 -k $k_value -r $ratio -t $dist -i $id  -f none  $colocate --centralized &
# python3 simulator.py -d $working_dir/ -p pow_of_k -l 0.3 -k $k_value -r $ratio -t $dist -i $id  -f none  $colocate --centralized &
# python3 simulator.py -d $working_dir/ -p pow_of_k -l 0.5 -k $k_value -r $ratio -t $dist -i $id  -f none  $colocate --centralized &
# python3 simulator.py -d $working_dir/ -p pow_of_k -l 0.7 -k $k_value -r $ratio -t $dist -i $id  -f none  $colocate --centralized &
# python3 simulator.py -d $working_dir/ -p pow_of_k -l 0.9 -k $k_value -r $ratio -t $dist -i $id  -f none  $colocate --centralized &
# python3 simulator.py -d $working_dir/ -p pow_of_k -l 0.99 -k $k_value -r $ratio -t $dist -i $id  -f none  $colocate --centralized &

# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.1 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate --du &
# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.2 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate --du &
# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.3 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate --du &
# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.4 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate --du &
# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.5 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate --du &
# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.6 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate --du &
# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.7 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate --du &
# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.8 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate --du &
# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.9 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate --du &
# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.99 -k $k_value -r $ratio -t $dist -i $id -f none $colocate --du &

python3 simulator.py -d $working_dir/ -p random_pow_of_k -l 0.1 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate &
python3 simulator.py -d $working_dir/ -p random_pow_of_k -l 0.3 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate &
python3 simulator.py -d $working_dir/ -p random_pow_of_k -l 0.5 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate &
python3 simulator.py -d $working_dir/ -p random_pow_of_k -l 0.7 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate &
python3 simulator.py -d $working_dir/ -p random_pow_of_k -l 0.9 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate &
python3 simulator.py -d $working_dir/ -p random_pow_of_k -l 0.99 -k $k_value -r $ratio -t $dist -i $id -f none $colocate &

python3 simulator.py -d $working_dir/ -p adaptive -l 0.1 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate &
python3 simulator.py -d $working_dir/ -p adaptive -l 0.3 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate &
python3 simulator.py -d $working_dir/ -p adaptive -l 0.5 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate &
python3 simulator.py -d $working_dir/ -p adaptive -l 0.7 -k $k_value -r $ratio -t $dist -i $id -f none $colocate  &
python3 simulator.py -d $working_dir/ -p adaptive -l 0.9 -k $k_value -r $ratio -t $dist -i $id -f none $colocate  &
python3 simulator.py -d $working_dir/ -p adaptive -l 0.99 -k $k_value -r $ratio -t $dist -i $id -f none $colocate &


# python3 simulator.py -d $working_dir/ -p adaptive -l 0.1 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate --du &
# python3 simulator.py -d $working_dir/ -p adaptive -l 0.3 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate --du &
# python3 simulator.py -d $working_dir/ -p adaptive -l 0.5 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate --du &
# python3 simulator.py -d $working_dir/ -p adaptive -l 0.7 -k $k_value -r $ratio -t $dist -i $id -f none $colocate --du &
# python3 simulator.py -d $working_dir/ -p adaptive -l 0.9 -k $k_value -r $ratio -t $dist -i $id -f none $colocate --du &
# python3 simulator.py -d $working_dir/ -p adaptive -l 0.99 -k $k_value -r $ratio -t $dist -i $id -f none $colocate --du &

# python3 simulator.py -d $working_dir/ -p jiq -l 0.1 -k $k_value -r $ratio -t $dist -i $id -f none &
# python3 simulator.py -d $working_dir/ -p jiq -l 0.3 -k $k_value -r $ratio -t $dist -i $id -f none &
# python3 simulator.py -d $working_dir/ -p jiq -l 0.5 -k $k_value -r $ratio -t $dist -i $id -f none &
# python3 simulator.py -d $working_dir/ -p jiq -l 0.7 -k $k_value -r $ratio -t $dist -i $id -f none &
# python3 simulator.py -d $working_dir/ -p jiq -l 0.9 -k $k_value -r $ratio -t $dist -i $id -f none &
# python3 simulator.py -d $working_dir/ -p jiq -l 0.99 -k $k_value -r $ratio -t $dist -i $id -f none &

# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.1 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate &
# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.3 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate &
# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.5 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate &
# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.7 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate &
# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.9 -k $k_value -r $ratio -t $dist -i $id -f none  $colocate &
# python3 simulator.py -d $working_dir/ -p pow_of_k_partitioned -l 0.99 -k $k_value -r $ratio -t $dist -i $id -f none $colocate &
#random_pow_of_k