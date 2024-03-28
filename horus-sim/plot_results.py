"""Usage:
plot_results.py -d <working_dir> -t <task_distribution> [-k <k_value>] [-l <ratio>] [--load <load>] [-p policy] [--tag <tag>] [--colocate] [--analyze] [--all] [--dissect] [--dimpact] [--latency] [--loss]

plot_results.py -h | --help
plot_results.py -v | --version

Arguments:
  -d <working_dir> Directory to save dataset "system_summary.log"
  -k <k_value> 
  -l <ratio>
  -t <task_distribution>
  --load <load>
  --tag <tag>
  -p policy
Options:
  -h --help  Displays this message
  -v --version  Displays script version
"""

import numpy.random as nr
import numpy as np
import math
import random 
import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import docopt
import seaborn as sns
from utils import *
import operator
from scipy.stats import kurtosis, skew
import matplotlib.text as mtext
import matplotlib.ticker
import warnings
from matplotlib.lines import Line2D
import matplotlib.ticker as ticker


class OOMFormatter(matplotlib.ticker.ScalarFormatter):
    def __init__(self, order=0, fformat="%1.1f", offset=True, mathText=True):
        self.oom = order
        self.fformat = fformat
        matplotlib.ticker.ScalarFormatter.__init__(self,useOffset=offset,useMathText=mathText)
    def _set_order_of_magnitude(self):
        self.orderOfMagnitude = self.oom
    def _set_format(self, vmin=None, vmax=None):
        self.format = self.fformat
        if self._useMathText:
            self.format = r'$\mathdefault{%s}$' % self.format

#import seaborn as sns
# Line Styles
DEFAULT_LINE_WIDTH = 8
ALTERNATIVE_LINE_WIDTH = 6
SMALL_LINE_WIDTH = 3
LINE_STYLES = ['--', '-', '-', '-']
FONT_FAMILY = 'Times New Roman'
#FONT_FAMILY = 'Linux Libertine O'

# Font
TEX_ENABLED = False
TICK_FONT_SIZE = 24
AXIS_FONT_SIZE = 28
AXIS_SMALL_FONT_SIZE = 28
LEGEND_FONT_SIZE = 24
CAP_SIZE = LEGEND_FONT_SIZE / 2
AUTLABEL_FONT_SIZE = 20


MARKER_STYLE = dict(markersize=TICK_FONT_SIZE, mew=2.5, mfc='w')
FAILURE_DETECTION_LATENCY=5000000 # 500us

# FONT_DICT = {'family': 'serif', 'serif': 'Times New Roman'}
FONT_DICT = {'family': FONT_FAMILY}

# DEFAULT_RC = {'lines.linewidth': DEFAULT_LINE_WIDTH,
#               'axes.labelsize': AXIS_FONT_SIZE,
#               'xtick.labelsize': TICK_FONT_SIZE,
#               'ytick.labelsize': TICK_FONT_SIZE,
#               'legend.fontsize': LEGEND_FONT_SIZE,
#               'text.usetex': TEX_ENABLED,
#               # 'ps.useafm': True,
#               # 'ps.use14corefonts': True,
#               'font.family': 'sans-serif',
#               # 'font.serif': ['Helvetica'],  # use latex default serif font
#               }

scale_normal = 1.18
scale_big = scale_normal
scale_med = scale_normal
scale_small = scale_normal

DEFAULT_RC = {'lines.linewidth': int(DEFAULT_LINE_WIDTH * scale_big),
'axes.labelsize': int(AXIS_FONT_SIZE*scale_big),
'xtick.labelsize': int(TICK_FONT_SIZE*scale_med),
'ytick.labelsize': int(TICK_FONT_SIZE*scale_med),
'legend.fontsize': int(LEGEND_FONT_SIZE*scale_big),
'text.usetex': int(TEX_ENABLED*scale_big),
# 'ps.useafm': True,
# 'ps.use14corefonts': True,
'font.family': 'sans-serif',
# 'font.serif': ['Helvetica'],  # use latex default serif font
}

SCATTER_MARKER_DIAMETER = 64

# FONT_DICT = {'family': 'serif', 'serif': 'Times New Roman'}

flatui = ["#0072B2", "#D55E00", "#009E73", "#3498db", "#CC79A7", "#F0E442", "#56B4E9"]
color_pallete = ['#e69d00', '#0071b2', '#009e74', '#cc79a7', '#d54300', '#994F00', '#000000']
markers = ['^', 's', '*', 'P', 's', 'p', 'P', 'x', 'X', 'D', 'v', '1']

STYLES = {
    'Horus': {
    'color': '#d54300', 
    'marker': '^',
    'linestyle': 'dashed'},

    'RS': {
    'color': "#6666ff",
    'marker': 's',
    'linestyle': 'dashed'},

    'JSQ': {
    'color': "#000000",
    'marker': '*',
    'linestyle': 'dotted'},

    'RS-H': {
    'color': "#0071b2",
    'marker': '8',
    'linestyle': 'dashed'},

    'RS-LB': {
    'color': "#378D37",
    'marker': 'o',
    'linestyle': 'dashed'},
    
    'Pow-of-2': {
    'color': "#009e74",
    'marker': 'p',
    'linestyle': 'dashed'},

    'Pow-of-2 (DU)': {
    'color': "#0071b2",
    'marker': 'H',
    'linestyle': 'dashed'},

    'Idle Selection': {
    'color': "#cc79a7",
    'marker': 's',
    'linestyle': 'dashed'
    }
    }

sns.set_context(context='paper', rc=DEFAULT_RC)
sns.set_style(style='ticks')
plt.rc('text', usetex=TEX_ENABLED)
plt.rc('ps', **{'fonttype': 42})
plt.rc('legend', handlelength=1., handletextpad=0.1)

fig, ax = plt.subplots()

result_dir =  "./"
plot_subdir = "./plots/"
analysis_subdir = "./analysis/"

TICKS_PER_US = 1000.0

#loads = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99]
loads = [0.1, 0.3, 0.5,0.7, 0.8, 0.9, 0.95, 0.99, 1.0]

linestyle = ['-', '--', ':']


l_values = [40, 20, 10]
l_value_lables = ['40', '20', "10"]
k_values = [2, 4, 8]

run_id_list = ['0']
k = 0
adaptive_decision_type = ['IQ', 'SQ', 'Random']
algorithm_names = ['Dummy'] # Array later filled with values depending on plot 

sparrow_resp_time_p99 = [4.8199011554, 28.1513564826, 32.9413517512,  36.6835379718, 38.1484818907, 38.6212824227]

class LegendTitle(object): # Used for sub-category in legends
    def __init__(self, text_props=None):
        self.text_props = text_props or {}
        super(LegendTitle, self).__init__()

    def legend_artist(self, legend, orig_handle, fontsize, handlebox):
        x0, y0 = handlebox.xdescent, handlebox.ydescent
        title = mtext.Text(x0, y0, orig_handle,  **self.text_props)
        handlebox.add_artist(title)
        return title

def get_clusters_within_range(param_range, is_colocate=False, param='size'):
    data = read_dataset(result_dir, is_colocate)
    tenants = data['tenants']
    num_total_workers = data['tenants']['worker_count']
    tenants_maps = tenants['maps']
    cluster_id_param_map = {}
    cluster_id_tor_count_map = {}
    cluster_imbalance_map = {}
    rack_worker_variance = {}
    worker_count = []
    for t in range(len(tenants_maps)):
        host_list = tenants_maps[t]['worker_to_host_map']
        worker_count.append(len(host_list))
        cluster_id = tenants_maps[t]['app_id']
        cluster_size = tenants_maps[t]['worker_count']
        tor_list = []
        tor_count = 0
        tor_worker_count = {}
        for host_id in host_list:
            tor_id = get_tor_id_for_host(host_id)
            # Avoid counting duplicates
            if tor_id not in tor_list:
                tor_list.append(tor_id)
                tor_count += 1
                tor_worker_count.update({tor_id: 1})
            else:
                tor_worker_count.update({tor_id: tor_worker_count[tor_id] + 1})
        
        worker_per_tor_list = np.array(list(tor_worker_count.values()))
        if param == 'size':
            metric = cluster_size
        elif param == 'var':
            metric = np.var(worker_per_tor_list)
        #print(metric)
        #print(param_range[0])
        #print(param_range[-1])
        if metric > param_range[0] and metric < param_range[-1]:
            cluster_id_tor_count_map.update({cluster_id : tor_count})
            cluster_id_param_map[cluster_id] = metric
            #print("Cluster ID: " + str(tenants_maps[t]['app_id']) + " metric: " + str(metric))
            #print(worker_per_tor_list)
            #cluster_imbalance_map.update({cluster_id : np.std(worker_per_tor_list)})
            #cluster_imbalance_map.update({cluster_id : np.mean(worker_per_tor_list)})
            #cluster_imbalance_map.update({cluster_id : skew(worker_per_tor_list)})
        print(worker_per_tor_list)
    print("Mean worker per cluster:")
    print(np.mean(worker_count))
    return dict(sorted(cluster_id_param_map.items())), dict(sorted(rack_worker_variance.items()))

def get_total_workers ():
    data = read_dataset(result_dir, is_colocate=False)
    return data['tenants']['worker_count']

def plot_latency_vs_net_condition(policies, net_condition, distribution, var_list, loads=[0.9],  percentile=0.0, run_id=0, is_colocate=False, param='size'):
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)
    x_axis = np.array(var_list)

    width = np.max(x_axis) / (len(policies)*len(x_axis) + 2)       # the width of the bars
    if percentile == 0: 
        output_tag = '_mean_'
    else:
        output_tag = '_p' + str(percentile) + '_'

    for load in loads:
        y_use_sci = False
        fig, ax = plt.subplots()
        for i, policy in enumerate(policies):
            y_axis = []
            y_err = []
            yerr_low = []
            yerr_high = []
            metric_values = []
            for var in var_list:
                if net_condition == 'loss':
                    condition_tag = f'l{var}_d5'
                elif net_condition == 'latency':
                    condition_tag = f'l0.0_d{var}'
                    if policy == 'random_racksched_k2':
                        condition_tag = f'l1e-05_d{var}'
                filename_latency = str(policy) + '_' + condition_tag + '_' + distribution + output_tag + 'response_times_' + str(load) + '_r' + str(run_id) +'.csv'
                values = np.genfromtxt(result_dir + analysis_subdir + filename_latency, delimiter=',')
                values = values / TICKS_PER_US
                y_value = np.mean(values)
                y_axis.append(y_value)
                y_err.append(np.std(values))

            ax.bar(np.linspace(x_axis[0], x_axis[-1], num=len(x_axis)) + i*width, y_axis, width, yerr=y_err, label=algorithm_names[i], color=STYLES[algorithm_names[i]]['color'], error_kw=dict(lw=3 , capsize=5, capthick=1.5), align='center')

        ax.set_xticks(np.linspace(x_axis[0], x_axis[-1], num=len(x_axis)) + width/len(policies))
    
    
        if net_condition == 'loss':
            ax.set_xlabel('Loss Rate (%)', fontsize=AXIS_SMALL_FONT_SIZE)
            ax.set_xticklabels([x*100 for x in x_axis])
        elif net_condition == 'latency':
            ax.set_xlabel(f'Per-Hop Delay' + '(%ss)' % r'$\mu$', fontsize=AXIS_SMALL_FONT_SIZE)
            ax.set_xticklabels(x_axis)
        if y_use_sci:
            plt.ticklabel_format(axis="y", style="sci", scilimits=(0,0))
        ax.tick_params(axis='both', which='major', labelsize=AUTLABEL_FONT_SIZE)


        #ax.set_ylim(0, ylim)
        
        if percentile == 0:
            stat_label = 'Avg. '
        else:
            stat_label = str(percentile) + '% '

        
        text_label = 'Resp. Time'
        #ax.set_xscale("log")

        ax.set_ylabel(stat_label + text_label + ' (%ss)' % r'$\mu$')
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.set_ylim(bottom=0)
        #plt.legend(loc='upper left')
        handles, labels = ax.get_legend_handles_labels()
        
        plt.legend(handles, labels, loc='best')
        ax.yaxis.set_major_formatter(OOMFormatter(3, "%.0f"))
        ax.ticklabel_format(axis='y', style='sci', scilimits=(3,3))
        #ax.set_xticks(ticks)
        if percentile == 0:
            output_name =  distribution + '_response_times_vs_' + net_condition  + '_l' +  str(load) + '_' +'_avg_' 
            #plt.title(text_label + ' Mean')
        else:
            output_name = distribution + '_response_times_vs_' + net_condition +  '_l' +  str(load) + '_' + str(percentile) 
            #plt.title(text_label + ' ' + str(percentile) + 'th percentile')
        plt.tight_layout()
        plt.savefig(result_dir + plot_subdir + output_name + '.png', ext='png', bbox_inches="tight")
        plt.savefig(result_dir + plot_subdir + output_name + '.pdf', ext='pdf', bbox_inches='tight')

def plot_msg_rate_vs_net_condition(policies, net_condition, distribution, var_list, loads=[0.9],  percentile=0.0, run_id=0, is_colocate=False, param='size'):
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)
    x_axis = np.array(var_list)[1:]
    metric_spine = 'msg_per_sec_spine'
    #if net_condition == 'latency':
    width = x_axis[-1]/10       # the width of the bars
    #else:
    #    width = 0.1
    if percentile == 0: 
        output_tag = '_mean_'
    else:
        output_tag = '_p' + str(percentile) + '_'
    baseline = 0
    for load in loads:
        y_use_sci = False
        fig, ax = plt.subplots()
        for i, policy in enumerate(policies):
            y_axis = []
            y_err = []
            yerr_low = []
            yerr_high = []
            metric_values = []
            for var_idx, var in enumerate(var_list):

                if net_condition == 'loss':
                    condition_tag = f'l{var}_d5'
                elif net_condition == 'latency':
                    condition_tag = f'l0.0_d{var}'
                    if policy == 'random_racksched_k2':
                        condition_tag = f'l1e-05_d{var}'
                filename = str(policy) + '_' + condition_tag + '_' + distribution + '_'  + metric_spine +  '_' + str(load) + '_r' + str(run_id) +  '.csv'
                values = np.genfromtxt(result_dir + analysis_subdir + filename, delimiter=',')
                values = values[np.nonzero(values)]
                if percentile == 0:
                    y_value = np.mean(values)
                else:
                    y_value = np.percentile(values, percentile)
                if var_idx == 0:
                    baseline = y_value
                else:
                    y_axis.append(((y_value / baseline) - 1.0) * 100)
                print(filename)
                print(y_value)
                print(((y_value / baseline) - 1.0) * 100)
            ax.bar(np.linspace(x_axis[0], x_axis[-1], num=len(x_axis)), y_axis, width, label=algorithm_names[i], color=STYLES[algorithm_names[i]]['color'], error_kw=dict(lw=3 , capsize=5, capthick=1.5), align='center')

        ax.set_xticks(np.linspace(x_axis[0], x_axis[-1], num=len(x_axis)))
    
    
        if net_condition == 'loss':
            ax.set_xlabel('Loss Rate (%)', fontsize=AXIS_SMALL_FONT_SIZE)
            ax.set_xticklabels([x*100 for x in x_axis])
        elif net_condition == 'latency':
            ax.set_xlabel(f'Per-Hop Delay' + '(%ss)' % r'$\mu$', fontsize=AXIS_SMALL_FONT_SIZE)
            ax.set_xticklabels(x_axis)
        if y_use_sci:
            plt.ticklabel_format(axis="y", style="sci", scilimits=(0,0))
        ax.tick_params(axis='both', which='major', labelsize=AUTLABEL_FONT_SIZE)

        
        text_label = 'Message Rate Increase (%)'
        #ax.set_xscale("log")

        ax.set_ylabel(text_label)
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.set_ylim(bottom=0)
        #plt.legend(loc='upper left')
        handles, labels = ax.get_legend_handles_labels()
        
        plt.legend(handles, labels, loc='best')
        # ax.yaxis.set_major_formatter(OOMFormatter(3, "%.0f"))
        # ax.ticklabel_format(axis='y', style='sci', scilimits=(3,3))
        #ax.set_xticks(ticks)
        if percentile == 0:
            output_name =  distribution + '_msg_per_sec_vs_' + net_condition  + '_l' +  str(load) + '_' +'_avg_' 
            #plt.title(text_label + ' Mean')
        else:
            output_name = distribution + '_msg_per_sec_vs_' + net_condition +  '_l' +  str(load) + '_' + str(percentile) 
            #plt.title(text_label + ' ' + str(percentile) + 'th percentile')
        plt.tight_layout()
        plt.savefig(result_dir + plot_subdir + output_name + '.png', ext='png', bbox_inches="tight")
        plt.savefig(result_dir + plot_subdir + output_name + '.pdf', ext='pdf', bbox_inches='tight')

def plot_latency_vs_param_bar(policies, metric, distribution, bucket_size, max_param, percentile=0.0, run_id=0, is_colocate=False, param='size'):    
    cluster_ranges = []
    
    range_lower = 0
    range_upper = bucket_size
    while range_upper <= max_param:
        cluster_ranges.append(range(range_lower, range_upper))
        range_upper += bucket_size
        range_lower += bucket_size

    col_name_extension = ''
    cluster_id_lists = []
    x_ticks = []

    for cr in cluster_ranges:
        print(cr)
        cluster_id_list, cluster_id_variance = get_clusters_within_range(cr, is_colocate, param=param)
        cluster_id_lists.append(cluster_id_list)
        #x_ticks.append(str(math.ceil(cr[0])) + '-' + str(math.ceil(cr[-1])))
        x_ticks.append(str(int((math.ceil(cr[0]) + math.ceil(cr[-1]) + 1)/2)))
        print(cluster_id_list)
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)
    ylim = 50000
    
    width = cluster_ranges[-1][-1] / (len(policies)*len(cluster_ranges) + 2)       # the width of the bars
    
    for load in [0.9]:
        y_use_sci = False
        fig, ax = plt.subplots()
        for i, policy in enumerate(policies):
            y_axis = []
            y_err = []
            yerr_low = []
            yerr_high = []
            x_axis = []
            metric_values = []
            

            if percentile == 0: 
                output_tag = '_mean_'
            else:
                output_tag = '_p' + str(percentile) + '_'

            filename_wait_time = str(policy) + '_' + distribution + output_tag + col_name_extension + 'wait_times_' + str(load) + '_r' + str(run_id) +'.csv'    
            #filename_transfer_time = output_tag + distribution + '_' + col_name_extension + 'n' + str(num_hosts) + '_t' + str(num_tenants) + '_transfer_times_' + str(load) + '_r' + str(run_id) +'.csv'
            filename_latency = str(policy) + '_' + distribution + output_tag + col_name_extension + 'response_times_' + str(load) + '_r' + str(run_id) +'.csv'

            for range_idx, cluster_id_list in enumerate(cluster_id_lists):
                points_to_aggregate = np.array(list(cluster_id_list.keys()))

                if metric == 'transfer_times':
                    values = np.genfromtxt(result_dir + analysis_subdir + filename_transfer_time, delimiter=',')
                elif metric == 'wait_times':
                    values = np.genfromtxt(result_dir + analysis_subdir + filename_wait_time, delimiter=',')
                elif metric == 'response_times':
                    values = np.genfromtxt(result_dir + analysis_subdir + filename_latency, delimiter=',')
                values = values / TICKS_PER_US
                y_value = values[points_to_aggregate].mean()
                y_axis.append(y_value)
                
                y_err.append(np.std(values[points_to_aggregate]))
                #yerr_low.append(abs(y_value - np.percentile(values[points_to_aggregate], 25)))
                #yerr_high.append(abs(y_value - np.percentile(values[points_to_aggregate], 75)))
                #y_err.append([np.percentile(values[points_to_aggregate], 10), np.percentile(values[points_to_aggregate], 90)])
                x_axis.append(int((cluster_ranges[range_idx][0] + cluster_ranges[range_idx][-1] + 1) / 2))
                if y_axis[-1] > 1000:
                    y_use_sci = True
                # print (str(policy) + " @"+ str(load) + " Range idx: " + str(range_idx))
                # print ("Y axis: " + str(y_axis[-1]))
                # print ("Y err: " + str(y_err[-1]))

            x_axis = np.array(x_axis)
            #y_err = [yerr_low, yerr_high]
            ax.bar(x_axis + i*width, y_axis, width, yerr=y_err, label=algorithm_names[i], color=STYLES[algorithm_names[i]]['color'], error_kw=dict(lw=5, capsize=8, capthick=3))
            print ("For alg: " + algorithm_names[i])
            print (y_axis)
            for k in range(len(y_axis)):
                if y_axis[k] > ylim:
                    plt.annotate("{:.1f}".format(y_axis[k]/1000), xy=(x_axis[k] + i*width, 49900), ha='center', fontsize=AUTLABEL_FONT_SIZE, va='bottom')

        ax.set_xticks(x_axis + width)
        ax.set_xticklabels(x_ticks)
        
        
        if param == 'size':
            ax.set_xlabel('Cluster Size (Nodes)')
        elif param == 'var':
            ax.set_xlabel('Variance of #Workers per Rack', fontsize=AXIS_SMALL_FONT_SIZE*1.13)

        if y_use_sci:
            plt.ticklabel_format(axis="y", style="sci", scilimits=(0,0))
        ax.set_ylim(0, ylim)
        
        if percentile == 0:
            stat_label = 'Avg. '
        else:
            stat_label = str(percentile) + '% '

        if metric == 'transfer_times':
            text_label = 'Scheduling Time'
        elif metric == 'wait_times':
            text_label = 'Waiting Time'
        else:
            text_label = 'Resp. Time'
        
        ax.set_ylabel(stat_label + text_label + ' (%ss)' % r'$\mu$')
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.set_ylim(bottom=0)
        #plt.legend(loc='upper left')
        handles, labels = ax.get_legend_handles_labels()
        
        plt.legend(handles, labels, loc='best')
        ax.yaxis.set_major_formatter(OOMFormatter(3, "%d"))
        ax.ticklabel_format(axis='y', style='sci', scilimits=(3,3))
        #ax.set_xticks(ticks)
        if percentile == 0:
            output_name =  distribution + '_' + metric + '_l' +  str(load) + '_' +'_avg_' + param 
            #plt.title(text_label + ' Mean')
        else:
            output_name = distribution + '_' + metric +  '_l' +  str(load) + '_' + str(percentile) + '_bar_' + param
            #plt.title(text_label + ' ' + str(percentile) + 'th percentile')
        plt.tight_layout()
        plt.savefig(result_dir + plot_subdir + output_name + '.png', ext='png', bbox_inches="tight")
        plt.savefig(result_dir + plot_subdir + output_name + '.pdf', ext='pdf', bbox_inches='tight')

def plot_latency_vs_ratio(policies, k, metric, distribution, percentile, load, run_id=0):
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)
    #x_axis = [str(x) for x in l_values]
    x_axis = ['20', '10']
    policy = policies[0] # Only for Falcon
    #width = l_values[-1] / (len(l_values) + 2)       # the width of the bars

    parent_dir = result_dir # result_dir passed with -d, and we open folders 
    if percentile == 0: 
            output_tag = str(policy) + '_mean_'
    else:
        output_tag = str(policy)+ '_p' + str(percentile) + '_'
    
    if percentile == 0: 
                output_tag = '_mean_'
    else:
        output_tag = '_p' + str(percentile) + '_'

    filename_wait_time = str(policy) + '_' + distribution + output_tag  + 'wait_times_' + str(load) + '_r' + str(run_id) +'.csv'    
    #filename_transfer_time = output_tag + distribution + '_'  + 'n' + str(num_hosts) + '_t' + str(num_tenants) + '_transfer_times_' + str(load) + '_r' + str(run_id) +'.csv'
    filename_latency = str(policy) + '_' + distribution + output_tag + 'response_times_' + str(load) + '_r' + str(run_id) +'.csv'

    fig, ax = plt.subplots()
    y_axis = []
    y_err = []
    yerr_low = []
    yerr_high = []
    for l_val in l_values:
        res_dir = parent_dir + '/result_l' + str(l_val) + '_k2_' + distribution + '/'
        if metric == 'transfer_times':
            latency = np.genfromtxt(res_dir + analysis_subdir + filename_transfer_time, delimiter=',')
        elif metric == 'wait_times':
            latency = np.genfromtxt(res_dir + analysis_subdir + filename_wait_time, delimiter=',')
        elif metric == 'response_times':
            latency = np.genfromtxt(res_dir + analysis_subdir + filename_latency, delimiter=',')
        if (l_val == 40):
            base = latency
        else:
            normalized = np.divide(latency, base)
            y_value = np.mean(normalized)
            y_axis.append(y_value)
            y_err.append(np.std(np.divide(latency, base)))
    #         yerr_low.append(abs(y_value - np.percentile(normalized, 25)))
    #         yerr_high.append(abs(y_value - np.percentile(normalized, 5)))
    # y_err = [yerr_low, yerr_high]
            #y_err.append(0)

        #y_err.append(0)
    ax.bar(x_axis , y_axis, 0.4, yerr=y_err, label=algorithm_names[0], color=color_pallete[0], error_kw=dict(lw=5, capsize=10, capthick=4))
    plt.axhline(y=1, color='0.3', linestyle='--', alpha=0.5, linewidth=SMALL_LINE_WIDTH)
    
    ax.set_xlabel('Leaf to Spine Scheduler Ratio', fontsize=AXIS_SMALL_FONT_SIZE)
    
    plt.rcParams['legend.handlelength'] = 0
    plt.rcParams['legend.numpoints'] = 1
    handles, labels = ax.get_legend_handles_labels()
    # remove the errorbars
    #handles = [h[0] for h in handles]
    #plt.legend(handles, labels, loc='best')
    
    plt.grid(True)
    #ax.set_xticks(x_axis)
    if metric == 'transfer_times':
            text_label = 'Scheduling Time'
    elif metric == 'wait_times':
        text_label = 'Normalized Performance'
    else:
        text_label = 'Normalized Performance'
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1, 1.25])
    #ax.set_ylabel(text_label + ' (%ss)' % r'$\mu$')
    ax.set_ylabel(text_label, fontsize=AXIS_SMALL_FONT_SIZE)
    ax.get_yaxis().get_offset_text().set_visible(False)
    sns.despine(ax=ax, top=True, right=True, left=False, bottom=False)
    ax.set_ylim(0)
    if percentile == 0:
        output_name =  distribution + '_' + metric + '_k' + str(k) + '_vs_ratio_l' +  str(load) + '_avg_r' + str(run_id)
        #plt.title(text_label + ' Mean')
    else:
        output_name = distribution + '_' + metric +  '_k' + str(k) + '_vs_ratio_l' +  str(load) + '_p' + str(percentile) + '_r' +str(run_id) 
        #plt.title(text_label + ' ' + str(percentile) +  'th Percentile')
    plt.tight_layout()
    plt.savefig(parent_dir + plot_subdir + output_name + '.png', ext='png', bbox_inches="tight")
    plt.savefig(parent_dir + plot_subdir + output_name + '.pdf', ext='pdf', bbox_inches='tight')


def analyze_latency(policy, load, distribution, percentile_list, run_id=0, is_colocate=False, size_range=range(10, 20001)):
    cluster_id_list, _ = get_clusters_within_range(size_range, is_colocate)
    # if is_colocate:
    #     col_name_extension = 'col_'
    # else:
    col_name_extension = ''
    print("Analyzing latencys for %d clusters with size in range [%d, %d]" %(len(cluster_id_list), size_range[0], size_range[-1]))
    print("Policy: %s @ load %s" %(policy, load))
    y_axis = []
    y_err = []
    matrices_wait_time = [] * len(percentile_list)
    matrices_transfer_time = [] * len(percentile_list)
    matrices_response_time = [] * len(percentile_list)
    
    cumulative_wait_times = []
    cumulative_transfer_times = []
    cumulative_response_time = []

    for percentile in percentile_list:
        matrices_wait_time.append([])
        matrices_transfer_time.append([])
        matrices_response_time.append([])

    for cluster_id in cluster_id_list:
        filename_wait_time = policy + '_' + distribution + '_wait_times_' + str(load) +  '_c' + str(cluster_id) + '_r' + str(run_id) +'.csv'
        #filename_transfer_time = policy + '_' + distribution + '_transfer_times_' + str(load) +  '_c' + str(cluster_id) + '_r' + str(run_id) +'.csv'
        filename_response_time = policy + '_' + distribution + '_response_times_' + str(load) +  '_c' + str(cluster_id) + '_r' + str(run_id) +'.csv'

        #transfer_times = np.genfromtxt(result_dir + filename_transfer_time, delimiter=',')
        wait_times = np.genfromtxt(result_dir + filename_wait_time, delimiter=',')
        response_time = np.genfromtxt(result_dir + filename_response_time, delimiter=',')
        #latency = np.add(response_time, transfer_times)
        
        cumulative_wait_times = np.append(cumulative_wait_times, wait_times)
        #cumulative_transfer_times = np.append(cumulative_transfer_times, transfer_times)
        cumulative_response_time = np.append(cumulative_response_time, response_time)

        for idx, percentile in enumerate(percentile_list):
            if percentile == 0:
                matrices_wait_time[idx].append(np.mean(wait_times) / TICKS_PER_US)
                #matrices_transfer_time[idx].append(np.mean(transfer_times) / TICKS_PER_US)
                matrices_response_time[idx].append(np.mean(response_time) / TICKS_PER_US)
            else:
                matrices_wait_time[idx].append(np.percentile(wait_times, percentile) / TICKS_PER_US)
                #matrices_transfer_time[idx].append(np.percentile(transfer_times, percentile) / TICKS_PER_US)
                matrices_response_time[idx].append(np.percentile(response_time, percentile) / TICKS_PER_US)
            
    for idx, percentile in enumerate(percentile_list):
        if percentile == 0: 
            # Add comulative means (for all clusters combined)
            matrices_wait_time[idx].append(np.mean(cumulative_wait_times) / TICKS_PER_US)
            #matrices_transfer_time[idx].append(np.mean(cumulative_transfer_times) / TICKS_PER_US) 
            matrices_response_time[idx].append(np.mean(cumulative_response_time) / TICKS_PER_US)
            output_tag = str(policy) + '_' + distribution +  '_mean_'
        else:
            # Add comulative percentile (for all clusters combined)
            matrices_wait_time[idx].append(np.percentile(cumulative_wait_times, percentile) / TICKS_PER_US) 
            #matrices_transfer_time[idx].append(np.percentile(cumulative_transfer_times, percentile) / TICKS_PER_US) 
            matrices_response_time[idx].append(np.percentile(cumulative_response_time, percentile) / TICKS_PER_US)
            output_tag = str(policy) + '_' + distribution + '_p' + str(percentile) + '_'

        #print("OVERALL Clusters Policy: " + str(policy)+ " load: " + str(load) + ' ' + output_tag  + "waiting_times: " + str(matrices_wait_time[idx][-1]))
        print("Policy: " + str(policy)+ " load: " + str(load) + ' ' + output_tag  + "response_times: " + str(np.mean(matrices_response_time[idx][:-1])) + " STD: " + str(np.std(matrices_response_time[idx][:-1])))
        print("Policy: " + str(policy)+ " load: " + str(load) + ' ' + output_tag  + "waiting_times: " + str(np.mean(matrices_wait_time[idx][:-1])) + " STD: " + str(np.std(matrices_wait_time[idx][:-1])))
        output_file_wait_time = output_tag + 'wait_times_' + str(load) + '_r' + str(run_id) +'.csv'    
        #output_file_transfer_time = output_tag + distribution + '_' + col_name_extension + 'n' + str(num_hosts) + '_t' + str(num_tenants) + '_transfer_times_' + str(load) + '_r' + str(run_id) +'.csv'
        output_file_latency = output_tag  + 'response_time_' + str(load) + '_r' + str(run_id) +'.csv'

        np_array_wait_times = np.array(matrices_wait_time[idx])
        #np_array_transfer_times = np.array(matrices_transfer_time[idx])
        np_array_latency = np.array(matrices_response_time[idx])

        with open(result_dir + analysis_subdir + output_file_wait_time, 'wb') as output_file:
            np.savetxt(output_file, [np_array_wait_times], delimiter=', ', fmt='%.2f')
        # with open(result_dir + analysis_subdir + output_file_transfer_time, 'wb') as output_file:
        #     np.savetxt(output_file, [np_array_transfer_times], delimiter=', ', fmt='%.2f')
        with open(result_dir + analysis_subdir + output_file_latency, 'wb') as output_file:
            np.savetxt(output_file, [np_array_latency], delimiter=', ', fmt='%.2f')
    
def plot_latency(policies, metric, distribution, cluster_size_range, percentile=0.0, run_id=0, inc_racksched=0, is_colocate=False, name_tag=''):
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)
    x_axis = [load*100 for load in loads] 
    cluster_id_list,_ = get_clusters_within_range(cluster_size_range, is_colocate)
    # if is_colocate:
    #     col_name_extension = 'col_'
    # else:
    col_name_extension = ''
    #print("Plotting %s for %d clusters with size in range [%d, %d]" %(metric, len(cluster_id_list), cluster_size_range[0], cluster_size_range[-1]))
    use_sci = False
    fig, ax = plt.subplots()
    points_to_aggregate = np.array(list(cluster_id_list.keys()))
    #print (cluster_id_list)
    max_y = 0
    min_y = 1000000
    for i, policy in enumerate(policies):
        # if policy == 'racksched_partitioned_k2' or policy == 'adaptive_k2':
        #     TICKS_PER_US = 1
        # else:
        #     TICKS_PER_US = 1000
        #TICKS_PER_US = 1000
        if percentile == 0: 
            output_tag = '_mean_'
        else:
            output_tag = '_p' + str(percentile) + '_'
        y_axis = []
        y_err = []
        max_resp_time = 0
        for load in loads:
            if policy == 'sparrow' and percentile==99:
                y_axis = [resp_ms * 1000 for resp_ms in sparrow_resp_time_p99]
                y_err = [0] * len(loads)
                break
            filename_wait_time = str(policy) + '_' + distribution + output_tag + col_name_extension + 'wait_times_' + str(load) + '_r' + str(run_id) +'.csv'    
            filename_latency = str(policy) + '_' + distribution + output_tag + col_name_extension + 'response_times_' + str(load) + '_r' + str(run_id) +'.csv'
            if (load < 1):
                if metric == 'transfer_times':
                    latency = np.genfromtxt(result_dir + analysis_subdir + filename_transfer_time, delimiter=',')
                elif metric == 'wait_times':
                    latency = np.genfromtxt(result_dir + analysis_subdir + filename_wait_time, delimiter=',')
                elif metric == 'response_times':
                    latency = np.genfromtxt(result_dir + analysis_subdir + filename_latency, delimiter=',')
                #latency = latency[2]
            else:
                latency = np.array([10000000000])

            #print(metric + " Policy: " + str(algorithm_names[i])+ " load: " + str(load) + " max: " + str(max(latency)) + " cluster ID: " + str(np.where(latency == max(latency))))
            #latency = latency[:-1] # Last element is comulative clusters percentile
            
            
            #print("Policy: " + str(algorithm_names[i])+ " load: " + str(load) + " Mean: " + str(np.mean(latency)) + " STD: " + str(np.std(latency)))
            if percentile != 0:
                y_axis.append(np.median(latency/ TICKS_PER_US))
            else:
                y_axis.append(np.mean(latency / TICKS_PER_US))

            #y_err.append(np.std(latency / TICKS_PER_US))
            y_err.append(0)
            if y_axis[-1] > 1000:
                use_sci = True
        
        if policy == 'adaptive_k2':
            max_y = max(max_y, max(y_axis))
        min_y = min(min_y, min(y_axis))
        print("\nPolicy: " + str(policy))
        print(y_axis)
        _, caps, bars = plt.errorbar(x_axis, y_axis, linestyle=STYLES[algorithm_names[i]]['linestyle'],  linewidth=ALTERNATIVE_LINE_WIDTH+1, markersize=17, marker=STYLES[algorithm_names[i]]['marker'], color=STYLES[algorithm_names[i]]['color'], label=algorithm_names[i], elinewidth=4, capsize=4, capthick=1, zorder=4-i)
        [bar.set_alpha(0.3) for bar in bars]
        [cap.set_alpha(0.3) for cap in caps]
    ax.set_xlabel('Load (%)')
    #print(policy)
    plt.rcParams['legend.handlelength'] = 0.1
    plt.rcParams['legend.numpoints'] = 1
    handles, labels = ax.get_legend_handles_labels()
    # remove the errorbars
    handles = [h[0] for h in handles]
    
    if dissect:
        leg = ax.legend(handles, algorithm_names,  loc='best', labelspacing=0.3, handlelength=0.48)
    else:
        leg = ax.legend(handles, algorithm_names, ncol=3, handlelength=0.48, borderpad=0.08, borderaxespad=0.0, labelspacing=-0.2, columnspacing=0.4, frameon=True, loc='upper center')
        
        bb = leg.get_bbox_to_anchor().inverse_transformed(ax.transAxes)
        f = leg.get_frame()
        bb.x0 += 0.08
        bb.x1 += 0.08
        bb.y0 += 0.18
        bb.y1 += 0.18
        leg.set_bbox_to_anchor(bb, transform = ax.transAxes)
    for i in range(len(policies)):
            leg.get_lines()[i].set_linestyle('')
    plt.grid(True)
    # x_ticks = []
    # for x_point in x_axis:
    #     if x_point != 99: 
    #         x_ticks.append(x_point)
    # ax.set_xticks(x_ticks)
    # if (percentile <= 50):
    #     ax.set_ylim(0, 1300)
    # elif (percentile > 75):
    #     ax.set_ylim(0, 8000)
    #ax.set_ylim(0.9*min_y, 2*max_y)
    ax.yaxis.get_offset_text().set_fontsize(TICK_FONT_SIZE)

    ax.yaxis.set_major_formatter(OOMFormatter(3, "%.1f"))
    ax.ticklabel_format(axis='y', style='sci', scilimits=(3,3))
    #ax.set_ylim(400, 4000)
    #ax.set_ylim(top=4000)
    ax.set_xticks([0, 25, 50, 75, 99])
    if percentile == 0:
        stat_label = 'Avg. '
    else:
        stat_label = str(percentile) + '% '
    if metric == 'transfer_times':
            text_label = 'Scheduling Time'
    elif metric == 'wait_times':
        text_label = 'Waiting Time'
    else:
        text_label = 'Resp. Time'

    ax.set_ylabel(stat_label+ text_label + ' (%ss)' % r'$\mu$')
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    
    if use_sci:
        plt.ticklabel_format(axis="y", style="sci", scilimits=(0,0))
    
    if percentile == 0:
        #'_inc_rsched_'
        output_name =  distribution + '_' +col_name_extension+ metric + '_avg_r' +str(run_id)
        #plt.title(text_label + ' Mean')
    else:
        output_name = distribution + '_'  + col_name_extension+ metric + '_' + str(percentile) + '_r' +str(run_id) 
    if inc_racksched:
        output_name += '_inc_rsched'
    plt.tight_layout()
    plt.savefig(result_dir + plot_subdir + output_name + name_tag +'.png', ext='png', bbox_inches="tight")
    plt.savefig(result_dir + plot_subdir + output_name + name_tag +'.pdf', ext='pdf', bbox_inches='tight')
    #plt.show(fig)


def plot_latency_all(policies, metric, distribution, cluster_size_range, percentile=0.0, run_id=0, inc_racksched=0, is_colocate=False, name_tag=''):
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)
    x_axis = [load*100 for load in loads] 
    cluster_id_list,_ = get_clusters_within_range(cluster_size_range, is_colocate)
    # if is_colocate:
    #     col_name_extension = 'col_'
    # else:
    col_name_extension = ''
    #print("Plotting %s for %d clusters with size in range [%d, %d]" %(metric, len(cluster_id_list), cluster_size_range[0], cluster_size_range[-1]))
    use_sci = False
    fig, ax = plt.subplots()
    points_to_aggregate = np.array(list(cluster_id_list.keys()))
    #print (cluster_id_list)
    max_y = 0
    min_y = 1000000
    dist_list = ['exponential', 'bimodal', 'trimodal']
    for i, policy in enumerate(policies):
        # if policy == 'racksched_partitioned_k2' or policy == 'adaptive_k2':
        #     TICKS_PER_US = 1
        # else:
        #     TICKS_PER_US = 1000
        #TICKS_PER_US = 1000
        if percentile == 0: 
            output_tag = '_mean_'
        else:
            output_tag = '_p' + str(percentile) + '_'
        y_axis = []
        y_err = []
        max_resp_time = 0
        for load in loads:
            val = []
            for dist in dist_list:
                filename_wait_time = str(policy) + '_' + dist + output_tag + col_name_extension + 'wait_times_' + str(load) + '_r' + str(run_id) +'.csv'    
                filename_latency = str(policy) + '_' + dist + output_tag + col_name_extension + 'response_times_' + str(load) + '_r' + str(run_id) +'.csv'
                if (load < 1):
                    if metric == 'transfer_times':
                        latency = np.genfromtxt(result_dir + 'result_l40_k2_' + dist + '/' + analysis_subdir + filename_transfer_time, delimiter=',')
                    elif metric == 'wait_times':
                        latency = np.genfromtxt(result_dir + 'result_l40_k2_' + dist + '/' + analysis_subdir + filename_wait_time, delimiter=',')
                    elif metric == 'response_times':
                        latency = np.genfromtxt(result_dir + 'result_l40_k2_' + dist + '/' + analysis_subdir + filename_latency, delimiter=',')
                    latency = latency[points_to_aggregate]
                else:
                    latency = np.array([10000000])
                val.append(np.mean(latency / TICKS_PER_US))
                #print(metric + " Policy: " + str(algorithm_names[i])+ " load: " + str(load) + " max: " + str(max(latency)) + " cluster ID: " + str(np.where(latency == max(latency))))
                #latency = latency[:-1] # Last element is comulative clusters percentile
                
            
            y_axis.append(np.sum(val))

            #y_err.append(np.std(latency / TICKS_PER_US))
            y_err.append(0)
            if y_axis[-1] > 1000:
                use_sci = True
        
        if policy == 'adaptive_k2':
            max_y = max(max_y, max(y_axis))
        min_y = min(min_y, min(y_axis))
        print("\nPolicy: " + str(policy))
        print(y_axis)
        _, caps, bars = plt.errorbar(x_axis, y_axis, linestyle='--', yerr=y_err, linewidth=ALTERNATIVE_LINE_WIDTH, markersize=16, marker=markers[i], color=color_pallete[i], label=algorithm_names[i], elinewidth=4, capsize=4, capthick=1, zorder=4-i)
        [bar.set_alpha(0.3) for bar in bars]
        [cap.set_alpha(0.3) for cap in caps]
    ax.set_xlabel('Load (%)')
    #print(policy)
    plt.rcParams['legend.handlelength'] = 0.1
    plt.rcParams['legend.numpoints'] = 1
    handles, labels = ax.get_legend_handles_labels()
    # remove the errorbars
    handles = [h[0] for h in handles]
    plt.legend(handles, labels, handletextpad=0.3, borderpad=0.4)
    
    plt.grid(True)
    # x_ticks = []
    # for x_point in x_axis:
    #     if x_point != 99: 
    #         x_ticks.append(x_point)
    # ax.set_xticks(x_ticks)
    # if (percentile <= 50):
    #     ax.set_ylim(0, 1300)
    # elif (percentile > 75):
    #     ax.set_ylim(0, 8000)
    #ax.set_ylim(0.9*min_y, 2*max_y)

    ax.yaxis.set_major_formatter(OOMFormatter(3, "%d"))
    ax.ticklabel_format(axis='y', style='sci', scilimits=(3,3))

    ax.set_ylim(0, 15000)
    ax.set_xticks([0, 25, 50, 75, 99])
    if percentile == 0:
        stat_label = 'Avg. '
    else:
        stat_label = str(percentile) + '% '
    if metric == 'overall_transfer_times':
            text_label = 'Scheduling Time'
    elif metric == 'overall_wait_times':
        text_label = 'Waiting Time'
    else:
        text_label = 'Response Time'

    ax.set_ylabel(stat_label+ text_label + ' (%ss)' % r'$\mu$')
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    
    if use_sci:
        plt.ticklabel_format(axis="y", style="sci", scilimits=(0,0))
    
    if percentile == 0:
        #'_inc_rsched_'
        output_name =   col_name_extension+ metric + '_avg_r' +str(run_id)
        #plt.title(text_label + ' Mean')
    else:
        output_name =  col_name_extension+ metric + '_' + str(percentile) + '_r' +str(run_id) 
    if inc_racksched:
        output_name += '_inc_rsched'
    plt.tight_layout()
    plt.savefig(result_dir + plot_subdir + output_name + name_tag +'.png', ext='png', bbox_inches="tight")
    plt.savefig(result_dir + plot_subdir + output_name + name_tag +'.pdf', ext='pdf', bbox_inches='tight')
    #plt.show(fig)

def plot_latency_dimapct(policies, load, metric, distribution, cluster_size_range, percentile=0.0, run_id=0, inc_racksched=0, is_colocate=False, name_tag=''):
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)
    
    cluster_id_list,_ = get_clusters_within_range(cluster_size_range, is_colocate)
    k_values = ['2', '4', '8', '16']
    x_axis = [int(k) for k in k_values] 
    col_name_extension = ''
    
    use_sci = False
    fig, ax = plt.subplots()
    points_to_aggregate = np.array(list(cluster_id_list.keys()))
    
    ylim = 8000
    min_y = 1000000
    width = 0.3

    ind = np.arange(len(k_values))
    for i, policy in enumerate(policies):
        if percentile == 0: 
            output_tag = '_mean_'
        else:
            output_tag = '_p' + str(percentile) + '_'
        y_axis = []
        y_err = []
        max_resp_time = 0

        for num_samples in k_values:
            if policy == 'sparrow' and percentile==99:
                y_axis = [resp_ms * 1000 for resp_ms in sparrow_resp_time_p99]
                y_err = [0] * len(loads)
                break
            if policy == 'racksched_iu': # Naming convention had k_X (Num samples befure the iu (Instant update tag))
                policy_d_file_name = 'racksched_k' + num_samples + '_iu'
            elif policy == 'racksched_k1000000_iu':
                policy_d_file_name = 'racksched_k1000000_iu'
            else:
                policy_d_file_name = policy + '_k' + num_samples
            filename_wait_time = policy_d_file_name + '_' + distribution + output_tag + col_name_extension + 'wait_times_' + str(load) + '_r' + str(run_id) +'.csv'    
            filename_latency = policy_d_file_name + '_' + distribution + output_tag + col_name_extension + 'response_times_' + str(load) + '_r' + str(run_id) +'.csv'
        
            if metric == 'transfer_times':
                latency = np.genfromtxt(result_dir + analysis_subdir + filename_transfer_time, delimiter=',')
            elif metric == 'wait_times':
                latency = np.genfromtxt(result_dir + analysis_subdir + filename_wait_time, delimiter=',')
            elif metric == 'response_times':
                latency = np.genfromtxt(result_dir + analysis_subdir + filename_latency, delimiter=',')
            latency = latency[points_to_aggregate]
        
            
            if percentile != 0:
                y_axis.append(np.mean(latency / TICKS_PER_US))
            else:
                y_axis.append(np.mean(latency / TICKS_PER_US))

            y_err.append(np.std(latency / TICKS_PER_US))
            #y_err.append(0)
            if y_axis[-1] > 1000:
                use_sci = True
            if policy == 'racksched_k1000000_iu': # Oracle
                break
        if policy == 'racksched_k1000000_iu': # Oracle
            plt.axhline(y=y_axis[0], color='0.3', linestyle='--', alpha=0.6, linewidth=SMALL_LINE_WIDTH)
            print("\nPolicy: " + str(policy))
            print(y_axis)
        else:
            x_axis = np.array(x_axis)
            min_y = min(min_y, min(y_axis))
            print("\nPolicy: " + str(policy))
            print(y_axis)
            ax.bar(ind + i*width, y_axis, width, yerr=y_err, label=algorithm_names[i], color=color_pallete[i], error_kw=dict(lw=5, capsize=8, capthick=3))
            for j in range(len(y_axis)):
                if y_axis[j] > ylim:
                    plt.annotate("{:.1f}".format(y_axis[j]/1000), xy=(ind[j] + i*width, ylim-100), ha='center', fontsize=AUTLABEL_FONT_SIZE, va='bottom')

    
    ax.set_xlabel('# Samples (d)')
    #print(policy)
    
    handles, labels = ax.get_legend_handles_labels()
    
    
    plt.legend(loc='upper left')
    
    plt.grid(True)

    ax.yaxis.set_major_formatter(OOMFormatter(3, "%g"))
    ax.ticklabel_format(axis='y', style='sci', scilimits=(3,3))

    ax.set_ylim(0, ylim)

    ax.set_xticks(ind + width)
    ax.set_xticklabels(k_values)
    if percentile == 0:
        stat_label = 'Avg. '
    else:
        stat_label = str(percentile) + '% '
    if metric == 'transfer_times':
            text_label = 'Scheduling Time'
    elif metric == 'wait_times':
        text_label = 'Waiting Time'
    else:
        text_label = 'Response Time'

    ax.set_ylabel(stat_label+ text_label + ' (%ss)' % r'$\mu$')
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    
    if use_sci:
        plt.ticklabel_format(axis="y", style="sci", scilimits=(0,0))
    
    if percentile == 0:
        output_name =  'dimpact_' + distribution + '_' +col_name_extension + metric + '_l' + str(load) + '_avg_r' +str(run_id)
        
    else:
        output_name = 'dimpact_' +  distribution + '_'  + col_name_extension + metric + '_l' + str(load) + '_' + str(percentile) + '_r' +str(run_id) 
    
    if inc_racksched:
        output_name += '_inc_rsched'
    plt.tight_layout()
    plt.savefig(result_dir + plot_subdir + output_name + '_bar' +'.png', ext='png', bbox_inches="tight")
    plt.savefig(result_dir + plot_subdir + output_name + '_bar' +'.pdf', ext='pdf', bbox_inches='tight')
    #plt.show(fig)

def plot_latency_cdf(policies, load, metric, distribution, cluster_size_range, run_id=0, inc_racksched=0, is_colocate=False, name_tag=''):
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)
    x_axis = [load*100 for load in loads] 
    cluster_id_list,_ = get_clusters_within_range(cluster_size_range, is_colocate)
    # if is_colocate:
    #     col_name_extension = 'col_'
    # else:
    #     col_name_extension = ''
    col_name_extension = ''
    #print("Plotting %s for %d clusters with size in range [%d, %d]" %(metric, len(cluster_id_list), cluster_size_range[0], cluster_size_range[-1]))
    use_sci = False
    fig, ax = plt.subplots()
    points_to_aggregate = np.array(list(cluster_id_list.keys()))
    
    max_val = 0
    for i, policy in enumerate(policies):
        res_policy = []
        for percentile in range (1, 101):
            if percentile == 0: 
                output_tag = '_mean_'
            else:
                output_tag = '_p' + str(percentile) + '_'
            y_axis = []
            y_err = []
            
            filename_wait_time = str(policy) + '_' + distribution + output_tag + col_name_extension + 'wait_times_' + str(load) + '_r' + str(run_id) +'.csv'    
            filename_latency = str(policy) + '_' + distribution + output_tag + col_name_extension + 'response_times_' + str(load) + '_r' + str(run_id) +'.csv'
            if metric == 'transfer_times':
                latency = np.genfromtxt(result_dir + analysis_subdir + filename_transfer_time, delimiter=',')
            elif metric == 'wait_times':
                latency = np.genfromtxt(result_dir + analysis_subdir + filename_wait_time, delimiter=',')
            elif metric == 'response_times':
                latency = np.genfromtxt(result_dir + analysis_subdir + filename_latency, delimiter=',')

            #print(metric + " Policy: " + str(algorithm_names[i])+ " load: " + str(load) + " max: " + str(max(latency)) + " cluster ID: " + str(np.where(latency == max(latency))))
            #latency = latency[:-1] # Last element is comulative clusters percentile
            res_policy.append(latency/TICKS_PER_US)
            if (policy == 'adaptive_k2'):
                max_val = max(max(res_policy), max_val)
            #print("Policy: " + str(algorithm_names[i])+ " load: " + str(load) + " Mean: " + str(np.mean(latency)) + " STD: " + str(np.std(latency))
            
            # if y_axis[-1] > 1000:
            #     use_sci = True
        result_sorted = np.sort(res_policy)
        print (max(res_policy))
        p_result = 1. * np.arange(len(res_policy)) / (len(res_policy) - 1)
        ax.plot(result_sorted, p_result, linestyle='--',  linewidth=DEFAULT_LINE_WIDTH, color=color_pallete[i], label=algorithm_names[i], zorder=4-i)
        # [bar.set_alpha(0.3) for bar in bars]
        # [cap.set_alpha(0.3) for cap in caps]
    
    
    #plt.rcParams['legend.handlelength'] = 0
    #plt.rcParams['legend.numpoints'] = 1
    #handles, labels = ax.get_legend_handles_labels()
    # remove the errorbars
    # handles = [h[0] for h in handles]
    plt.legend(loc='best')
    
    
    # x_ticks = []
    # for x_point in x_axis:
    #     if x_point != 99: 
    #         x_ticks.append(x_point)
    # ax.set_xticks(x_ticks)
    
    ax.set_ylim(bottom=0, top=1)
    #ax.set_xscale('log')


    ax.set_xlim(0, 30000)
    #ax.set_yticks(list(range(0, 4001 , 1000)))
    if metric == 'transfer_times':
            text_label = 'Scheduling Time'
    elif metric == 'wait_times':
        text_label = 'Waiting Time'
    else:
        text_label = 'Response Time'

    ax.set_ylabel('Fraction of Tasks')
    ax.set_xlabel(text_label + ' (%ss)' % r'$\mu$')
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    plt.grid(True)
    #if max_val> 1000:
    plt.ticklabel_format(axis="x", style="sci", scilimits=(0,0))
    
    output_name = distribution + '_'  + col_name_extension+ metric + '_cdf_r' + str(run_id) + '_' + str(load)
   
    plt.tight_layout()
    plt.savefig(result_dir + plot_subdir + output_name + name_tag + '.png', ext='png', bbox_inches="tight")
    plt.savefig(result_dir + plot_subdir + output_name + name_tag +'.pdf', ext='pdf', bbox_inches='tight')
    #plt.show(fig)

def plot_switch_packet_rate(policies, distribution, percentile=0.0, metric="msg", layer='spine', logarithmic=True, is_colocate=False, sum_layer=False):
    x_axis = loads
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)
    x_axis = [load*100 for load in loads] 

    # if is_colocate:
    #     col_name_extension = 'col_'
    # else:
    #     col_name_extension = ''
    col_name_extension = ''
    if metric== "msg":
        metric_spine = 'msg_per_sec_spine'
        metric_tor = 'msg_per_sec_tor'
        y_label = '#Msgs/s'
    elif metric == "task":
        metric_spine = 'task_per_sec_spine'
        metric_tor = 'task_per_sec_tor'
        y_label = '#Task/s'

    for run_id in run_id_list:
        fig, ax = plt.subplots()
        for i, policy in enumerate(policies):
            y_axis = []

            for load in loads:
                filename_spine = policy + '_' + distribution + '_' + col_name_extension  + metric_spine +  '_' + str(load) + '_r' + str(run_id) +  '.csv'
                filename_tor = policy + '_' + distribution + '_' + col_name_extension + metric_tor +  '_' + str(load) + '_r' + str(run_id) +  '.csv'

                if layer == 'spine':
                    msg_per_sec_spine = np.genfromtxt(result_dir + analysis_subdir +filename_spine, delimiter=',')
                    if not sum_layer:
                        if percentile == 0:
                            y_axis.append(msg_per_sec_spine[np.nonzero(msg_per_sec_spine)].mean())
                        else:
                            y_axis.append(np.percentile(msg_per_sec_spine, percentile))
                    else:
                        y_axis.append(np.sum(msg_per_sec_spine))
                
                elif layer== 'tor':
                    msg_per_sec_tor = np.genfromtxt(result_dir + analysis_subdir + filename_tor, delimiter=',')
                    if not sum_layer:
                        if percentile == 0:
                            y_axis.append(msg_per_sec_tor[np.nonzero(msg_per_sec_tor)].mean())
                        else:
                            y_axis.append(np.percentile(msg_per_sec_tor, percentile))
                    else:
                        y_axis.append(np.sum(msg_per_sec_tor))
            print("Msg rate for " + str(policy) + ": ")
            print (y_axis)
            plt.plot(x_axis, y_axis, '--', linewidth=ALTERNATIVE_LINE_WIDTH, markersize=LEGEND_FONT_SIZE, marker=markers[i], color=color_pallete[i], label=algorithm_names[i])
        
        ax.set_xlabel('Load (%)')
        ax.set_ylabel(y_label)
        
        ax.get_yaxis().get_offset_text().set_visible(False)
        sns.despine(ax=ax, top=True, right=True, left=False, bottom=False)
        if logarithmic:
            ax.set_yscale('log')
        ax.set_xticks(x_axis)
        
        plt.rcParams['legend.handlelength'] = 1
        plt.rcParams['legend.numpoints'] = 1
        handles, labels = ax.get_legend_handles_labels()
        plt.legend(handles, labels, loc='best')
        plt.grid(True)
        
        if not sum_layer:
            if percentile == 0:
                stat_tag = 'avg'
            else:
                stat_tag = str(percentile)
        else:
            stat_tag = 'sum'
        output_name = distribution + '_' + col_name_extension + layer + '_' + metric+ '_per_sec_' + stat_tag + '_r' + str(run_id)
        
        #plt.title('Msg Rate ' + stat_tag)
        plt.tight_layout()
        plt.savefig(result_dir + plot_subdir + output_name + '.png', ext='png', bbox_inches="tight")
        plt.savefig(result_dir + plot_subdir + output_name + '.pdf', ext='pdf', bbox_inches='tight')

def plot_msg_breakdown(policy, distribution, percentile=0.0, metric="msg", layer='spine', logarithmic=True, is_colocate=False, sum_layer=False):
    x_axis = loads
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)
    x_axis = [load*100 for load in loads if load < 1] 
    ind = np.arange(len(x_axis))
    width = 0.5
    offset = 0
    # if is_colocate:
    #     col_name_extension = 'col_'
    # else:
    #     col_name_extension = ''
    col_name_extension = ''
    if metric== "msg":
        metric_spine = 'msg_per_sec_spine'
        metric_tor = 'msg_per_sec_tor'
        y_label = '#Msgs/task'
    elif metric == "task":
        metric_spine = 'task_per_sec_spine'
        metric_tor = 'task_per_sec_tor'
        y_label = '#Task/s'

    for run_id in run_id_list:
        fig, ax = plt.subplots()
        y_msg = np.array([])
        y_msg_idle_signal = []
        y_msg_idle_remove = []
        y_msg_load_signal = []

        for load in loads:
            if load >= 1:
                continue
            filename_spine_msg = policy + '_' + distribution + '_' + col_name_extension  + 'msg_per_sec_spine' +  '_' + str(load) + '_r' + str(run_id) +  '.csv'
            filename_spine_task = policy + '_' + distribution + '_' + col_name_extension  + 'task_per_sec_spine' +  '_' + str(load) + '_r' + str(run_id) +  '.csv'
            filename_spine_msg_idle_remove = policy + '_' + distribution + '_' + col_name_extension  + 'msg_per_sec_spine_idle_remove' +  '_' + str(load) + '_r' + str(run_id) +  '.csv'
            filename_spine_msg_idle_signal = policy + '_' + distribution + '_' + col_name_extension  + 'msg_per_sec_spine_idle_signal' +  '_' + str(load) + '_r' + str(run_id) +  '.csv'
            filename_spine_msg_load_signal = policy + '_' + distribution + '_' + col_name_extension  + 'msg_per_sec_spine_load_signal' +  '_' + str(load) + '_r' + str(run_id) +  '.csv'

            msg_per_sec_spine = np.genfromtxt(result_dir + analysis_subdir +filename_spine_msg, delimiter=',')
            task_per_sec_spine = np.genfromtxt(result_dir + analysis_subdir +filename_spine_task, delimiter=',')
            msg_per_sec_spine_idle_remove = np.genfromtxt(result_dir + analysis_subdir +filename_spine_msg_idle_remove, delimiter=',')
            msg_per_sec_spine_msg_idle_signal = np.genfromtxt(result_dir + analysis_subdir +filename_spine_msg_idle_signal, delimiter=',')
            msg_per_sec_spine_msg_load_signal = np.genfromtxt(result_dir + analysis_subdir +filename_spine_msg_load_signal, delimiter=',')
            # y_msg += np.mean(msg_per_sec_spine) / np.mean(task_per_sec_spine)
            y_msg_idle_signal.append(np.mean(msg_per_sec_spine_msg_idle_signal) / np.mean(task_per_sec_spine))
            y_msg_idle_remove.append(np.mean(msg_per_sec_spine_idle_remove) / np.mean(task_per_sec_spine))
            y_msg_load_signal.append(np.mean(msg_per_sec_spine_msg_load_signal) / np.mean(task_per_sec_spine))
            
        y_msg_idle_signal = np.array(y_msg_idle_signal)
        y_msg_idle_remove = np.array(y_msg_idle_remove)
        y_msg_load_signal = np.array(y_msg_load_signal)
        y_msg_idle_tot = y_msg_idle_signal+y_msg_idle_remove;

        plt.bar(ind, y_msg_idle_tot, width=width, color=color_pallete[1], label='Idle Add/Remove')
        plt.bar(ind, y_msg_load_signal, bottom=y_msg_idle_tot, width=width, color=color_pallete[0],  label='Load Updates')
        
        #plt.bar(ind + 2*offset, y_msg_idle_remove, bottom=y_msg_idle_signal, width=width, color=color_pallete[2], label='Idle Add/Remove')
        
        
        ax.set_xlabel('Load (%)')
        ax.set_ylabel(y_label)
        
        ax.get_yaxis().get_offset_text().set_visible(False)
        sns.despine(ax=ax, top=True, right=True, left=False, bottom=False)
        
        plt.xticks(ind + offset, [str(int(x)) for x in x_axis])
        
        plt.rcParams['legend.handlelength'] = 1
        plt.rcParams['legend.numpoints'] = 1
        handles, labels = ax.get_legend_handles_labels()
        plt.legend(handles, labels, loc='best')
        plt.grid(True)
        
        if not sum_layer:
            if percentile == 0:
                stat_tag = 'avg'
            else:
                stat_tag = str(percentile)
        else:
            stat_tag = 'sum'
        output_name = distribution + '_' + col_name_extension + layer + '_' + metric+ '_per_sec_' + stat_tag + '_r' + str(run_id)
        
        #plt.title('Msg Rate ' + stat_tag)
        plt.tight_layout()
        plt.savefig(result_dir + plot_subdir + output_name + '.png', ext='png', bbox_inches="tight")
        plt.savefig(result_dir + plot_subdir + output_name + '.pdf', ext='pdf', bbox_inches='tight')


def plot_msg_breakdown_vs_net_condition(policy, net_condition, distribution, var_list, loads=[0.9],  percentile=0.0, run_id=0, is_colocate=False):
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)
    x_axis = [var*100 for var in var_list] 
    ind = np.arange(len(x_axis))
    width = 0.4
    offset = 0
    y_label = '#Msgs/task'
    col_name_extension = ''
    
    run_id = 0
    for load in loads:
        print ("LOAD")
        fig, ax = plt.subplots()
        y_msg = np.array([])
        y_msg_idle_signal = []
        y_msg_idle_remove = []
        y_msg_load_signal = []
        for var in var_list:
            if net_condition == 'loss':
                condition_tag = f'l{var}_d5'
            elif net_condition == 'latency':
                condition_tag = f'l1e-05_d{var}'
            name_base = policy + '_' + condition_tag + '_' + distribution
            filename_spine_msg = name_base + '_' + col_name_extension  + 'msg_per_sec_spine' +  '_' + str(load) + '_r' + str(run_id) +  '.csv'
            filename_spine_task = name_base + '_' + col_name_extension  + 'task_per_sec_spine' +  '_' + str(load) + '_r' + str(run_id) +  '.csv'
            filename_spine_msg_idle_remove = name_base + '_' + col_name_extension  + 'msg_per_sec_spine_idle_remove' +  '_' + str(load) + '_r' + str(run_id) +  '.csv'
            filename_spine_msg_idle_signal = name_base + '_' + col_name_extension  + 'msg_per_sec_spine_idle_signal' +  '_' + str(load) + '_r' + str(run_id) +  '.csv'
            filename_spine_msg_load_signal = name_base + '_' + col_name_extension  + 'msg_per_sec_spine_load_signal' +  '_' + str(load) + '_r' + str(run_id) +  '.csv'

            msg_per_sec_spine = np.genfromtxt(result_dir + analysis_subdir +filename_spine_msg, delimiter=',')
            task_per_sec_spine = np.genfromtxt(result_dir + analysis_subdir +filename_spine_task, delimiter=',')
            msg_per_sec_spine_idle_remove = np.genfromtxt(result_dir + analysis_subdir +filename_spine_msg_idle_remove, delimiter=',')
            msg_per_sec_spine_msg_idle_signal = np.genfromtxt(result_dir + analysis_subdir +filename_spine_msg_idle_signal, delimiter=',')
            msg_per_sec_spine_msg_load_signal = np.genfromtxt(result_dir + analysis_subdir +filename_spine_msg_load_signal, delimiter=',')
            # y_msg += np.mean(msg_per_sec_spine) / np.mean(task_per_sec_spine)
            y_msg_idle_signal.append(np.mean(msg_per_sec_spine_msg_idle_signal) / np.mean(task_per_sec_spine))
            y_msg_idle_remove.append(np.mean(msg_per_sec_spine_idle_remove) / np.mean(task_per_sec_spine))
            y_msg_load_signal.append(np.mean(msg_per_sec_spine_msg_load_signal) / np.mean(task_per_sec_spine))
            
        y_msg_idle_signal = np.array(y_msg_idle_signal)
        y_msg_idle_remove = np.array(y_msg_idle_remove)
        y_msg_idle_tot = y_msg_idle_signal+y_msg_idle_remove;

        plt.bar(ind, y_msg_idle_tot, width=width, color=color_pallete[1], label='Idle Add/Remove')
        plt.bar(ind, y_msg_load_signal, bottom=y_msg_idle_tot, width=width, color=color_pallete[0],  label='Load Updates')
        
        ax.set_xlabel('Load (%)')
        if net_condition == 'loss':
            ax.set_xlabel('Loss Rate (%)')
            ax.set_xticklabels([x*100 for x in x_axis])
        elif net_condition == 'latency':
            ax.set_xlabel(f'Per-Hop Delay' + '(%ss)' % r'$\mu$')
            ax.set_xticklabels(x_axis)
        
        #ax.get_yaxis().get_offset_text().set_visible(False)
        sns.despine(ax=ax, top=True, right=True, left=False, bottom=False)
        
        plt.xticks(ind + offset, [str(x) for x in x_axis])
        
        plt.rcParams['legend.handlelength'] = 1
        plt.rcParams['legend.numpoints'] = 1
        handles, labels = ax.get_legend_handles_labels()
        plt.legend(handles, labels, loc='best')
        plt.grid(True)
        stat_tag = 'avg'
        ax.set_ylabel(y_label)
        output_name = distribution +  '_msg_per_sec_breakdown_' + stat_tag + '_l' + str(load)
        
        #plt.title('Msg Rate ' + stat_tag)
        plt.tight_layout()
        plt.savefig(result_dir + plot_subdir + output_name + '.png', ext='png', bbox_inches="tight")
        plt.savefig(result_dir + plot_subdir + output_name + '.pdf', ext='pdf', bbox_inches='tight')

def plot_switch_packet_rate_ratios(parent_dir, policies, distribution, percentile=0.0, metric="msg", layer='spine', logarithmic=True, is_colocate=False, sum_layer=False):
    x_axis = loads
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=2.5, handletextpad=0.15)
    x_axis = [load*100 for load in loads] 

    # if is_colocate:
    #     col_name_extension = 'col_'
    # else:
    #     col_name_extension = ''
    col_name_extension = ''
    if metric== "msg":
        metric_spine = 'msg_per_sec_spine'
        metric_tor = 'msg_per_sec_tor'
        y_label = '#Msgs/s'
    elif metric == "task":
        metric_spine = 'task_per_sec_spine'
        metric_tor = 'task_per_sec_tor'
        y_label = '#Task/s'
    fig, ax = plt.subplots()
    for run_id in run_id_list:
        for i, policy in enumerate(policies):
            for r_idx, ratio in enumerate(l_values):
                result_dir = parent_dir + 'result_l' + str(ratio) + '_k2_' + distribution + '/'
                y_axis = []

                for load in loads:
                    filename_spine = policy + '_' + distribution + '_' + col_name_extension  + metric_spine +  '_' + str(load) + '_r' + str(run_id) +  '.csv'
                    filename_tor = policy + '_' + distribution + '_' + col_name_extension + metric_tor +  '_' + str(load) + '_r' + str(run_id) +  '.csv'

                    if layer == 'spine':
                        msg_per_sec_spine = np.genfromtxt(result_dir + analysis_subdir +filename_spine, delimiter=',')
                        if not sum_layer:
                            if percentile == 0:
                                y_axis.append(msg_per_sec_spine[np.nonzero(msg_per_sec_spine)].mean())
                            else:
                                y_axis.append(np.percentile(msg_per_sec_spine, percentile))
                        else:
                            y_axis.append(np.sum(msg_per_sec_spine))
                    
                    elif layer== 'tor':
                        msg_per_sec_tor = np.genfromtxt(result_dir + analysis_subdir + filename_tor, delimiter=',')
                        if not sum_layer:
                            if percentile == 0:
                                y_axis.append(msg_per_sec_tor[np.nonzero(msg_per_sec_tor)].mean())
                            else:
                                y_axis.append(np.percentile(msg_per_sec_tor, percentile))
                        else:
                            y_axis.append(np.sum(msg_per_sec_tor))

                #print np.mean(y_axis)
                plt.plot(x_axis, y_axis, linestyle[r_idx], linewidth=DEFAULT_LINE_WIDTH, markersize=LEGEND_FONT_SIZE, color=color_pallete[i], label=algorithm_names[i] + ', r' + str(ratio))
            
        ax.set_xlabel('Load (%)')
        ax.set_ylabel(y_label)
        
        ax.get_yaxis().get_offset_text().set_visible(False)
        sns.despine(ax=ax, top=True, right=True, left=False, bottom=False)
        if logarithmic:
            ax.set_yscale('log')
        ax.set_xticks(x_axis)
        
        plt.rcParams['legend.handlelength'] = 1
        plt.rcParams['legend.numpoints'] = 1
        handles, labels = ax.get_legend_handles_labels()
        plt.legend(handles, labels, loc='best',
          ncol=2, handlelength=2, labelspacing=0.2, columnspacing=0.8)
        plt.grid(True)
        
        if not sum_layer:
            if percentile == 0:
                stat_tag = 'avg'
            else:
                stat_tag = str(percentile)
        else:
            stat_tag = 'sum'
        output_name = distribution + '_' + col_name_extension + layer + '_' + metric+ '_per_sec_' + stat_tag + '_r' + str(run_id)
        
        #plt.title('Msg Rate ' + stat_tag)
        plt.tight_layout()
        plt.savefig(parent_dir + plot_subdir + output_name + '.png', ext='png', bbox_inches="tight")
        plt.savefig(parent_dir + plot_subdir + output_name + '.pdf', ext='pdf', bbox_inches='tight')

def plot_failure_impacted_tors(distribution, num_runs=5,layer='spine', is_colocate=False):
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)
    
    run_result_list = []
    x_axis = [] 
    y_axis = []
    plot_subdir = 'failure_plots/'
    # num affected clusters is not related to load or policy so we only need to look up one of the files and count the lengths
    metric = 'affected_tors_1.0_'
    if is_colocate:
        col_name_extension = 'col_'
    else:
        col_name_extension = ''
    fig, ax = plt.subplots()
    for i, l_val in enumerate(l_values):    
        run_result_list = []
        for run_id in range(num_runs):
            filename_spine = 'adaptive_k2_' + distribution + '_' + col_name_extension + metric + 'r' + str(run_id) + '.csv'
            result = np.genfromtxt(result_dir + "/result_failure_spine_l" + str(l_val) + "/" + filename_spine, delimiter=',')
            run_result_list.append(len(result))

        result_sorted = np.sort(run_result_list) 
        print("\nFor Ratio: " + str(l_val))
        print ("Max #tors affected by spine failure: " + str(max(result_sorted)))
        print ("Mean #tors affected by spine failure: " + str(np.mean(result_sorted)))
        p_result = 1. * np.arange(len(run_result_list)) / (len(run_result_list) - 1)
        ax.plot(result_sorted, p_result, '-', label=l_value_lables[i], color=color_pallete[i])
        ax.set_ylim(bottom=0, top=1)
        ax.set_xlabel('# Control Msgs to Leaves')
        ax.set_ylabel('Fraction of failures')
        ax.grid(True, which="both", ls="--", alpha=0.6)
        handles, labels = ax.get_legend_handles_labels()
        handles.insert(0, 'Ratio (r)')
        labels.insert(0, '')
        ax.legend(handles, labels, fontsize=LEGEND_FONT_SIZE,
            handler_map={str: LegendTitle({'fontsize': LEGEND_FONT_SIZE})}, loc='best', handlelength=1.7, handletextpad=0.7)
        #plt.legend(loc='best')
        if layer == 'spine':
            output_name = distribution + '_affected_tors_cdf'
        
        plt.tight_layout()
        plt.savefig(result_dir + plot_subdir + output_name + '.png', ext='png', bbox_inches="tight")
        plt.savefig(result_dir + plot_subdir + output_name + '.pdf', ext='pdf', bbox_inches='tight')

def plot_failure_missed_tasks_cdf(distribution, num_runs=5,layer='spine', is_colocate=False):
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)
    plot_subdir = 'failure_plots/'
    mean_task_time = 275
    load = 1.0 # we care about percentage of failed tasks so load is irrelevant report results for full utilization
    
    x_axis = loads 
    y_axis = []
    total_workers = get_total_workers()
    # num affected clusters is not related to load or policy so we only need to look up one of the files and count the lengths
    metric_missed = 'num_failed_tasks_'
    metric_scheduled = 'num_scheduled_tasks_'
    metric_conv_latency = 'converge_latency_'

    if is_colocate:
        col_name_extension = 'col_'
    else:
        col_name_extension = ''

    fig, ax = plt.subplots()
    y_axis_imp=[]
    y_err_imp=[]
    y_axis_all=[]
    y_err_all=[]
    ind = np.arange(len(l_values))  # the x locations for the groups
    width=0.35
    max_converge_latency = 0
    mean_latency_per_failure = []

    for i, l_val in enumerate(l_values):
        run_result_list_imp= [] # per impacted clusters only
        run_result_list_all = [] # per all clusters in dcn
        per_run_affected_clusters = []
        for run_id in range(num_runs):
            filename_scheduled = 'adaptive_k2_' + distribution + '_' + col_name_extension + metric_scheduled + str(load) + '_r' + str(run_id) + '.csv'
            filename_missed = 'adaptive_k2_' + distribution + '_' + col_name_extension + metric_missed + str(load) + '_r' + str(run_id) + '.csv'
            filename_conv_latency = 'adaptive_k2_' + distribution + '_' + col_name_extension + metric_conv_latency + str(load) + '_r' + str(run_id) + '.csv'
            result_scheduled = np.genfromtxt(result_dir + "/result_failure_spine_l" + str(l_val) + "/" + filename_scheduled, delimiter=',')
            result_missed = np.genfromtxt(result_dir + "/result_failure_spine_l" + str(l_val) + "/" + filename_missed, delimiter=',')
            result_conv_latency = np.genfromtxt(result_dir + "/result_failure_spine_l" + str(l_val) + "/" + filename_conv_latency, delimiter=',')
            result_conv_latency += FAILURE_DETECTION_LATENCY
            conv_latency = result_conv_latency.max()
            max_converge_latency = max(conv_latency, max_converge_latency)
            mean_latency_per_failure.append(result_conv_latency.mean())
            
            per_run_affected_clusters.append(result_missed.size)

            run_result_list_imp.append(100*(np.sum(result_missed)/ (np.sum(result_missed + np.sum(result_scheduled)))))
            run_result_list_all.append(100*(np.sum(result_missed)/ ((conv_latency) * total_workers * (1/mean_task_time) * 1e-3)))
        y_axis_imp.append(np.mean(run_result_list_imp))
        y_axis_all.append(np.mean(run_result_list_all))
        y_err_imp.append(np.std(run_result_list_imp))
        y_err_all.append(np.std(run_result_list_all))
        print("Selection parameter (ratio): " + str(l_val))
        print ("Per-cluster failure (%): " + str(y_axis_imp[i]))
        print ("Total failure (%): " + str(y_axis_all[i]))
        print("Mean affected cluster per failure: " + str(np.mean(per_run_affected_clusters)))
        print("Max affected cluster per failure: " + str(np.max(per_run_affected_clusters)))
    
    print ("Maximum converge_latency: " + str(max_converge_latency))
    print ("Mean converge_latency: " + str(np.mean(mean_latency_per_failure)))
    #ax.yaxis.set_major_formatter(OOMFormatter(1, "%d"))
    ax.bar(ind, y_axis_all, yerr=y_err_all, width=width, color=color_pallete[1], error_kw=dict(lw=DEFAULT_LINE_WIDTH, capsize=DEFAULT_LINE_WIDTH, capthick=DEFAULT_LINE_WIDTH/4))
    ax.set_ylabel('Total Aborted Tasks (%)', color=color_pallete[1], fontsize=AXIS_SMALL_FONT_SIZE-2)
    ax.set_xticks(ind + width/2)
    ax.set_xticklabels(l_value_lables)
    ax.set_xlabel('Leaf/Spine Scheduler Ratio')
    ax.set_ylim(ymin=0)
    ax.set_yticks([0.05, 0.1, 0.15, 0.2])
    #ax.ticklabel_format(axis="y", style="sci")
    
    
    ax.spines['top'].set_visible(False)
    
    ax2=ax.twinx()
    #ax2.yaxis.set_major_formatter(OOMFormatter(1, "%1.1f"))
    ax2.bar(ind+width, y_axis_imp, yerr=y_err_imp, width=width, color=color_pallete[4], error_kw=dict(lw=DEFAULT_LINE_WIDTH, capsize=DEFAULT_LINE_WIDTH, capthick=DEFAULT_LINE_WIDTH/4))
    ax2.set_ylabel("Per-App Aborted Tasks (%)",color=color_pallete[4], fontsize=AXIS_SMALL_FONT_SIZE-2)
    ax2.set_ylim(ymin=0)
    ax2.set_yticks([10, 20, 30, 40])
    ax2.spines['top'].set_visible(False)
    # ax.bar(ind, y_axis_all, yerr=y_err_all, width=width, color=color_pallete[1], error_kw=dict(lw=DEFAULT_LINE_WIDTH, capsize=DEFAULT_LINE_WIDTH, capthick=DEFAULT_LINE_WIDTH/4))
    # ax.set_ylabel('Aborted Tasks (%)', color='black', fontsize=AXIS_SMALL_FONT_SIZE)
    # ax.set_xticks(ind )
    # ax.set_xticklabels(l_value_lables)
    # ax.set_xlabel('Leaf/Spine Scheduler Ratio')
    # ax.set_ylim(ymin=0)
    # ax.spines['top'].set_visible(False)
    # ax.spines['right'].set_visible(False)
    #ax2.spines['top'].set_visible(False)
    #ax.set_xticklabels(l_value_lables)
    
    ax.grid(True, which="both", ls="--", alpha=0.5)
    if layer == 'spine':
        output_name = distribution + '_miss_percentage_bar'
    
    plt.tight_layout()
    plt.savefig(result_dir + plot_subdir + output_name + '.png', ext='png', bbox_inches="tight")
    plt.savefig(result_dir + plot_subdir + output_name + '.pdf', ext='pdf', bbox_inches='tight')
    plt.show()

def plot_load_imb_workers(policies, metric, distribution, cluster_size_range, percentile=0.0, run_id=0, inc_racksched=0, is_colocate=False, name_tag='', logarithmic=False):
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)

    x_axis = [load*100 for load in loads] 
    cluster_id_list,_ = get_clusters_within_range(cluster_size_range, is_colocate)
    # if is_colocate:
    #     col_name_extension = 'col_'
    # else:
    col_name_extension = ''
    #print("Plotting %s for %d clusters with size in range [%d, %d]" %(metric, len(cluster_id_list), cluster_size_range[0], cluster_size_range[-1]))
    use_sci = False
    fig, ax = plt.subplots()
    points_to_aggregate = np.array(list(cluster_id_list.keys()))
    #print (cluster_id_list)
    max_y = 0
    min_y = 1000000
    for i, policy in enumerate(policies):
        # if policy == 'racksched_partitioned_k2' or policy == 'adaptive_k2':
        #     TICKS_PER_US = 1
        # else:
        #     TICKS_PER_US = 1000
        #TICKS_PER_US = 1000
        if percentile == 0: 
            output_tag = '_mean_'
        else:
            output_tag = '_p' + str(percentile) + '_'
        y_axis = []
        y_err = []
        max_resp_time = 0
        for load in loads:
            if policy == 'sparrow' and percentile==99:
                y_axis = [resp_ms * 1000 for resp_ms in sparrow_resp_time_p99]
                y_err = [0] * len(loads)
                break
            filename_workers = str(policy) + '_' + distribution + output_tag + col_name_extension + 'load_imb_workers_' + str(load) + '_r' + str(run_id) +'.csv'    
            filename_tors = str(policy) + '_' + distribution + output_tag + col_name_extension + 'load_imb_tors_' + str(load) + '_r' + str(run_id) +'.csv'
            filename_intra_rack = str(policy) + '_' + distribution + output_tag + col_name_extension + 'intra_rack_load_imb_max_' + str(load) + '_r' + str(run_id) +'.csv'
            #intra_rack_max = 
            if (load < 1):
                if metric == 'workers':
                    if os.stat(result_dir + analysis_subdir + filename_workers).st_size <= 1:
                        result = np.array([1,1,1,1,1]) 
                    else: 
                        result = np.genfromtxt(result_dir + analysis_subdir + filename_workers, delimiter=',')
                elif metric == 'tors':
                    if os.stat(result_dir + analysis_subdir + filename_tors).st_size <= 1:
                        result = np.array([1,1,1,1,1]) 
                    else: 
                        result = np.genfromtxt(result_dir + analysis_subdir + filename_tors, delimiter=',')
                elif metric == 'intra_rack':
                    result = np.genfromtxt(result_dir + analysis_subdir + filename_intra_rack, delimiter=',')
                result = np.nan_to_num(result, nan=1.0) # No load imbalance is equal to val 1 (max_load was = avg load)
                result[result == 0] = 1
                #result = result[points_to_aggregate]
            else:
                result = np.array([10000000])

            #print(metric + " Policy: " + str(algorithm_names[i])+ " load: " + str(load) + " max: " + str(max(latency)) + " cluster ID: " + str(np.where(latency == max(latency))))
            #latency = latency[:-1] # Last element is comulative clusters percentile
            
            
            #print("Policy: " + str(algorithm_names[i])+ " load: " + str(load) + " Mean: " + str(np.mean(latency)) + " STD: " + str(np.std(latency)))
            if percentile != 0:
                y_axis.append(np.mean((result -1)*100 ))
            else:
                y_axis.append(np.mean((result -1)*100 ))

            #y_err.append(np.std(latency / TICKS_PER_US))
            y_err.append(0)
            if y_axis[-1] > 1000:
                use_sci = True
        
        if policy == 'adaptive_k2':
            max_y = max(max_y, max(y_axis))
        min_y = min(min_y, min(y_axis))
        print("\nPolicy: " + str(policy))
        print(y_axis)
        _, caps, bars = plt.errorbar(x_axis, y_axis, linestyle='--', yerr=y_err, linewidth=ALTERNATIVE_LINE_WIDTH, markersize=16, marker=markers[i], color=color_pallete[i], label=algorithm_names[i], elinewidth=4, capsize=4, capthick=1, zorder=4-i)
        [bar.set_alpha(0.3) for bar in bars]
        [cap.set_alpha(0.3) for cap in caps]
    ax.set_xlabel('Load (%)')
    #print(policy)
    plt.rcParams['legend.handlelength'] = 0.1
    plt.rcParams['legend.numpoints'] = 1
    handles, labels = ax.get_legend_handles_labels()
    # remove the errorbars
    handles = [h[0] for h in handles]
    plt.legend(handles, labels, handletextpad=0.3, borderpad=0.4)
    
    plt.grid(True)
    # x_ticks = []
    # for x_point in x_axis:
    #     if x_point != 99: 
    #         x_ticks.append(x_point)
    # ax.set_xticks(x_ticks)
    # if (percentile <= 50):
    #     ax.set_ylim(0, 1300)
    # elif (percentile > 75):
    #     ax.set_ylim(0, 8000)
    #ax.set_ylim(0.9*min_y, 2*max_y)

    #ax.yaxis.set_major_formatter(OOMFormatter(3, "%d"))
    #ax.ticklabel_format(axis='y', style='sci', scilimits=(3,3))

    

    if percentile == 0:
        stat_label = ''
    else:
        stat_label = str(percentile) + '% '
    if metric == 'transfer_times':
            text_label = 'Scheduling Time'
    elif metric == 'workers':
        text_label = 'Queue Imbalance (%)'
    else:
        text_label = 'Response Time'

    ax.set_ylabel(stat_label+ text_label)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    
    if use_sci:
        plt.ticklabel_format(axis="y", style="sci", scilimits=(0,0))
    if logarithmic:
        ax.set_yscale('log')
    else:
        ax.set_ylim(0)

    ax.set_xticks([0, 25, 50, 75, 99])
    if percentile == 0:
        #'_inc_rsched_'
        output_name =  distribution + '_' +col_name_extension+ metric + '_avg_r' +str(run_id)
        #plt.title(text_label + ' Mean')
    else:
        output_name = distribution + '_'  + col_name_extension+ metric + '_' + str(percentile) + '_r' +str(run_id) 
    if inc_racksched:
        output_name += '_inc_rsched'
    plt.tight_layout()
    plt.savefig(result_dir + plot_subdir + output_name + name_tag +'.png', ext='png', bbox_inches="tight")
    plt.savefig(result_dir + plot_subdir + output_name + name_tag +'.pdf', ext='pdf', bbox_inches='tight')
    #plt.show(fig)

def hextofloats(h):
    '''Takes a hex rgb string (e.g. #ffffff) and returns an RGB tuple (float, float, float).'''
    return [int(h[i:i + 2], 16) / 255. for i in (1, 3, 5)] # skip '#'

def plot_latency_vs_net_condition_box(policies, net_condition, distribution, var_list, loads=[0.9],  percentile=0.0, run_id=0, is_colocate=False, param='size'):
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)
    x_axis = np.array(var_list)
    p_list = [1, 25, 50, 75, 99]
    medianprops = dict(linestyle='-', linewidth=2.5, color='black')
    width = np.max(x_axis) / (len(policies)*len(x_axis) + 2)       # the width of the bars
    #metric_spine = 'msg_per_sec_spine'
    if percentile == 0: 
        output_tag = '_mean_'
    else:
        output_tag = '_p' + str(percentile) + '_'
    max_seen = 0
    for load in loads:
        y_use_sci = False
        pos = -5
        fig, ax = plt.subplots()
        for var_idx, var in enumerate(var_list):
            if var_idx%2 == 1:
                plt.axvspan(pos-6, pos+6, color='gray', alpha=0.08)
            y_axis = []
            y_err = []
            yerr_low = []
            yerr_high = []
            metric_values = []
            for i, policy in enumerate(policies):
                rgb = hextofloats(STYLES[algorithm_names[i]]['color'])

                if net_condition == 'loss':
                    condition_tag = f'l{var}_d5'
                elif net_condition == 'latency':
                    condition_tag = f'l1e-05_d{var}'
                    if policy == 'random_racksched_k2':
                        condition_tag = f'l1e-05_d{var}'
                filename = str(policy) + '_' + condition_tag + '_' + distribution + output_tag + 'response_times_' + str(load) + '_r' + str(run_id) +'.csv'
                values = np.genfromtxt(result_dir + analysis_subdir + filename, delimiter=',')
                values = values / TICKS_PER_US
                # print(filename)
                # print(np.median(values))
                #values = values[np.nonzero(values)]
                # if percentile == 0:
                #     y_value = np.mean(values)
                # else:
                #     y_value = np.percentile(values, percentile)
                
                # y_axis.append(y_value * 1000)

                boxprops = dict(linestyle='-', facecolor=(rgb[0],rgb[1],rgb[2], 1.0), linewidth=SMALL_LINE_WIDTH*scale_med)
                whiskerprops = dict(linestyle='-', linewidth=SMALL_LINE_WIDTH *scale_med)
                capprops = dict(linestyle='-', linewidth=SMALL_LINE_WIDTH*scale_med)
                flierprops=dict(linestyle='-', linewidth=SMALL_LINE_WIDTH*scale_med)
                max_seen = max(np.percentile(values, 90), max_seen)
                ax.bxp([{
                        'label' : str(int(load*100)),
                        'whislo': np.percentile(values, 10),    # Bottom whisker position
                        'q1'    : np.percentile(values, 25),    # First quartile (25th percentile)
                        'med'   : np.percentile(values, 50),    # Median         (50th percentile)
                        'q3'    : np.percentile(values, 75),    # Third quartile (75th percentile)
                        'whishi': np.percentile(values, 90),    # Top whisker position
                        'fliers': []        # Outliers
                    }], 
                    patch_artist=True,
                    boxprops=boxprops, 
                    medianprops=medianprops,
                    showfliers=False,
                    whiskerprops=whiskerprops,
                    capprops=capprops,
                    flierprops=flierprops,
                    positions=[pos], 
                    widths = 4.4
                    )
                pos += 7
            pos += 4.5

        #ax.set_xticks(np.linspace(x_axis[0], x_axis[-1], num=len(x_axis)) + width/len(policies))
    
        if net_condition == 'loss':
            ax.set_xlabel('Loss Rate (%)')
            ax.set_xticklabels([x*100 for x in x_axis])
        elif net_condition == 'latency':
            ax.set_xlabel(f'Per-Hop Delay' + '(%ss)' % r'$\mu$')
            ax.set_xticklabels(x_axis)
        if y_use_sci:
            plt.ticklabel_format(axis="y", style="sci", scilimits=(0,0))

        ax.tick_params(axis='both', which='major')
        ax.grid(True, which="both",axis='y', ls="--", alpha=0.6)
        custom_lines = []
        for i in range(len(policies)):
            custom_lines.append(Line2D([0], [0], color=STYLES[algorithm_names[i]]['color'], lw=DEFAULT_LINE_WIDTH*scale_big, linestyle='--'))
        leg = ax.legend(custom_lines, algorithm_names, ncol=3, handlelength=0.6, borderpad=0.06, borderaxespad=0.0, labelspacing=0.0, columnspacing=0.6, frameon=True, loc='upper center')
        bb = leg.get_bbox_to_anchor().inverse_transformed(ax.transAxes)
        bb.x0 += 0.02
        bb.x1 += 0.02
        bb.y0 += 0.14
        bb.y1 += 0.14
        leg.set_bbox_to_anchor(bb, transform = ax.transAxes)

        if net_condition == 'latency':
            loc = ticker.MaxNLocator(min_n_ticks=3, nbins=4) # this locator puts ticks at regular intervals
            ax.yaxis.set_major_locator(loc)
        #ax.set_ylim(0, ylim)
        
        if percentile == 0:
            stat_label = 'Avg. '
        else:
            stat_label = str(percentile) + '% '

        
        text_label = 'Resp. Time'
        #ax.set_xscale("log")

        ax.set_ylabel(stat_label + text_label + ' (%ss)' % r'$\mu$')
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        
        # if max_seen > 20000:
        #     ax.set_ylim(0, 20000)
        if net_condition == 'latency':
            if load > 0.5:
                ax.yaxis.set_major_formatter(OOMFormatter(3, "%d"))
            else:
                ax.yaxis.set_major_formatter(OOMFormatter(3, "%.1f"))
        else:
            if load == 0.5:
                ax.yaxis.set_major_formatter(OOMFormatter(2, "%.1f"))
            else:
                ax.yaxis.set_major_formatter(OOMFormatter(3, "%.1f"))

        ax.ticklabel_format(axis='y', style='sci', scilimits=(0,3))
        #ax.set_xticks(ticks)
        if percentile == 0:
            output_name =  distribution + '_response_times_vs_' + net_condition  + '_l' +  str(load) + '_box_' +'_avg_' 
            #plt.title(text_label + ' Mean')
        else:
            output_name = distribution + '_response_times_vs_' + net_condition +  '_l' +  str(load) + '_box_' + str(percentile) 
            #plt.title(text_label + ' ' + str(percentile) + 'th percentile')
        plt.tight_layout()
        plt.savefig(result_dir + plot_subdir + output_name + '.png', ext='png', bbox_inches="tight")
        plt.savefig(result_dir + plot_subdir + output_name + '.pdf', ext='pdf', bbox_inches='tight')

def plot_msg_rate_vs_net_condition_box(policies, net_condition, distribution, var_list, loads=[0.9],  percentile=0.0, run_id=0, is_colocate=False, param='size'):
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=1., handletextpad=0.25)
    x_axis = np.array(var_list)
    p_list = [1, 25, 50, 75, 99]
    medianprops = dict(linestyle='-', linewidth=2.5, color='black')
    width = np.max(x_axis) / (len(policies)*len(x_axis) + 2)       # the width of the bars
    if percentile == 0: 
        output_tag = '_mean_'
    else:
        output_tag = '_p' + str(percentile) + '_'
    max_seen = 0
    for load in loads:
        y_use_sci = False
        pos = -5
        fig, ax = plt.subplots()
        for var_idx, var in enumerate(var_list):
            if var_idx%2 == 1:
                plt.axvspan(pos-6, pos+6, color='gray', alpha=0.08)
            y_axis = []
            y_err = []
            yerr_low = []
            yerr_high = []
            metric_values = []
            for i, policy in enumerate(policies):
                rgb = hextofloats(STYLES[algorithm_names[i]]['color'])

                if net_condition == 'loss':
                    condition_tag = f'l{var}_d5'
                elif net_condition == 'latency':
                    condition_tag = f'l0.0_d{var}'
                    if policy == 'random_racksched_k2':
                        condition_tag = f'l1e-05_d{var}'
                filename = str(policy) + '_' + condition_tag + '_' + distribution + '_msg_per_sec_spine_'  + str(load) + '_r' + str(run_id) +  '.csv'
                values = np.genfromtxt(result_dir + analysis_subdir + filename, delimiter=',')
                values = values[np.nonzero(values)]
                values *= 20
                boxprops = dict(linestyle='-', facecolor=(rgb[0],rgb[1],rgb[2], 1.0), linewidth=SMALL_LINE_WIDTH-0.5)
                whiskerprops = dict(linestyle='-', linewidth=SMALL_LINE_WIDTH-0.5)
                capprops = dict(linestyle='-', linewidth=SMALL_LINE_WIDTH-0.5)
                flierprops=dict(linestyle='-', linewidth=SMALL_LINE_WIDTH-0.5)
                max_seen = max(np.percentile(values, 90), max_seen)
                ax.bxp([{
                        'label' : str(int(load*100)),
                        'whislo': np.percentile(values, 10),    # Bottom whisker position
                        'q1'    : np.percentile(values, 25),    # First quartile (25th percentile)
                        'med'   : np.percentile(values, 50),    # Median         (50th percentile)
                        'q3'    : np.percentile(values, 75),    # Third quartile (75th percentile)
                        'whishi': np.percentile(values, 90),    # Top whisker position
                        'fliers': []        # Outliers
                    }], 
                    patch_artist=True,
                    boxprops=boxprops, 
                    medianprops=medianprops,
                    showfliers=False,
                    whiskerprops=whiskerprops,
                    capprops=capprops,
                    flierprops=flierprops,
                    positions=[pos], 
                    widths = 4
                    )
                pos += 7
            pos += 4.5

        #ax.set_xticks(np.linspace(x_axis[0], x_axis[-1], num=len(x_axis)) + width/len(policies))
    
        if net_condition == 'loss':
            ax.set_xlabel('Loss Rate (%)', fontsize=AXIS_SMALL_FONT_SIZE)
            ax.set_xticklabels([x*100 for x in x_axis])
        elif net_condition == 'latency':
            ax.set_xlabel(f'Per-Hop Delay' + '(%ss)' % r'$\mu$', fontsize=AXIS_SMALL_FONT_SIZE)
            ax.set_xticklabels(x_axis)
        

        ax.tick_params(axis='both', which='major', labelsize=AUTLABEL_FONT_SIZE)
        ax.grid(True, which="both",axis='y', ls="--", alpha=0.6)
        custom_lines = []
        for i in range(len(policies)):
            custom_lines.append(Line2D([0], [0], color=STYLES[algorithm_names[i]]['color'], lw=DEFAULT_LINE_WIDTH))
        leg = ax.legend(custom_lines, algorithm_names, ncol=3, handlelength=0.2, borderpad=0.13, labelspacing=0.0, columnspacing=1, loc='upper center')
        bb = leg.get_bbox_to_anchor().inverse_transformed(ax.transAxes)
        bb.y0 += 0.19
        bb.y1 += 0.19
        leg.set_bbox_to_anchor(bb, transform = ax.transAxes)

        #ax.set_ylim(0, ylim)
        
        text_label = '#Msgs/s'
        #ax.set_xscale("log")

        ax.set_ylabel(text_label)
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        
        # if max_seen > 20000:
        #     ax.set_ylim(0, 20000)
        ax.yaxis.set_major_formatter(OOMFormatter(7, "%.1f"))
        ax.ticklabel_format(axis='y', style='sci', scilimits=(0,5))
        #ax.set_xticks(ticks)
        if percentile == 0:
            output_name =  distribution + '_msg_rate_vs_' + net_condition  + '_l' +  str(load) + '_box_' +'_avg_' 
            #plt.title(text_label + ' Mean')
        else:
            output_name = distribution + '_msg_rate_vs_' + net_condition +  '_l' +  str(load) + '_box_' + str(percentile) 
            #plt.title(text_label + ' ' + str(percentile) + 'th percentile')
        plt.tight_layout()
        plt.savefig(result_dir + plot_subdir + output_name + '.png', ext='png', bbox_inches="tight")
        plt.savefig(result_dir + plot_subdir + output_name + '.pdf', ext='pdf', bbox_inches='tight')

def plot_box_load_imb(policies, metric, distribution, cluster_size_range, run_id=0, inc_racksched=0, is_colocate=False, name_tag='', logarithmic=False):
    sns.set_context(context='paper', rc=DEFAULT_RC)
    plt.rc('font', **FONT_DICT)
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('pdf', **{'fonttype': 42})
    plt.rc('mathtext', **{'default': 'regular'})
    plt.rc('ps', **{'fonttype': 42})
    plt.rc('legend', handlelength=.5, handletextpad=0.25)

    #x_axis = [load*100 for load in loads] 
    loads = [0.5, 0.7, 0.9]
    p_list = [1, 25, 50, 75, 99]
    cluster_id_list,_ = get_clusters_within_range(cluster_size_range, is_colocate)
    # if is_colocate:
    #     col_name_extension = 'col_'
    # else:
    col_name_extension = ''
    #print("Plotting %s for %d clusters with size in range [%d, %d]" %(metric, len(cluster_id_list), cluster_size_range[0], cluster_size_range[-1]))
    use_sci = False
    fig, ax = plt.subplots()
    points_to_aggregate = np.array(list(cluster_id_list.keys()))
    #print (cluster_id_list)
    max_y = 0
    min_y = 1000000
    boxes = []
    box_props = []
    medianprops = dict(linestyle='-', linewidth=2.5, color='black')
    pos = 0
    for load_idx, load in enumerate(loads):
        y_axis = []
        y_err = []
        max_resp_time = 0
        if load_idx%2 == 1:
            plt.axvspan(pos-0.26, pos+0.87, color='gray', alpha=0.10)
        for i, policy in enumerate(policies):
            box_res = []
            for percentile in p_list:
                if percentile == 0: 
                    output_tag = '_mean_'
                else:
                    output_tag = '_p' + str(percentile) + '_'
                filename_workers = str(policy) + '_' + distribution + output_tag + col_name_extension + 'load_imb_workers_' + str(load) + '_r' + str(run_id) +'.csv'    
                filename_tors = str(policy) + '_' + distribution + output_tag + col_name_extension + 'load_imb_tors_' + str(load) + '_r' + str(run_id) +'.csv'
                filename_intra_rack = str(policy) + '_' + distribution + output_tag + col_name_extension + 'intra_rack_load_imb_max_' + str(load) + '_r' + str(run_id) +'.csv'
                #intra_rack_max = 
                if (load < 1):
                    if metric == 'workers':
                        if os.stat(result_dir + analysis_subdir + filename_workers).st_size <= 1:
                            result = np.array([1,1,1,1,1]) 
                        else: 
                            result = np.genfromtxt(result_dir + analysis_subdir + filename_workers, delimiter=',')
                    elif metric == 'tors':
                        if os.stat(result_dir + analysis_subdir + filename_tors).st_size <= 1:
                            result = np.array([1,1,1,1,1]) 
                        else: 
                            result = np.genfromtxt(result_dir + analysis_subdir + filename_tors, delimiter=',')
                    elif metric == 'intra_rack':
                        result = np.genfromtxt(result_dir + analysis_subdir + filename_intra_rack, delimiter=',')
                    if len(result) == 0:
                        result = np.array([1,1,1,1,1]) 
                    result = np.nan_to_num(result, nan=1.0) # No load imbalance is equal to val 1 (max_load was = avg load)
                    #result[result == 0] = 1
                    #result = result[points_to_aggregate]
                else:
                    result = np.array([10000000])
                print(filename_workers)
                box_res.append(np.median((result)))
                print(np.median(result))
            rgb = hextofloats(STYLES[algorithm_names[i]]['color'])
            boxprops = dict(linestyle='-', facecolor=(rgb[0],rgb[1],rgb[2], 0.85), linewidth=SMALL_LINE_WIDTH-0.5)
            whiskerprops = dict(linestyle='-', linewidth=SMALL_LINE_WIDTH-0.5)
            capprops = dict(linestyle='-', linewidth=SMALL_LINE_WIDTH-0.5)
            flierprops=dict(linestyle='-', linewidth=SMALL_LINE_WIDTH-0.5)
            ax.bxp([{
                    'label' : str(int(load*100)),
                    'whislo': (box_res[0] - 1) * 100,    # Bottom whisker position
                    'q1'    : (box_res[1] - 1) * 100,    # First quartile (25th percentile)
                    'med'   : (box_res[2] - 1) * 100,    # Median         (50th percentile)
                    'q3'    : (box_res[3] - 1) * 100,    # Third quartile (75th percentile)
                    'whishi': (box_res[4] - 1) * 80,    # Top whisker position
                    'fliers': []        # Outliers
                }], 
                patch_artist=True,
                boxprops=boxprops, 
                medianprops=medianprops,
                showfliers=False,
                whiskerprops=whiskerprops,
                capprops=capprops,
                flierprops=flierprops,
                positions=[pos], 
                widths = 0.24
                )
            pos += 0.3
        pos += 0.15
    print(boxes)
    ax.grid(True, which="both",axis='y', ls="--", alpha=0.6)
    custom_lines = []
    for i in range(len(policies)):
        custom_lines.append(Line2D([0], [0], color=STYLES[algorithm_names[i]]['color'], lw=DEFAULT_LINE_WIDTH*scale_big, linestyle='--'))
    leg = ax.legend(custom_lines, algorithm_names, ncol=3, handlelength=0.4, borderpad=0.06, borderaxespad=0.0, labelspacing=0.0, columnspacing=0.4, frameon=True, loc='upper center')
    bb = leg.get_bbox_to_anchor().inverse_transformed(ax.transAxes)
    f = leg.get_frame()
    bb.x0 += 0.05
    bb.x1 += 0.05
    bb.y0 += 0.19
    bb.y1 += 0.19
    leg.set_bbox_to_anchor(bb, transform = ax.transAxes)
    # ax.bxp(boxes[:3], boxprops=box_props[0], medianprops=medianprops, showfliers=False, positions=[1, 2, 3])
    # ax.bxp(boxes[3:6], boxprops=box_props[1], medianprops=medianprops, showfliers=False, positions=[4, 5, 6])
    # ax.bxp(boxes[6:9], boxprops=box_props[2], medianprops=medianprops, showfliers=False, positions=[7, 8, 9])
    ax.set_ylabel('Queue Imbalance (%)')
    ax.set_xlabel('Load (%)')
    ax.yaxis.get_offset_text().set_fontsize(TICK_FONT_SIZE)
    ax.yaxis.set_major_formatter(OOMFormatter(3, "%.0f"))
    xticks = ax.xaxis.get_major_ticks()
    vis_idx = int(len(policies)/2)
    for i in range(len(xticks)):
        if i == vis_idx:
            xticks[i].set_visible(True)
            vis_idx += len(policies)
        else:
            xticks[i].set_visible(False)
    ax.set_ylim(0, 5000)
    ax.set_xlim(-0.2, pos)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    
    plt.tight_layout()
    
    plt.savefig(result_dir + plot_subdir + 'load_imbalance_box' +'.png', ext='png', bbox_inches="tight")
    plt.savefig(result_dir + plot_subdir + 'load_imbalance_box' +'.pdf', ext='pdf', bbox_inches='tight')

    #plt.show(fig)
    #plt.show(fig)

if __name__ == "__main__":
    arguments = docopt.docopt(__doc__, version='1.0')
    working_dir = arguments['-d']
    # global result_dir
    result_dir = working_dir
    
    if arguments['-k']: # @parham set docopt default value for optional args?
        k = int(arguments['-k'])
    if arguments['-l']:
        ratio = int(arguments['-l'])
    if arguments['--load']:
        load = float(arguments['--load'])
    if arguments['--tag']:
        add_name_tag = arguments['--tag']
    else:
        add_name_tag = ''
    if arguments['-p']:
        policy = arguments['-p']

    task_distribution = arguments['-t']
    inc_racksched = arguments.get('--all', False)
    dissect = arguments.get('--dissect')
    dimpact = arguments.get('--dimpact')
    latency = arguments.get('--latency')
    loss = arguments.get('--loss')
    is_colocate = arguments.get('--colocate', False)

    if inc_racksched:
        policies = ['adaptive_k' + str(k), 'racksched_k2', 'random_racksched_k2']
        algorithm_names = ['Horus', 'RS-H', 'RS-R']
        # policies = ['adaptive_k' + str(k), 'racksched_k2', 'random_racksched_k2', 'jiq_k2']
        # algorithm_names = ['Horus', 'RS-H', 'RS-R', 'Idle Selection']
    else:
        policies = ['adaptive_k' + str(k), 'racksched_k2']
        algorithm_names = ['Horus', 'RS-H']

    if dissect:
        policies = ['adaptive_k2', 'racksched_k2_iu', 'racksched_partitioned_k2', 'jiq_k2']
        algorithm_names = ['Horus', 'Pow-of-2', 'Pow-of-2 (DU)', 'Idle Selection']
        loads = [0.1, 0.3, 0.5, 0.7, 0.9, 0.99]
    
    elif dimpact:
        policies = ['adaptive', 'racksched_iu', 'racksched', 'racksched_k1000000_iu']
        algorithm_names = ['Horus', 'Pow-of-d', 'Pow-of-d (DU)', 'Oracle']
        # policies = ['racksched_k2_iu', 'racksched_k4_iu', 'racksched_k8_iu', 'racksched_k16_iu']
        # algorithm_names = ['Pow-of-d (d=2)', 'Pow-of-d (d=4)', 'Pow-of-d (d=8)', 'Pow-of-d (d=16)']
        
        # policies = ['adaptive_k2', 'adaptive_k4', 'adaptive_k8', 'adaptive_k16', 'racksched_k1000000_iu']
        # algorithm_names = ['Saqr (d=2)', 'Saqr (d=4)', 'Saqr (d=8)', 'Saqr (d=16)', 'Omniscient (JSQ)']
        
        # policies = ['racksched_k2', 'racksched_k4', 'racksched_k8', 'racksched_k16']
        # algorithm_names = ['RS-H (d=2)', 'RS-H (d=4)', 'RS-H (d=8)', 'RS-H (d=16)']
    elif latency:
        policies = ['adaptive_k2', 'racksched_k2']
        algorithm_names = ['Horus', 'RS-H']
        #plot_msg_breakdown_vs_net_condition('adaptive_k2', net_condition='latency', distribution=task_distribution, var_list=[0, 5, 10, 50, 100], loads=[0.5, 0.8, 0.9],  percentile=0)
        plot_latency_vs_net_condition_box(['adaptive_k2'], net_condition='latency', distribution=task_distribution, var_list=[0, 5, 10, 50, 100], loads=[0.5, 0.9],  percentile=99)
        #plot_msg_rate_vs_net_condition(policies = ['adaptive_k2'], net_condition='latency' if latency else 'loss', distribution=task_distribution, var_list=[0, 5, 10, 50, 100], loads=[0.5, 0.7, 0.8, 0.9],  percentile=0)
        #plot_latency_vs_net_condition_box(['adaptive_k2'], net_condition='latency', distribution=task_distribution, var_list=[0, 5, 10, 50, 100], loads=[0.5],  percentile=99)
        #plot_latency_vs_net_condition(policies, net_condition='latency' if latency else 'loss', distribution=task_distribution, var_list=[0, 5, 10, 50, 100], loads=[0.5, 0.7, 0.8, 0.9],  percentile=99)
        exit()
    elif loss:
        policies = ['adaptive_k2', 'racksched_k2']
        algorithm_names = ['Horus', 'RS-H', 'RS-LB']
        plot_msg_breakdown_vs_net_condition('adaptive_k2', net_condition='loss', distribution=task_distribution, var_list=[0.0, 0.0001, 0.001, 0.005, 0.01], loads=[0.5, 0.8, 0.9],  percentile=0)
        #plot_msg_rate_vs_net_condition_box(['adaptive_k2'], net_condition='loss', distribution=task_distribution, var_list=[0.0, 0.0001, 0.001, 0.01], loads=[0.5, 0.8, 0.9],  percentile=0)
        #plot_msg_rate_vs_net_condition(policies = ['adaptive_k2'], net_condition='loss', distribution=task_distribution, var_list=[0.0, 0.0001, 0.001, 0.01, 0.1], loads=[0.5, 0.8, 0.9],  percentile=0)
        #plot_latency_vs_net_condition_box(['adaptive_k2'], net_condition='loss', distribution=task_distribution, var_list=[0.0, 0.0001, 0.001, 0.005, 0.01], loads=[0.5, 0.9],  percentile=99)
        exit()
    # plot_latency_vs_size(policies, range(10, 50), 'wait_times', task_distribution, load=0.99, percentile=99, run_id=0)

    # policies = ['adaptive_k2_l1e-05_d5']
    # algorithm_names = ['Horus']
    #policies = ['adaptive_k2_l1e-05_d5', 'racksched_k2_l1e-05_d5', 'random_racksched_k2_l1e-05_d5']
    #algorithm_names = ['Horus', 'RS-H', 'RS-LB']
    # policies = ['adaptive_k2_l0.0001_d5', 'racksched_k2_l0.0001_d5', 'racksched_k100000_l0.0_d0_iu']
    # algorithm_names = ['Horus', 'RS', 'JSQ']
    #plot_latency(policies, metric='response_times', distribution=task_distribution, percentile=0, cluster_size_range=range(10, 30000), is_colocate=is_colocate)
    # print (cluster_maps)
    # for cluster_id in range(10):
    #     plot_per_cluster_wait_times("bimodal", cluster_id, cluster_maps[cluster_id], percentile=99.99)
    
    #plot_failure_impacted_tors(distribution=task_distribution, num_runs=30, layer='spine', is_colocate=is_colocate)
    # plot_failure_impacted_clients(distribution=task_distribution, num_runs=10,layer='spine', is_colocate=is_colocate)
    #plot_failure_missed_tasks(distribution=task_distribution, num_runs=20,layer='spine', is_colocate=is_colocate)
    #plot_failure_missed_tasks_cdf(distribution=task_distribution, num_runs=30,layer='spine', is_colocate=is_colocate)
    
    # get_clusters_within_range(range(1000,2000), is_colocate)
    #percentile_list = [0]
    #percentile_list = list(range(0, 100, 1)) + [99, 99.99]
    # for policy in policies:
    #     for load in loads:
    #         analyze_latency(policy, load, distribution=task_distribution, percentile_list=percentile_list, run_id=0, is_colocate=is_colocate)
    
    # policies = ['adaptive_k' + str(k), 'sparrow_k' + str(k), 'jiq_k' + str(k)]
    #algorithm_names = ['Adaptive', 'JSQ(d)', 'JIQ']
    
    #plot_latency_vs_param_bar(policies, 'response_times', task_distribution, bucket_size=40, max_param=161, percentile=99, run_id=0, is_colocate=is_colocate, param='var')
    #plot_latency_vs_param_bar(policies, 'wait_times', task_distribution, bucket_size=5000, max_param=20001, percentile=99, run_id=0, is_colocate=is_colocate)
    #plot_latency_vs_net_condition(policies, net_condition='latency' if latency else 'loss', distribution=task_distribution, var_list=[0, 5, 10, 50, 100], loads=[0.5, 0.7, 0.9, 0.99],  percentile=99)
    #plot_latency_vs_net_condition(policies, net_condition='latency' if latency else 'loss', distribution=task_distribution, var_list=[0.0, 0.0001, 0.001, 0.01, 0.1], loads=[0.5, 0.7, 0.9, 0.99],  percentile=99)
    #plot_latency_all(policies, metric='response_times', distribution=task_distribution, percentile=0, cluster_size_range=range(10, 40000), is_colocate=is_colocate)
    #plot_latency(policies, metric='response_times', distribution=task_distribution, percentile=99, cluster_size_range=range(10, 30000), is_colocate=is_colocate)
    # plot_latency(policies, metric='response_times', distribution=task_distribution, percentile=0,
    #             cluster_size_range=range(10, 30000), is_colocate=is_colocate)
    #plot_latency(policies, metric='wait_times', distribution=task_distribution, percentile=99, cluster_size_range=range(10, 30000), is_colocate=is_colocate)
    #plot_latency(policies, metric='wait_times', distribution=task_distribution, percentile=0, cluster_size_range=range(10, 30000), is_colocate=is_colocate)
    #plot_latency(policies, metric='wait_times', distribution=task_distribution, percentile=50, cluster_size_range=range(10, 30000), is_colocate=is_colocate)
    #plot_latency(policies, metric='wait_times', distribution=task_distribution, percentile=90, cluster_size_range=range(10, 30000), is_colocate=is_colocate)
    
    #plot_latency_dimapct(policies, load=load, metric='response_times', distribution=task_distribution, percentile=99, cluster_size_range=range(0, 40000), is_colocate=is_colocate, name_tag= add_name_tag)    
    # plot_latency_cdf(policies, load=0.5, metric='wait_times', distribution=task_distribution,
    #                  cluster_size_range=range(10, 30000), is_colocate=is_colocate)
    # plot_latency_cdf(policies, load=0.9, metric='wait_times', distribution=task_distribution, cluster_size_range=range(10, 30000), is_colocate=is_colocate, name_tag=add_name_tag)
    # plot_latency_cdf(policies, load=0.99, metric='wait_times', distribution=task_distribution, cluster_size_range=range(10, 40000), is_colocate=is_colocate, name_tag=add_name_tag)
    # plot_latency_cdf(policies, load=0.7, metric='wait_times', distribution=task_distribution, cluster_size_range=range(10, 30000), is_colocate=is_colocate)
    # plot_latency_cdf(policies, load=0.99, metric='response_times', distribution=task_distribution, cluster_size_range=range(10, 30000), is_colocate=is_colocate)
    #plot_latency(policies, metric='response_times', distribution=task_distribution, percentile=0, cluster_size_range=range(10, 40000), is_colocate=is_colocate)
    #plot_latency_vs_centralized(policies, metric='wait_times', ratio=ratio, distribution=task_distribution, percentile=99, cluster_size_range=range(0, 100), is_colocate=is_colocate)
    
    #plot_latency(policies, metric='response_times', distribution=task_distribution, percentile=99, cluster_size_range=range(0, 40000), is_colocate=is_colocate, name_tag= add_name_tag)
    #plot_latency(policies, metric='response_times', distribution=task_distribution, percentile=0, cluster_size_range=range(0, 40000), is_colocate=is_colocate, name_tag=add_name_tag)
    #plot_load_imb_workers(policies, metric='workers', distribution=task_distribution, percentile=0, cluster_size_range=range(0, 40000), is_colocate=is_colocate, name_tag=add_name_tag, logarithmic=True)
    #plot_load_imb_workers(policies, metric='workers', distribution=task_distribution, percentile=0, cluster_size_range=range(0, 40000), is_colocate=is_colocate, name_tag=add_name_tag, logarithmic=True)
    #plot_box_load_imb(policies, metric='workers', distribution=task_distribution, cluster_size_range=range(0, 40000), is_colocate=is_colocate, name_tag=add_name_tag, logarithmic=False)
    #plot_latency(policies, metric='response_times', distribution=task_distribution, percentile=99, cluster_size_range=range(10, 40000), is_colocate=is_colocate)
    #plot_latency(policies, metric='response_times', distribution=task_distribution, percentile=90, cluster_size_range=range(10, 40000), is_colocate=is_colocate)
    #plot_latency(policies, metric='response_times', distribution=task_distribution, percentile=0, cluster_size_range=range(10, 40000), is_colocate=is_colocate)
    #plot_latency(policies, metric='wait_times', distribution=task_distribution, percentile=50, cluster_size_range=range(10, 40000), is_colocate=is_colocate)
    #plot_latency(policies, metric='wait_times', distribution=task_distribution, percentile=0, cluster_size_range=range(10, 40000), is_colocate=is_colocate)
    #exit(0)
   
    #plot_latency_vs_ratio(policies, k, metric='response_times', distribution=task_distribution, percentile=99, load=0.99)
    #plot_latency_vs_ratio(policies, k, metric='wait_times', distribution="bimodal", percentile=50, load=0.99)
    plot_msg_breakdown('adaptive_k2_l1e-05_d5', distribution=task_distribution, percentile=0, metric="msg", layer='spine',is_colocate=is_colocate, sum_layer=False)
    #plot_switch_packet_rate(policies, distribution=task_distribution, percentile=99.99, metric="msg", layer='spine',is_colocate=is_colocate, sum_layer=False)
    #plot_switch_packet_rate(policies, distribution=task_distribution, percentile=99.99, metric="msg", layer='spine',is_colocate=is_colocate)
    # plot_switch_packet_rate(policies, distribution=task_distribution, percentile=0, metric="msg", layer='spine',is_colocate=is_colocate)
    #plot_switch_packet_rate(policies, distribution=task_distribution, percentile=99, metric="msg", layer='tor', is_colocate=is_colocate)
    #plot_switch_packet_rate(policies, distribution=task_distribution, percentile=50, metric="msg", layer='spine', is_colocate=is_colocate)
    #plot_switch_packet_rate(policies, distribution=task_distribution, percentile=50, metric="msg", layer='tor', is_colocate=is_colocate)
    #plot_switch_packet_rate(policies, distribution=task_distribution, percentile=0, metric="msg", layer='tor', is_colocate=is_colocate)
    #plot_switch_packet_rate(policies, distribution=task_distribution, percentile=0, metric="msg", layer='spine', is_colocate=is_colocate)
    #plot_switch_packet_rate_ratios(result_dir, policies, distribution=task_distribution, percentile=90, metric="msg", layer='spine',is_colocate=is_colocate, sum_layer=False)

