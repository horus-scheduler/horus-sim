## In-Network Task Scheduler Simulator
This repo contains the event-based simulator for in-network scheduling project [Horus: Granular In-Network Task Scheduler for Cloud Datacenters](https://www.usenix.org/conference/nsdi24/presentation/yassini).
In addition to Horus the simulator supports multiple different policies (e.g Join-idle-queue and power-of-d choices). It is also used for comparison against the state-of-the-art in-network shceduler [RackSched](https://www.usenix.org/conference/osdi20/presentation/zhu) in large-scale datacenters.
## Dependencies
The ``requiremnts.txt`` file contains the essential libraries for running the code. The code is tested using Python 3.6.3.

## Simulated Environment and Setup
### Topology
The simulator uses a fat-tree Clos topology. The size is configurable using the _k_ parameter which indicates number of pods. In our simulations we used ``k=48`` where we have 1152 spine and 1152 leaf switches (racks). Each rack has 24 servers which in total gives us 27,648 servers. 

This can be changed using the ``num_pods`` and ```hosts_per_tor``` variables in the ```utils.py``` file. Note that the dataset for worker placements needs to be re-generated for a new topology. 

### Virtualization
We simulate an environment where 1K virtual clusters work in parallel in the datacenter. Each virtual cluster has its own set of workers where workers might be placed on different racks. The tasks that belong to one virtual cluster will be only scheduled on workers that belong to that virtual cluster. Example of such environment is the multi-tenant datacenters  where each tenant has some Virtual Machines (VMs) and can run applications on their VMs.

> In this document and in codes we might use the term "tenant" instead of virtual cluster.

#### Worker Placement Dataset
To simulate that environment, we first generate a dataset for the placement of workers of each virtual cluster on the physical hosts. 
The files for the dataset used in our simulations are available XXX.
The placement algorithm is based on the VM placement algorithm used in simulations of these papers [ \[1](https://dl.acm.org/doi/pdf/10.1145/2535372.2535380), [2\]
](https://courses.engr.illinois.edu/ece598hpn/fa2019/papers/elmo.pdf). 

The number of workers per virtual cluster follows an exponential distribution with min=50, max=20K and mean=685, where the total number of workers is 685K. 

To generate a new dataset, use the following script:
```
python generate_dataset.py -d <directory> -t <num_tenants> --min=<min_workers_per_tenant> --max=<max_workers_per_tenant>
```
The result will be sotred in the given directory under a file with name ```summary_system.log```.

In addtition, the placement of workers of each tenant can be changed to be more colocated (span fewer number of racks). To do so run the same script and pass the directory that contains the original dataset and add the option ``--colocate``. It will generate an additional file in the same directory with name ```summary_system_col.log```. 
> Note: in colocate dataset, the number of workers per tenant will the same as the first dataset (summary_system.log) but the physical host IDs for the workers will be re-assigned to make a colocated placement.

### Latency model
In some simulations we use the real-world traces from [Pingmesh](https://conferences.sigcomm.org/sigcomm/2015/pdf/papers/p139.pdf) paper. The summary of rtts are compiled in to the ```rtt_results.txt`` file. The simulator will read and use these values.

## How it works?
The simulation starts with reading the dataset for worker placements in virtual clusters. The ``VirtualCluster`` class in ``vcluster.py`` holds the necessary info about the virtual cluster and the control plane logic for initializing the state:
Each cluster uses specific switches in the datacenter for *scheduling*. That is, all of the leaf switches that are physically connected to the machines that run workers. A fraction of spine switches that run 
XXX Some details to be added

## Running Simulations

To run the simulations, put the generated dataset and rtt_results.txt file in the desired directory. Also, make a sub-dir named "analysis" where the summary of results will be stored.

```
python3 simulator.py 

-d <working_dir> -p <policy> -l <load> -k <k value> -r <spine ratio>  -t <task distribution> -i <experiment id> [--delay <delay per link (micro sec)>] [--loss <loss probability per hop (fraction)>] -f <failure mode> [--fid <failed switch id>] [--colocate] [--centralized] [--du] [--all]

```

### Policy
The input can be one of the following:

- **pow_of_k**: Simulates schedulers that use power-of-k choices algorithm for scheduling. In case of hierarchical scheduling (spine-leaf layers), spine switches track load of every rack in virtual cluster (replicated state). Also, each spine switch can any schedule task on every rack. 
- **random_pow_of_k**: Simulates a system with rack-local schedulers where the tasks are sent to one of the racks randomly. Each rack-local scheduler will use pow-of-k policy to select a worker inside the rack.
- **pow_of_k_partitioned**: Similar to pow_of_k, but in hierarchical schedulers, each spine scheduler tracks a subset of racks and when a task arrives each spine can send the task to its subset of racks (no replicated state).
- **jiq**:  Simulates schedulers that use [Join-idle-queue (JIQ)](https://www.microsoft.com/en-us/research/publication/join-idle-queue-a-novel-load-balancing-algorithm-for-dynamically-scalable-web-services/) algorithm where they only track the idle nodes and use this info for scheduling tasks. At leaf layer, each scheduler tracks the idle workers in its own rack. At spine layer, leaf switches use the probing  mechanism (with two probes) as in the original paper to join the idle list of one of the spines. 
- **adaptive**: This is **Horus** policy. It uses the idle info and load info (power-of-two choices) adaptively to schedule tasks.


### Load
The input should in format 0.x where x<1. It indicates the load relative to the maximum capacity of the clusters. For each cluster this load translates to mean inter-arrival time for tasks (higher load means smaller inter-arrival delays). We ran experiments for 0.1, 0.2 ... 0.99 load values.

### k-value
It controls the number of samples for power-of-k scheduling in the mentioned policies. 

### spine ratio
It defines the ratio of #leaf-schedulers / #spine-schedulers. This controls the number of spine switches that will act as scheduler. For example, consider spine ratio = 5. Virtual cluster A has 100 workers placed on 10 different racks. In this case, all 10 leaf switches will handle rack-local scheduling decisions and there will be (10/5) two spine schedulers that track these racks for A. Similaly, virtual cluster B that has workers across 40 racks, will use (40/5), 8 spine scheduelrs.  
Options used in our experiments was 10, 20, 40. 
> If spine ratio is set to 0, the simulator assigns a fixed redundancy number for number of schedulers (e.g 2 spine schedulers regardless of number of racks).

### task distribution
It defines the distribution of the task service times in the workload. 
The options can be:
* exponential: exponential service time distribution with mean=100us.
* bimodal: 50%-50us, 50%-500us.
* trimodal: 33%-50us, 33%-500us, 33%5000us. 

### expeirment id
Just use for differntiating the result files in case we run a single setup multiple times. The files will be named as *X_experiment-id.csv*. 

### Failure Mode
It controls if a failure should be simulated in the experiment or not. There are currently two options: 
* "none": Use this input for normal case simulations.
* "spine": Use this for spine switch failure.
> In the case of "spine" failure, the ID of the switch that will fail during the simulation should be also passed to the program (see next part).

### failed switch id
The ID of switch that fails during the experiment. We currenlty support spine failure simulations. The ID in the simulated topology can be in range [0,1151] (inclusive). 

### --colocate
Optional input, tells the simulator to use the colocate version of dataset for simulation (reads and parses *summary_system_col.log*). 

### --centralized
Optional input, used for simulating the *Oracle* scheduler where a single component (switch in our case) can observe the load of all workers in the whole datacenter and it handles all scheduling decisions. Note that the policy that this scheduler uses is configurable through  ```-p policy``` arg as mentioned. 
> For normal multi-switch (spine-leaf) schedulers, we do not include "--centralized" in the args. 

### --du
Delayed Updates: Optional input, it controls the process of updating switch states *after making a scheduling decisions*. 

Schedulers in Racksched do not update the load state after they make a decision and the state is **only updated when a reply from the worker arrives at the switch**. To simulate such case, we pass ``--du`` to the simulator. For Horus schedulers we do not use this option by default. It is also used in breaking down Horus benefits to observe the impact of delayed updates.

> Note: for pow_of_k policy and pow_of_k_partitioned, the default setting is to pass --du. The output files in the other case (run without --du option), the output files will conatin a "_iu_" in their name which indicates that (instant updates were enabled). For horus policy, the default is instant updates so in case that run with --du option, horus output files will contain a "_du_" to indicate that it is delayed updates.

### --all
If passed, it forces simulator to save all output files. In normal case the output will contain *waiting_time* and *response_time* for every task and the message rate metrics for switches. If --all is passed, the output will also include the *transfer time* (time spend for task in network before arrives at worker), and *decision type* (for horus) which indicates that each scheduling decision is made based on idle selection (0) or pow of two choices (1). 
> For final simulations we did not pass --all to reduce the space used for each experiment. The additional metrics were useful in intermediate stages when desiging the policy and state distribution.

 
## Example Usage 

### Result folder and datasets
The ```result-dir``` folder provides an example of the experiment result directory. It also includes the **Datasets** used in our experiments and the RTT latency file. The experiments on analysis of Horus (breaking down benefits and impact of d samples) are done on smaller dataset which is provided in this folder. To run experiments on the small data set, rename the file to ```summary_system.log``` and run the simulator. 

### Python Script 
Below are some example cases for running the experiments that are included in the paper. 

- Racksched-Random (RS-R), bimodal task distribution.
```
python3 simulator.py -d $working_dir/ -p random_pow_of_k -l <load> -k 2 -r 40 -t bimodal -i 0 -f none --delay 5 --loss 0.00001 --du
```

- Racksched-Hierarchical (RS-H), exponential task distribution.
```
python3 simulator.py -d $working_dir/ -p pow_of_k -l <load> -k 2 -r 40 -t exponential -i 0 -f none --delay 5 --loss 0.00001 --du
```

- Horus, trimodal task distribution.
```
python3 simulator.py -d $working_dir/ -p adaptive -l <load> -k 2 -r 40 -t trimodal -i 0 -f --delay 5 --loss 0.00001 none 
```

- Horus, failure simulations, r=40, bimodal task distribution, failing spine switch with  ID=100.
```
python3 simulator.py -d $working_dir/l20/ -p adaptive -l load -k 2 -r 40 -t bimodal -i $run_id -f spine --fid 100
```
> We run the same experiment for different *load* values [0.1, 0.99].
> To analyze impact of loss or delay we vary the parameters and repeat each experiment
