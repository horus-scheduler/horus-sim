import numpy.random as nr
import numpy as np
import math
import random 
import matplotlib.pyplot as plt
import pandas as pd

#import seaborn as sns

# BAR_PLOT_TICKS = 6

# # Line Styles
# DEFAULT_LINE_WIDTH = 4
# ALTERNATIVE_LINE_WIDTH = 5
# SMALL_LINE_WIDTH = 2
# CAP_SIZE = 4
# LINE_STYLES = ['-', '--', '-.', ':']

# # Font
# TEX_ENABLED = False
# TICK_FONT_SIZE = 24
# AXIS_FONT_SIZE = 24
# LEGEND_FONT_SIZE = 22

# # Font for bar charts
# SMALL_TICK_FONT_SIZE = 18
# SMALL_AXIS_FONT_SIZE = 18
# SMALL_LEGEND_FONT_SIZE = 17

# width = 0.16 # the width of the bars

# FONT_DICT = {'family': 'serif', 'serif': 'Times New Roman'}

flatui = ["#0072B2", "#D55E00", "#009E73", "#3498db", "#CC79A7", "#F0E442", "#56B4E9"]

# color_pallete = ['#0071b2', '#009e74', '#cc79a7', '#d54300', '#897456']

# color_orca = '#e69d00'

# DEFAULT_RC = {'lines.linewidth': DEFAULT_LINE_WIDTH,
#               'axes.labelsize': AXIS_FONT_SIZE,
#               'xtick.labelsize': TICK_FONT_SIZE,
#               'ytick.labelsize': TICK_FONT_SIZE,
#               'legend.fontsize': LEGEND_FONT_SIZE,
#               'text.usetex': TEX_ENABLED,
#               # 'ps.useafm': True,
#               # 'ps.use14corefonts': True,
#               # 'font.family': 'sans-serif',
#               # 'font.serif': ['Helvetica'],  # use latex default serif font
#               }

# SMALL_FONT_RC = {'lines.linewidth': DEFAULT_LINE_WIDTH,
#               'axes.labelsize': SMALL_AXIS_FONT_SIZE,
#               'xtick.labelsize': SMALL_TICK_FONT_SIZE,
#               'ytick.labelsize': SMALL_TICK_FONT_SIZE,
#               'legend.fontsize': SMALL_LEGEND_FONT_SIZE,
#               'text.usetex': TEX_ENABLED,
#               # 'ps.useafm': True,
#               # 'ps.use14corefonts': True,
#               # 'font.family': 'sans-serif',
#               # 'font.serif': ['Helvetica'],  # use latex default serif font
#               }

# sns.set_context(context='paper', rc=DEFAULT_RC)
# sns.set_style(style='ticks')
# plt.rc('font', **FONT_DICT)
# plt.rc('ps', **{'fonttype': 42})
# plt.rc('pdf', **{'fonttype': 42})
# plt.rc('mathtext', **{'fontset': 'cm'})
# plt.rc('ps', **{'fonttype': 42})
# plt.rc('legend', handlelength=1., handletextpad=0.1)

#num_machines = 400
#NUM_SCHEDS = 8

num_machines = 100
NUM_SCHEDS = 10

#loads = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6,0.7, 0.8, 0.85, 0.9, 0.92, 0.94, 0.96, 0.98, 0.99]
loads = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99]
#loads = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6,0.7, 0.8, 0.9, 0.95, 0.99]
ticks = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.96, 0.98, 0.99]

result_dir = "./results_layered_1/"
#result_dir = "./results_10/"
#policies = ['sparrow_k2', 'racksched_k2', 'jiq_k2']
# markers = ['s', '^', 'o', '*']
policies = ['sparrow_k2', 'racksched_k2', 'jiq_k2', 'adaptive_k2']

#policies = ['sparrow_k2', 'jiq_k2', 'adaptive_k2']
markers = ['^', 'o', '*', 's', 'p']

adaptive_decision_type = ['IQ', 'SQ', 'Random']
def write_to_file(policy, load, distribution, num_dispatchers = 1, queue_lengths=None, num_msgs=None, wait_times=None):
    if queue_lengths:
        metric = 'queue_lengths'
        results = queue_lengths
    elif num_msgs:
        metric = 'num_msgs'
        results = num_msgs
    elif wait_times:
        metric = 'wait_times'
        results = wait_times
    filename =  policy + '_' + distribution + '_' + 'n' + str(num_machines) + '_m' + str(num_dispatchers) + '_' + metric +  '_' + str(load) + '.csv'
    
    with open(result_dir + filename, 'a') as output_file:
        for wait_time in wait_times:
            output_file.write(str(wait_time) + ', ')
        # fieldnames = [key_label, value_label]
        # writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        # writer.writeheader()
        # for key in results:
        #      writer.writerow({
        #         key_label: key,
        #         value_label: results[key]
        #         })

def print_result(result, task_distribution, load):
    print ("\nMax wait: " + str(np.max(result)))
    print ("Avg wait: " + str(np.mean(result)))
    #print("Ideal load:" + str((np.sum(distribution)/ num_machines)))
    print ("50 Percentile: " + str(np.percentile(result, 50)))
    print ("75 Percentile: " + str(np.percentile(result, 75)))
    print ("90 Percentile: " + str(np.percentile(result, 90)))
    print ("99 Percentile: " + str(np.percentile(result, 99)))

def plot_wait_times(distribution, percentile=0.0):
    x_axis = loads
    
    metric = 'wait_times'

    fig, ax = plt.subplots()
    for i, policy in enumerate(policies):
        y_axis = []
        if policy == 'random':
            num_dispatchers = 1
        else:
            num_dispatchers = NUM_SCHEDS
        for load in loads:
            filename = policy + '_' + distribution + '_' + 'n' + str(num_machines) + '_m' + str(num_dispatchers) + '_' + metric +  '_' + str(load) + '.csv'
            wait_times = np.genfromtxt(result_dir + filename, delimiter=',')
            #wait_times = pd.read_csv(result_dir + filename, delimiter=",").values
            if percentile == 0:
                y_axis.append(np.mean(wait_times))
            else:
                y_axis.append(np.percentile(wait_times, percentile))
    
        plt.plot(x_axis, y_axis, '--', linewidth=3, markersize=6, marker=markers[i], label=policy)
    
    ax.set_xlabel('System Load')
    ax.set_ylabel('Task Wait Time (us)')
    
    plt.legend(loc='best')
    plt.grid(True)
    #ax.set_xticks(ticks)
    if percentile == 0:
        output_name = distribution + '_wait_times_avg.png' 
        plt.title('Wait times Avg.')
    else:
        output_name = distribution + '_wait_times_' + str(percentile) + '.png'
        plt.title('Wait times ' + str(percentile) + 'th percentile')
    plt.tight_layout()
    plt.savefig(result_dir + output_name, ext='png', bbox_inches="tight")
    #plt.show(fig)

def plot_queue_lens(distribution, percentile=0.0):
    x_axis = loads
    
    metric = 'queue_lens'

    fig, ax = plt.subplots()
    for i, policy in enumerate(policies):
        y_axis = []
        if policy == 'random':
            num_dispatchers = 1
        else:
            num_dispatchers = NUM_SCHEDS
        for load in loads:
            filename = policy + '_' + distribution + '_' + 'n' + str(num_machines) + '_m' + str(num_dispatchers) + '_' + metric +  '_' + str(load) + '.csv'
            wait_times = np.genfromtxt(result_dir + filename, delimiter=',')
            if percentile == 0:
                y_axis.append(np.mean(wait_times))
            else:
                y_axis.append(np.percentile(wait_times, percentile))
    
        plt.plot(x_axis, y_axis, '--', linewidth=3, markersize=6, marker=markers[i], label=policy)
    
    ax.set_xlabel('System Load')
    ax.set_ylabel('Queue Length of Assigned Worker')
    
    plt.legend(loc='best')
    plt.grid(True)
    #ax.set_xticks(ticks)
    if percentile == 0:
        output_name = distribution + '_queue_lens_avg.eps' 
        plt.title('Queue Length Avg.')
    else:
        output_name = distribution + '_queue_lens_' + str(percentile) + '.eps'
        plt.title('Queue Length ' + str(percentile) + 'th percentile')
    plt.tight_layout()
    plt.savefig(result_dir + output_name, ext='eps', bbox_inches="tight")
    #plt.show(fig)

def plot_msg_rate(distribution):
    x_axis = loads
    
    metric = 'msg_per_sec'

    fig, ax = plt.subplots()
    for i, policy in enumerate(policies):
        y_axis = []
        if policy == 'random':
            continue
        else:
            num_dispatchers = NUM_SCHEDS
        for load in loads:
            filename = policy + '_' + distribution + '_' + 'n' + str(num_machines) + '_m' + str(num_dispatchers) + '_' + metric +  '_' + str(load) + '.csv'
            wait_times = np.genfromtxt(result_dir + filename, delimiter=',')
            
            y_axis.append(wait_times)
            
        #print np.mean(y_axis)
        plt.plot(x_axis, y_axis, '--', linewidth=3, markersize=6, marker=markers[i], label=policy)
    
    ax.set_xlabel('System Load')
    ax.set_ylabel('Message rate (#msg/s)')
    #ax.set_yscale('log')
    #ax.set_xticks(x_axis)
    plt.legend(loc='best')
    plt.grid(True)
    
    output_name = distribution + '_msg_per_sec.eps' 
    plt.title('Msg Rate')
    plt.tight_layout()
    plt.savefig(result_dir + output_name, ext='eps', bbox_inches="tight")
    #plt.show(fig)

def plot_idle_count(distribution, percentile=0.0, fixed_load=0.5):
    x_axis = loads
    
    metric = 'idle_count'

    #fig, ax = plt.subplots()
    for i, policy in enumerate(policies):
        y_axis = []
        if policy == 'random':
            num_dispatchers = 1
        else:
            num_dispatchers = NUM_SCHEDS
    
        for load in loads:
            filename = policy + '_' + distribution + '_' + 'n' + str(num_machines) + '_m' + str(num_dispatchers) + '_' + metric +  '_' + str(load) + '.csv'
            idle_count = np.genfromtxt(result_dir + filename, delimiter=',')
            if percentile == 0:
                y_axis.append(np.mean(idle_count))
            else:
                y_axis.append(np.percentile(idle_count, percentile))
            print (idle_count)
        plt.plot(x_axis, y_axis, '--', linewidth=3, markersize=6, marker=markers[i], label=policy)

    ax.set_xlabel('System Load')
    ax.set_ylabel('#Idle Workers')
    #ax.set_xticks(x_axis)
    plt.legend(loc='best')
    plt.grid(True)
    
    if percentile == 0:
        output_name = distribution + '_idle_count_avg.eps' 
        plt.title('Idle workers Avg.')
    else:
        output_name = distribution + '_idle_count_' + str(percentile) + '.eps'
        plt.title('Idle Workers ' + str(percentile) + 'th percentile')
    plt.tight_layout()
    plt.savefig(result_dir + output_name, ext='eps', bbox_inches="tight")
    #plt.show(fig)

def plot_queue_len_wait(distribution, load=0.5):
    x_axis = loads
    
    queue_metric = 'queue_lens'
    wait_metric = 'wait_times'
    type_metric = 'decision_type'
    x_ticks = []
    fig, ax = plt.subplots(figsize=(20 , 11))
    
    for i, policy in enumerate(policies):
        
        if policy == 'random':
            num_dispatchers = 1
        else:
            num_dispatchers = NUM_SCHEDS
        
        filename_queue = policy + '_' + distribution + '_' + 'n' + str(num_machines) + '_m' + str(num_dispatchers) + '_' + queue_metric +  '_' + str(load) + '.csv'
        filename_wait = policy + '_' + distribution + '_' + 'n' + str(num_machines) + '_m' + str(num_dispatchers) + '_' + wait_metric +  '_' + str(load) + '.csv'
        filename_decision_type = policy + '_' + distribution + '_' + 'n' + str(num_machines) + '_m' + str(num_dispatchers) + '_' + type_metric +  '_' + str(load) + '.csv'
        queue_lens = np.genfromtxt(result_dir + filename_queue, delimiter=',')
        wait_times = np.genfromtxt(result_dir + filename_wait, delimiter=',')
        

        x_ticks += list(queue_lens)
        
        if policy == 'adaptive_k2':
            offset = 0.05
            decision_type = np.genfromtxt(result_dir + filename_decision_type, delimiter=',')
            for type_id, dec_type in enumerate(adaptive_decision_type):
                    plt.scatter(queue_lens[decision_type==type_id] + offset, wait_times[decision_type==type_id], marker=markers[i + type_id], color=flatui[i], label=policy + ': ' + dec_type, alpha=0.3)
                    offset += 0.15
        else:
            offset = -0.2 * i
            plt.scatter(queue_lens + offset, wait_times, marker=markers[i], color=flatui[i], label=policy, alpha=0.3)
    
    x_ticks = set(x_ticks)
    x_ticks = list(x_ticks)
    ax.set_xlabel('Queue Length')
    ax.set_ylabel('Wait time')
    
    plt.legend(loc='best')
    #plt.grid(True)
    ax.set_xticks(x_ticks)
    
    output_name = distribution + '_queue_len_wait_' + str(load) +'.png' 
    plt.title('Wait time vs. queue length. Tasks: ' + distribution + ' @load: ' + str(load))
    plt.tight_layout()
    plt.savefig(result_dir + output_name, ext='png', bbox_inches="tight")
    #plt.show(fig)

def plot_queue_len_idle(distribution, load=0.5):
    x_axis = loads
    
    queue_metric = 'queue_lens'
    wait_metric = 'idle_count'
    x_ticks = []
    fig, ax = plt.subplots(figsize=(12, 7))
    for i, policy in enumerate(policies):
        y_axis = []
        if policy == 'random':
            num_dispatchers = 1
        else:
            num_dispatchers = NUM_SCHEDS
        
        filename_queue = policy + '_' + distribution + '_' + 'n' + str(num_machines) + '_m' + str(num_dispatchers) + '_' + queue_metric +  '_' + str(load) + '.csv'
        filename_wait = policy + '_' + distribution + '_' + 'n' + str(num_machines) + '_m' + str(num_dispatchers) + '_' + wait_metric +  '_' + str(load) + '.csv'
        queue_lens = np.genfromtxt(result_dir + filename_queue, delimiter=',')
        idle_count = np.genfromtxt(result_dir + filename_wait, delimiter=',')
        
        x_ticks += list(queue_lens)
        
        queue_lens += (0.19 * (-1)**i) * (i!=0) # Offset for visualization
        
        #samples = random.sample(range(len(queue_lens)), 2000)
        #queue_lens = [queue_lens[i] for i in samples]
        #wait_times = [wait_times[i] for i in samples]

        plt.scatter(queue_lens, idle_count, marker=markers[i], label=policy, alpha=0.5)
        
    x_ticks = set(x_ticks)
    x_ticks = list(x_ticks)
    ax.set_xlabel('Queue Length')
    ax.set_ylabel('#Idle workers')
    
    plt.legend(loc='best')
    #plt.grid(True)
    ax.set_xticks(x_ticks)
    
    output_name = distribution + '_queue_len_idle_' + str(load) +'.png' 
    plt.title('Idle workers vs. queue length. Tasks: ' + distribution + ' @load: ' + str(load))
    plt.tight_layout()
    plt.savefig(result_dir + output_name, ext='png', bbox_inches="tight")
    #plt.show(fig)

#plot_msg_rate(distribution="bimodal")

#plot_queue_len_idle(distribution="bimodal", load=0.7)
#plot_queue_len_idle(distribution="bimodal", load=0.7)
# plot_queue_len_idle(distribution="bimodal", load=0.5)
#plot_queue_len_idle(distribution="bimodal", load=0.2)
# plot_queue_len_idle(distribution="trimodal", load=0.95)
#plot_queue_len_idle(distribution="bimodal", load=0.7)
# plot_queue_len_idle(distribution="trimodal", load=0.5)
# plot_queue_len_idle(distribution="trimodal", load=0.2)

#plot_queue_len_wait(distribution="bimodal", load=0.7)
#plot_queue_len_wait(distribution="bimodal", load=0.95)
#plot_queue_len_wait(distribution="bimodal", load=0.97)
#plot_queue_len_wait(distribution="bimodal", load=0.2)
# plot_queue_len_wait(distribution="bimodal", load=0.9)
# plot_queue_len_wait(distribution="bimodal", load=0.5)
# plot_queue_len_wait(distribution="trimodal", load=0.5)
#plot_queue_len_wait(distribution="bimodal", load=0.9)
#plot_queue_len_wait(distribution="trimodal", load=0.7)
# plot_queue_len_wait(distribution="bimodal", load=0.95)
# plot_queue_len_wait(distribution="trimodal", load=0.95)

plot_wait_times(distribution="bimodal", percentile=99)
plot_wait_times(distribution="bimodal", percentile=0)
plot_wait_times(distribution="bimodal", percentile=50)
# plot_wait_times(distribution="bimodal", percentile=0)
# plot_wait_times(distribution="bimodal", percentile=50)

#plot_wait_times(distribution="trimodal", percentile=100)
# plot_wait_times(distribution="trimodal", percentile=75)
# plot_wait_times(distribution="trimodal", percentile=0)
# plot_wait_times(distribution="trimodal", percentile=50)
