import numpy.random as nr
import numpy as np
import math
import random 
import matplotlib.pyplot as plt
import pandas as pd
from utils import *

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

#num_hosts = 400
#NUM_SCHEDS = 8

plot_subdir = "./plots/"

#policies = ['sparrow_k2', 'racksched_k2', 'jiq_k2']
# markers = ['s', '^', 'o', '*']
#policies = ['sparrow_k2', 'racksched_k2', 'jiq_k2', 'adaptive_k2']

policies = ['sparrow_k2', 'jiq_k2', 'adaptive_k2']
#policies = ['adaptive_k2']
markers = ['^', 'o', '*', 's', 'p']

adaptive_decision_type = ['IQ', 'SQ', 'Random']

def get_clusters_with_size(size_range):
    data = read_dataset()
    tenants = data['tenants']
    num_total_workers = data['tenants']['worker_count']
    tenants_maps = tenants['maps']
    cluster_id_list = []
    for t in range(len(tenants_maps)):
        cluster_id = tenants_maps[t]['app_id']
        # if int(cluster_id) == 0:
        #     continue
        if tenants_maps[t]['worker_count'] in size_range:
            cluster_id_list.append(cluster_id)
    return cluster_id_list


def plot_wait_times(distribution, cluster_size_range, percentile=0.0):
    x_axis = loads
    
    metric = 'wait_times'

    cluster_id_list = get_clusters_with_size(cluster_size_range)

    print("Plotting wait times for %d clusters with size in range [%d, %d]" %(len(cluster_id_list), cluster_size_range[0], cluster_size_range[-1]))
    print (cluster_id_list)
    
    fig, ax = plt.subplots()

    for i, policy in enumerate(policies):
        y_axis = []

        for load in loads:
            wait_times = None
            for cluster_id in cluster_id_list:
                filename = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_t' + str(num_tenants) + '_' + metric +  '_' + str(load) + '_c'+ str(cluster_id)  +'.csv'
                cluster_result = np.genfromtxt(result_dir + filename, delimiter=',')
                if wait_times is None:
                    wait_times = cluster_result
                else:
                    wait_times = np.concatenate((wait_times, cluster_result)) 

                
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
        output_name = 'cs_' + str(cluster_size_range[0]) + '_' + str(cluster_size_range[-1]) + '_' + distribution + '_wait_times_avg.png' 
        plt.title('Wait times Avg.')
    else:
        output_name = 'cs_' + str(cluster_size_range[0]) + '_' + str(cluster_size_range[-1]) + '_' + distribution + '_wait_times_' + str(percentile) + '.png'
        plt.title('Wait times ' + str(percentile) + 'th percentile')
    plt.tight_layout()
    plt.savefig(result_dir + plot_subdir + output_name, ext='png', bbox_inches="tight")
    #plt.show(fig)

def plot_transfer_times(distribution, percentile=0.0):
    x_axis = loads
    
    metric = 'transfer_times'

    fig, ax = plt.subplots()
    for i, policy in enumerate(policies):
        y_axis = []
        if policy == 'random':
            num_dispatchers = 1
        else:
            num_dispatchers = NUM_SCHEDS
        for load in loads:
            filename = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_m' + str(num_dispatchers) + '_' + metric +  '_' + str(load) + '.csv'
            wait_times = np.genfromtxt(result_dir + filename, delimiter=',')
            #wait_times = pd.read_csv(result_dir + filename, delimiter=",").values
            if percentile == 0:
                y_axis.append(np.mean(wait_times))
            else:
                y_axis.append(np.percentile(wait_times, percentile))
    
        plt.plot(x_axis, y_axis, '--', linewidth=3, markersize=6, marker=markers[i], label=policy)
    
    ax.set_xlabel('System Load')
    ax.set_ylabel('Task Transfer Time (us)')
    
    plt.legend(loc='best')
    plt.grid(True)
    #ax.set_xticks(ticks)
    if percentile == 0:
        output_name = distribution + '_transfer_times_avg.png' 
        plt.title('Wait times Avg.')
    else:
        output_name = distribution + '_transfer_times_' + str(percentile) + '.png'
        plt.title('Transfer times ' + str(percentile) + 'th percentile')
    plt.tight_layout()
    plt.savefig(result_dir + plot_subdir + output_name, ext='png', bbox_inches="tight")
    #plt.show(fig)

def plot_overhead(metric, distribution, percentile=0.0):
    x_axis = loads
    
    fig, ax = plt.subplots()
    for i, policy in enumerate(policies):
        y_axis = []
        if policy == 'random':
            num_dispatchers = 1
        else:
            num_dispatchers = NUM_SCHEDS
        for load in loads:
            filename_wait_time = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_t' + str(num_tenants) + '_wait_times_' + str(load) + '.csv'
            filename_transfer_time = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_t' + str(num_tenants) + '_transfer_times_' + str(load) + '.csv'
            
            if metric == 'transfer_times':
                overhead = np.genfromtxt(result_dir + filename_transfer_time, delimiter=',')
            elif metric == 'wait_times':
                overhead = np.genfromtxt(result_dir + filename_wait_time, delimiter=',')
            elif metric == 'total_overhead':
                transfer_times = np.genfromtxt(result_dir + filename_transfer_time, delimiter=',')
                wait_times = np.genfromtxt(result_dir + filename_wait_time, delimiter=',')
                overhead = np.add(wait_times, transfer_times)
            #wait_times = pd.read_csv(result_dir + filename, delimiter=",").values
            if percentile == 0:
                y_axis.append(np.mean(overhead))
            else:
                y_axis.append(np.percentile(overhead, percentile))
    
        plt.plot(x_axis, y_axis, '--', linewidth=3, markersize=6, marker=markers[i], label=policy)
    
    ax.set_xlabel('System Load')
    
    ax.set_ylabel(metric + ' (us)')
    output_tag = metric
    
    plt.legend(loc='best')
    plt.grid(True)
    #ax.set_xticks(ticks)

    if percentile == 0:
        output_name = distribution + '_' + metric + '_avg.png' 
        plt.title('Wait times Avg.')
    else:
        output_name = distribution + '_' + metric + '_' + str(percentile) + '.png'
        plt.title(metric + ' ' + str(percentile) + 'th percentile')
    plt.tight_layout()
    plt.savefig(result_dir + plot_subdir + output_name, ext='png', bbox_inches="tight")
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
            filename = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_m' + str(num_dispatchers) + '_' + metric +  '_' + str(load) + '.csv'
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
    plt.savefig(result_dir + plot_subdir + output_name, ext='eps', bbox_inches="tight")
    #plt.show(fig)

def plot_msg_rate(distribution, percentile=0.0, layer='spine', logarithmic=True):
    x_axis = loads
    
    metric_spine = 'msg_per_sec_spine'
    metric_tor = 'msg_per_sec_tor'
    fig, ax = plt.subplots()
    for i, policy in enumerate(policies):
        y_axis = []

        for load in loads:
            filename_spine = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_t' + str(num_tenants) + '_' + metric_spine +  '_' + str(load) + '.csv'
            filename_tor = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_t' + str(num_tenants) + '_' + metric_tor +  '_' + str(load) + '.csv'

            if layer == 'spine':
                msg_per_sec_spine = np.genfromtxt(result_dir + filename_spine, delimiter=',')
                if percentile == 0:
                    y_axis.append(np.mean(msg_per_sec_spine))
                else:
                    y_axis.append(np.percentile(msg_per_sec_spine, percentile))
            elif layer== 'tor':
                msg_per_sec_tor = np.genfromtxt(result_dir + filename_tor, delimiter=',')
                if percentile == 0:
                    y_axis.append(np.mean(msg_per_sec_tor))
                else:
                    y_axis.append(np.percentile(msg_per_sec_tor, percentile))
            
        #print np.mean(y_axis)
        plt.plot(x_axis, y_axis, '--', linewidth=3, markersize=6, marker=markers[i], label=policy)
    
    ax.set_xlabel('System Load')
    ax.set_ylabel('Message rate (#msg/s)')
    if logarithmic:
        ax.set_yscale('log')
    #ax.set_xticks(x_axis)
    plt.legend(loc='best')
    plt.grid(True)
    
    if percentile == 0:
        stat_tag = 'avg'
    else:
        stat_tag = str(percentile)

    output_name = distribution + '_' + layer + '_msg_per_sec_' + stat_tag + '.png' 
    
    plt.title('Msg Rate ' + stat_tag)
    plt.tight_layout()
    plt.savefig(result_dir + plot_subdir + output_name, ext='png', bbox_inches="tight")
    #plt.show(fig)

def plot_switch_state(distribution, percentile=0.0, max_states=True, multi_layer=True, layer=None, logarithmic=False):
    x_axis = loads
    
    if max_states:
        metric_spine = 'switch_state_spine_max'
        metric_tor = 'switch_state_tor_max' 
    else:
        metric_spine = 'switch_state_spine_mean'
        metric_tor = 'switch_state_tor_mean' 

    fig, ax = plt.subplots()
    for i, policy in enumerate(policies):
        
        y_axis = []
        
        for load in loads:
            filename_spine = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_t' + str(num_tenants) + '_' + metric_spine +  '_' + str(load) + '.csv'
            filename_tor = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_t' + str(num_tenants) + '_' + metric_tor +  '_' + str(load) + '.csv'
            
            state_spine = np.genfromtxt(result_dir + filename_spine, delimiter=',')
            state_tor = np.genfromtxt(result_dir + filename_tor, delimiter=',')
            if multi_layer:
                y_axis.append(np.mean(state_spine) + np.mean(state_tor)) # Sum of spine layer and tor layer states
            else:
                if layer == 'spine':
                    if percentile == 0:
                        y_axis.append(np.mean(state_spine))
                    else:
                        y_axis.append(np.percentile(state_spine, percentile))
                elif layer == 'tor':
                    if percentile == 0:
                        y_axis.append(np.mean(state_tor))
                    else:
                        y_axis.append(np.percentile(state_tor, percentile))
            
        #print np.mean(y_axis)
        plt.plot(x_axis, y_axis, '--', linewidth=3, markersize=6, marker=markers[i], label=policy)
    
    ax.set_xlabel('Load')
    ax.set_ylabel('#States per switch')
    if logarithmic:
        ax.set_yscale('log')
    #ax.set_xticks(x_axis)
    plt.legend(loc='best')
    plt.grid(True)
    if percentile == 0:
        stat_tag = 'avg'
    else:
        stat_tag = str(percentile)


    if layer == 'spine':
        output_name = distribution + '_' + metric_spine + '_' + stat_tag + '.png' 
    else:
        output_name = distribution + '_' + metric_tor + '_' + stat_tag + '.png' 
    

    plt.title(stat_tag + ' #States per active switch at layer:' + layer)
    plt.tight_layout()
    plt.savefig(result_dir + plot_subdir + output_name, ext='png', bbox_inches="tight")

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
            filename = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_m' + str(num_dispatchers) + '_' + metric +  '_' + str(load) + '.csv'
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
    plt.savefig(result_dir + plot_subdir + output_name, ext='eps', bbox_inches="tight")
    #plt.show(fig)

def plot_queue_len_wait(distribution, cluster_size_range, load=0.5):
    x_axis = loads
    cluster_id_list = get_clusters_with_size(cluster_size_range)

    print("Plotting queue_len_wait for %d clusters with size in range [%d, %d]" %(len(cluster_id_list), cluster_size_range[0], cluster_size_range[-1]))
    print (cluster_id_list)

    queue_metric = 'queue_lens'
    wait_metric = 'wait_times'
    type_metric = 'decision_type'
    x_ticks = []
    fig, ax = plt.subplots(figsize=(20 , 11))
    
    for cluster_id in cluster_id_list:
        for i, policy in enumerate(policies):
            filename_queue = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_t' + str(num_tenants) + '_' + queue_metric +  '_' + str(load) + '_c'+ str(cluster_id)  +'.csv'
            filename_wait = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_t' + str(num_tenants) + '_' + wait_metric +  '_' + str(load) + '_c'+ str(cluster_id)  +'.csv'
            filename_decision_type = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_t' + str(num_tenants) + '_' + type_metric +  '_' + str(load) + '_c'+ str(cluster_id)  +'.csv'
            queue_lens = np.genfromtxt(result_dir + filename_queue, delimiter=',')
            wait_times = np.genfromtxt(result_dir + filename_wait, delimiter=',')
        

            x_ticks += list([int(x) for x in queue_lens])
        
            if policy == 'adaptive_k2':
                offset = 0.00
                decision_type = np.genfromtxt(result_dir + filename_decision_type, delimiter=',')
                for type_id, dec_type in enumerate(adaptive_decision_type):
                        plt.scatter(queue_lens[decision_type==type_id] + offset, wait_times[decision_type==type_id], marker=markers[i + type_id], color=flatui[i+ type_id], label=policy + ': ' + dec_type, alpha=0.3)
                        #offset += 0.15
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
        
        output_name = distribution + '_queue_len_wait_' + str(load) + '_c'+ str(cluster_id) + '.png' 
        plt.title('Wait time vs. queue length. Tasks: ' + distribution + ' @load: ' + str(load))
        plt.tight_layout()
        plt.savefig(result_dir + plot_subdir + output_name, ext='png', bbox_inches="tight")
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
        
        filename_queue = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_m' + str(num_dispatchers) + '_' + queue_metric +  '_' + str(load) + '.csv'
        filename_wait = policy + '_' + distribution + '_' + 'n' + str(num_hosts) + '_m' + str(num_dispatchers) + '_' + wait_metric +  '_' + str(load) + '.csv'
        queue_lens = np.genfromtxt(result_dir + filename_queue, delimiter=',')
        idle_count = np.genfromtxt(result_dir + filename_wait, delimiter=',')
        
        x_ticks += list([int(x) for x in queue_lens])
        
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
    plt.savefig(result_dir + plot_subdir + output_name, ext='png', bbox_inches="tight")
    #plt.show(fig)


# plot_msg_rate(distribution="bimodal", percentile=99, layer='spine', logarithmic=True)
# plot_msg_rate(distribution="bimodal", percentile=99, layer='tor', logarithmic=True)
# plot_msg_rate(distribution="bimodal", percentile=50, layer='spine', logarithmic=True)
# plot_msg_rate(distribution="bimodal", percentile=50, layer='tor', logarithmic=True)
# plot_msg_rate(distribution="bimodal", percentile=0, layer='tor', logarithmic=True)
# plot_msg_rate(distribution="bimodal", percentile=0, layer='spine', logarithmic=True)

# plot_switch_state(distribution="bimodal", percentile=99.99, multi_layer=False, layer='spine', logarithmic=False)
# plot_switch_state(distribution="bimodal", percentile=99.99, multi_layer=False, layer='tor', logarithmic=False)

# plot_switch_state(distribution="bimodal", percentile=50, multi_layer=False, layer='spine', logarithmic=False)
# plot_switch_state(distribution="bimodal", percentile=50, multi_layer=False, layer='tor', logarithmic=False)

# plot_switch_state(distribution="bimodal", max_states=False, percentile=99.99, multi_layer=False, layer='spine', logarithmic=False)
# plot_switch_state(distribution="bimodal", max_states=False, percentile=99.99, multi_layer=False, layer='tor', logarithmic=False)

#plot_queue_len_idle(distribution="bimodal", load=0.7)
#plot_queue_len_idle(distribution="bimodal", load=0.7)
# plot_queue_len_idle(distribution="bimodal", load=0.5)
#plot_queue_len_idle(distribution="bimodal", load=0.2)
# plot_queue_len_idle(distribution="trimodal", load=0.95)
#plot_queue_len_idle(distribution="bimodal", load=0.7)
# plot_queue_len_idle(distribution="trimodal", load=0.5)
# plot_queue_len_idle(distribution="trimodal", load=0.2)
#plot_queue_len_wait(distribution="bimodal", load=0.99, cluster_size_range=range(1800, 1801))
#plot_queue_len_wait(distribution="bimodal", load=0.99, cluster_size_range=range(50, 51))
#plot_queue_len_wait(distribution="bimodal", load=0.96)
#plot_queue_len_wait(distribution="bimodal", load=0.97)
#plot_queue_len_wait(distribution="bimodal", load=0.2)
# plot_queue_len_wait(distribution="bimodal", load=0.9)
# plot_queue_len_wait(distribution="bimodal", load=0.5)
# plot_queue_len_wait(distribution="trimodal", load=0.5)
#plot_queue_len_wait(distribution="bimodal", load=0.9)
#plot_queue_len_wait(distribution="trimodal", load=0.7)
# plot_queue_len_wait(distribution="bimodal", load=0.95)
# plot_queue_len_wait(distribution="trimodal", load=0.95)

#plot_transfer_times(distribution="bimodal", percentile=0)

# plot_overhead(metric='wait_times', distribution="bimodal", percentile=99)
# plot_overhead(metric='total_overhead', distribution="bimodal", percentile=99)

# plot_overhead(metric='wait_times', distribution="bimodal", percentile=75)
# plot_overhead(metric='total_overhead', distribution="bimodal", percentile=75)

# plot_overhead(metric='wait_times', distribution="bimodal", percentile=0)
# plot_overhead(metric='total_overhead', distribution="bimodal", percentile=0)

#plot_overhead(metric='wait_times', distribution="bimodal", percentile=50)
# plot_overhead(metric='transfer_times', distribution="bimodal", percentile=75)
# plot_overhead(metric='transfer_times', distribution="bimodal", percentile=99)

plot_wait_times(distribution="bimodal", percentile=99, cluster_size_range=range(50, 51))
# plot_wait_times(distribution="bimodal", percentile=99, cluster_size_range=range(100, 200))
# plot_wait_times(distribution="bimodal", percentile=99, cluster_size_range=range(200, 300))
# plot_wait_times(distribution="bimodal", percentile=99, cluster_size_range=range(300, 400))
# plot_wait_times(distribution="bimodal", percentile=99, cluster_size_range=range(400, 500))
# plot_wait_times(distribution="bimodal", percentile=99, cluster_size_range=range(500, 1000))
# plot_wait_times(distribution="bimodal", percentile=99, cluster_size_range=range(1000, 2000))

#plot_wait_times(distribution="bimodal", percentile=99, cluster_size_range=range(80, 81))
# plot_wait_times(distribution="bimodal", percentile=0)
# plot_wait_times(distribution="bimodal", percentile=50)
#plot_wait_times(distribution="bimodal", percentile=75)
# plot_wait_times(distribution="bimodal", percentile=50)

#plot_wait_times(distribution="trimodal", percentile=100)
# plot_wait_times(distribution="trimodal", percentile=75)
# plot_wait_times(distribution="trimodal", percentile=0)
# plot_wait_times(distribution="trimodal", percentile=50)
