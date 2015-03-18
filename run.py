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

if len(sys.argv) != 3:
    print "usage: " + str(sys.argv[0]) + " <nruns> <template.ini>"
    sys.exit(1)

nruns = int(sys.argv[1])
config_file = str(sys.argv[2])

x = 0
sections=OrderedDict()
average_results=OrderedDict()
configs = []
global_options = {}
filenames=[]

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

def printn (str):
    sys.stdout.write(str)
    sys.stdout.flush()

def parse_lines(lines):
    for line in lines:
        if re.match("(.*)iops=(.*)", line):
            out=re.split("(iops=[0-9]+)", line)[1]
            out_value=string.split(out, "=")[1]
            if out_value == "":
                return -1
            return out_value

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
    sections[section] = []
    average_results[section] = []

c = ConfigParser.RawConfigParser(allow_no_value=True)
c.read(config_file)

s = c.sections()[0]
o = c.options(s)
for opt in o:
    value = c.get(s, opt)
    global_options[opt] = value

bss = global_options['bs'].split(' ')
iodepths = global_options['iodepth'].split(' ')
shutil.rmtree("out/", ignore_errors=True)
os.mkdir("out")
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
    printn(sections.keys()[k])
    while i < nruns:
        subprocess.call("rm -f ../disk_test/*.0", shell=True)
        p1 = subprocess.Popen(["fio", filename], stdout=subprocess.PIPE)
        output = p1.stdout.read()
        p1.stdout.close()
        printn('*')
        output_lines = string.split(output, "\n")
        ret = parse_lines(output_lines)

        # the following line is here just for testing purposes :)
        #ret=math.floor(random.random()*100000)

        if ret == -1:
            printn("!")
            continue
        else:
            sections[sections.keys()[k]].append(int(ret))
        printn("*")
        i+=1
    print "DONE"
    average_results[sections.keys()[k]].append(int(math.floor(sum(sections[sections.keys()[k]])/float(len(sections[sections.keys()[k]])))))
    k+=1

writer = csv.writer(open('results.csv', 'wb'))
for key, value in average_results.items():
       writer.writerow([key, value])