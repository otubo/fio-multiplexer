#!/usr/bin/python
import subprocess
import sys
import re
import string
import ConfigParser
import os, shutil
import random, math
import csv
from collections import OrderedDict
import datetime

if len(sys.argv) != 3:
    print "usage: " + str(sys.argv[0]) + " <nruns> <template.ini>"
    sys.exit(1)

nruns = int(sys.argv[1])
config_file = str(sys.argv[2])

timestamp=datetime.datetime.now().strftime("%Y%m%d%H%M")

#
# global variables
x = 0
# dictionary that is in the format:
#   {'config_name': [list, of, results]}
results=OrderedDict()
# dictionary that is in the format:
#   {'config_name': 'average for this config'}
average_results=OrderedDict()
# dictionary that holds all global options defined in the [global] section of
# the template.ini file.
global_options = {}
# all the different filenames for each configuration generated
filenames=[]

# just a simple function to replace this:
#    key = value
# by this:
#    key=value
def remove_whitespace_from_assignments(config_path):
    separator = "="
    lines = file(config_path).readlines()
    fp = open(config_path, "w")
    for line in lines:
        line = line.strip()
        if not line.startswith("#") and separator in line:
            assignment = line.split(separator, 1)
            assignment = map(str.strip, assignment)
            fp.write("%s%s%s\n" % (assignment[0], separator, assignment[1]))
        else:
            fp.write(line + "\n")

# inline characters like "echo -n"
def printn (str):
    sys.stdout.write(str)
    sys.stdout.flush()

# parse lines from `fio' command output and return 'opt's value
def parse_lines(lines, opt):
    if opt == "cpu":
        opt="sys"
        regex_strip_value="(%s=[0-9]+[\.][0-9+]%)" % cpu
    elif opt == "lat":
        regex_strip_value="(avg=[0-9]+[\.][0-9+])"
    elif opt == "bw":
        regex_strip_value="(%s=[0-9]+KB/s)" % opt
    else:
        regex="(.*)%s=(.*)" % opt
        regex_strip_value="(%s=[0-9]+)" % opt

    for line in lines:
        if re.match(regex, line):
            out=re.split(regex_strip_value, line)[1]
            out_value=string.split(out, "=")[1]
            if out_value == "":
                return -1
            return out_value

# create a new configuration file in the for "out/000%d.ini" for each
# configuration generated. Also appends the new filename to the array
# filenames, declares a new empty array in the dictionary 'results'
# and a new empty array to average_results dictionary.
def create_config_file(bs, iodepth, rw, i):
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.add_section("global")
    for opt in global_options.keys():
        if opt == "bs" or opt == "iodepth" or opt == "rw":
            continue
        config.set("global", opt, global_options[opt])

    if rw == "read":
        section = "B%sI%sR" % (bs, iodepth)
        op = "read"
    elif rw == "write":
        section = "B%sI%sW" % (bs, iodepth)
        op = "write"
    elif rw == "randread":
        section = "B%sI%sR" % (bs, iodepth)
        op = "randread"
    elif rw == "randwrite":
        section = "B%sI%sW" % (bs, iodepth)
        op = "randwrite"

    config.add_section(section)
    config.set(section, "size", "%sk" % bs)
    config.set(section, "iodepth", iodepth)
    config.set(section, "rw", op)

    filename = "out/%s.ini" % str(i).zfill(4)
    with open(filename, 'wb') as configfile:
        config.write(configfile)
    remove_whitespace_from_assignments(filename)

    filenames.append(filename)
    results[section] = []
    average_results[section] = []

# open template.ini, grab all global options and transform the list of block
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

# clean up old config files if there's any
shutil.rmtree("out/", ignore_errors=True)
os.mkdir("out")

# create config files
i=0
for bs in bss:
    for iodepth in iodepths:
        if global_options['rw'] == "rw":
            create_config_file(bs, iodepth, "read", i)
            i+=1
            create_config_file(bs, iodepth, "write", i)
            i+=1
        elif global_options['rw'] == "randrw":
            create_config_file(bs, iodepth, "randread", i)
            i+=1
            create_config_file(bs, iodepth, "randwrite", i)
            i+=1
        else:
            create_config_file(bs, iodepth, global_options['rw'], i)
            i+=1

k=0
print "Starting benchmarks runs:"
for filename in filenames:
    i=0
    printn(results.keys()[k])
    while i < nruns:
        # TODO: change this to a non hard-coded path
        #subprocess.call("rm -f ../disk_test/*.0", shell=True)
        #p1 = subprocess.Popen(["fio", filename], stdout=subprocess.PIPE)
        #output = p1.stdout.read()
        #p1.stdout.close()
        #printn('*')
        #output_lines = string.split(output, "\n")
        #ret = parse_lines(output_lines, "iops")

        # the following line is here just for testing purposes :)
        ret=math.floor(random.random()*100000)

        if ret == -1:
            printn("!")
            continue
        else:
            results[results.keys()[k]].append(int(ret))
        printn("*")
        i+=1
    print "DONE"
    # calculate the floor of the average and append to average_results
    # dictionary
    average_results[results.keys()[k]].append(
            int(math.floor(sum(results[results.keys()[k]])/
                float(len(results[results.keys()[k]])))))
    k+=1

# TODO: perhaps saving into chunks is better, imagine if, for some god forsaken
# reason, the script breaks and all the previous results are lost :/
writer = csv.writer(open('%s.csv' % timestamp, 'wb'))
for key, value in average_results.items():
       writer.writerow([key, value])
