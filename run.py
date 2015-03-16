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
    section = "B%sI%sR" % (bs, iodepth)
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.add_section("global")
    for opt in global_options.keys():
        if opt == "bs" or opt == "iodepth" or opt == "rw":
            continue
        config.set("global", opt, global_options[opt])

    config.add_section(section)
    config.set(section, "size", "%sk" % bs)
    config.set(section, "iodepth", iodepth)

    if rw == "read":
        config.set(section, "rw", "read")
    elif rw == "write":
        config.set(section, "rw", "write")
    elif rw == "randr":
        config.set(section, "rw", "randr")
    elif rw == "randw":
        config.set(section, "rw", "randw")

    filename = "out/%s.ini" % str(i).zfill(4)
    with open(filename, 'wb') as configfile:
        config.write(configfile)
    remove_whitespace_from_assignments(filename)

    return filename, section


c = ConfigParser.RawConfigParser(allow_no_value=True)
c.read(config_file)

x = 0
sections=OrderedDict()
average_results=OrderedDict()
configs = []
global_options = {}
filenames=[]

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
            filename, section = create_config_file(bs, iodepth, "read", i)
            i+=1
            filename, section = create_config_file(bs, iodepth, "write", i)
            i+=1
        elif global_options['rw'] == "randrw":
            filename, section = create_config_file(bs, iodepth, "randr", i)
            i+=1
            filename, section = create_config_file(bs, iodepth, "randw", i)
            i+=1
        else:
            filename, section = create_config_file(bs, iodepth, global_options['rw'], i)
            i+=1

        filenames.append(filename)
        sections[section] = []
        average_results[section] = []

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
