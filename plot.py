#!/usr/bin/env python
"""fio-multiplexer plot tool

Usage: ./run.py <-1|--first=<first_results_folder>> -2|--second=<second_results_folder> [[-c|--config=] <config.ini>] [-h|--help]
    -1|--first           first set of results
    -2|--second          second set of results
    -c|--config         configuration file that will be used as base for
                        fio tool
    -h|--help            displays this help message
"""
import matplotlib.pyplot as plt
import numpy as np
import csv, sys
import ConfigParser
import getopt
import datetime
import os
import shutil

timestamp=datetime.datetime.now().strftime("%Y%m%d%H%M%S")

config_file = None
test_cases = []
global_options = {}
bss = []
iodepths = []
ordered_result0 = []
ordered_result1 = []
graphs_folder_name = None

# print information back to user depending on how much verbosity is set
# info_type can be:
#   I: Info
#   W: Warning
#   E: Error
#   V: Verbose
def print_verbose(info_type, string):
    # TODO: add logic to add more information depending on verbosity config
    print "[%s] %s" % (info_type, string)

def parse_config(config_file):
    # open config.ini, grab all global options and transform the list of block
    # sizes and iodepths into interable arrays
    c = ConfigParser.RawConfigParser(allow_no_value=True)
    c.read(config_file)
    s = c.sections()[0]
    o = c.options(s)
    for opt in o:
        value = c.get(s, opt)
        global_options[opt] = value
    bss = global_options['bs'].split(' ')
    iodepths = global_options['iodepth'].split(' ')

    # generate all possible test_cases from template.ini
    for bs in bss:
        for iodepth in iodepths:
            if ( global_options['rw'] == "rw" or
                    global_options['rw'] == "randrw"):
                test_cases.append("B%sI%sR" % (bs, iodepth))
                test_cases.append("B%sI%sW" % (bs, iodepth))

            elif (global_options['rw'] == "read" or
                    global_options['rw'] == "randread"):
                test_cases.append("B%sI%sR" % (bs, iodepth))
            elif (global_options['rw'] == "write" or
                    global_options['rw'] == "randwrite"):
                test_cases.append("B%sI%sW" % (bs, iodepth))

def do_graph(results_file0, results_file1, label):
    global config_file
    global test_cases
    global global_options
    global bss
    global iodepths
    ordered_result0 = []
    ordered_result1 = []

    print_verbose("I", "drawing graphs for %s" % label)

    # open and read both csv result files
    reader = csv.reader(open(results_file0, 'rb'))
    results0 = dict(x for x in reader)
    reader = csv.reader(open(results_file1, 'rb'))
    results1 = dict(x for x in reader)

    # remove '[' and ']' from results and append to results Array
    for test_case in test_cases:
        value0 = results0[test_case].replace("[", "")
        value0 = value0.replace("]", "")
        value1 = results1[test_case].replace("[", "")
        value1 = value1.replace("]", "")
        ordered_result0.append(int(value0))
        ordered_result1.append(int(value1))

    # graph stuff
    N = len(test_cases)
    ind = np.arange(N)
    width = 0.35
    fig, ax = plt.subplots()

    rects1 = ax.bar(ind, tuple(ordered_result0), width, color='b')
    rects2 = ax.bar(ind+width, tuple(ordered_result1), width, color='r')

    ax.set_ylabel(label)
    #ax.set_title('configuration')
    ax.set_xticks(ind+width)
    ax.set_xticklabels(tuple(test_cases), rotation='vertical')

    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.text(rect.get_x()+rect.get_width()/2., 1.05*height, '%d'%int(height),
                    ha='center', va='bottom', rotation='vertical')

    autolabel(rects1)
    autolabel(rects2)
    plt.savefig("%s/%s.png" % (graphs_folder_name, label))
    #plt.show()

def main():
    # parse command line options
    global template_file
    global vms_file
    global vms
    global config_file
    global graphs_folder_name

    try:
        opts, args = getopt.getopt(sys.argv[1:], "h1:2:c:", ["help", "first=",
            "second=", "config="])
    except getopt.error, msg:
        print msg
        print __doc__
        return 2

    # process options
    if len(opts) < 2:
        print "not enough arguments"
        print "for help use --help"
        return 2

    for o, a in opts:
        if o in ("-h", "--help"):
            print __doc__
            return 0
        elif o in ("-1", "--first"):
            folder0=a
        elif o in ("-2", "--second"):
            folder1=a
        elif o in ("-c", "--config"):
            config_file=a

    #if nothing is set, go back to default
    if config_file == None:
        print_verbose("I", "No configuration given, using default config.ini")
        config_file = "config.ini"

    parse_config(config_file)

    graphs_folder_name = "logs/%s__%s" % (folder0.replace("logs/", ""),
            folder1.replace("logs/", ""))
    shutil.rmtree(graphs_folder_name, ignore_errors=True)
    os.mkdir(graphs_folder_name)

    do_graph("%s/iops.csv" % folder0, "%s/iops.csv" % folder1, "iops")
    do_graph("%s/bw.csv" % folder0, "%s/bw.csv" % folder1, "bw")
    do_graph("%s/cpu.csv" % folder0, "%s/cpu.csv" % folder1, "cpu")
    do_graph("%s/lat.csv" % folder0, "%s/lat.csv" % folder1, "lat")

    return 0

if __name__ == "__main__":
    sys.exit(main())
