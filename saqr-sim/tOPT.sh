working_dir=$1

# adaptive
python3 -u simulator.py -d $working_dir -p adaptive -l 0.1 -k 2 -r 40 -t exponential -i 0 -f none  &
python3 -u simulator.py -d $working_dir -p adaptive -l 0.3 -k 2 -r 40 -t exponential -i 0 -f none  &
python3 -u simulator.py -d $working_dir -p adaptive -l 0.5 -k 2 -r 40 -t exponential -i 0 -f none  &
python3 -u simulator.py -d $working_dir -p adaptive -l 0.7 -k 2 -r 40 -t exponential -i 0 -f none  &
python3 -u simulator.py -d $working_dir -p adaptive -l 0.9 -k 2 -r 40 -t exponential -i 0 -f none  &
python3 -u simulator.py -d $working_dir -p adaptive -l 0.99 -k 2 -r 40 -t exponential -i 0 -f none &

# Topt
python3 -u simulator.py -d $working_dir -p pow_of_k -l 0.1 -k 1000000 -r 0 -t exponential -i 0 -f none  --centralized &
python3 -u simulator.py -d $working_dir -p pow_of_k -l 0.3 -k 1000000 -r 0 -t exponential -i 0 -f none  --centralized &
python3 -u simulator.py -d $working_dir -p pow_of_k -l 0.5 -k 1000000 -r 0 -t exponential -i 0 -f none  --centralized &
python3 -u simulator.py -d $working_dir -p pow_of_k -l 0.7 -k 1000000 -r 0 -t exponential -i 0 -f none  --centralized &
python3 -u simulator.py -d $working_dir -p pow_of_k -l 0.9 -k 1000000 -r 0 -t exponential -i 0 -f none  --centralized &
python3 -u simulator.py -d $working_dir -p pow_of_k -l 0.99 -k 1000000 -r 0 -t exponential -i 0 -f none  --centralized &

# racksched - H
python3 -u simulator.py -d $working_dir -p random_pow_of_k -l 0.1 -k 2 -r 40 -t exponential -i 0 -f none &
python3 -u simulator.py -d $working_dir -p random_pow_of_k -l 0.3 -k 2 -r 40 -t exponential -i 0 -f none &
python3 -u simulator.py -d $working_dir -p random_pow_of_k -l 0.5 -k 2 -r 40 -t exponential -i 0 -f none &
python3 -u simulator.py -d $working_dir -p random_pow_of_k -l 0.7 -k 2 -r 40 -t exponential -i 0 -f none &
python3 -u simulator.py -d $working_dir -p random_pow_of_k -l 0.9 -k 2 -r 40 -t exponential -i 0 -f none &
python3 -u simulator.py -d $working_dir -p random_pow_of_k -l 0.99 -k 2 -r 40 -t exponential -i 0 -f none 

