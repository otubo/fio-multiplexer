#!/usr/bin/env python

import matplotlib.pyplot as plt
import numpy as np
import csv, sys
import ConfigParser

if len(sys.argv) != 4:
    print "usage: " + str(sys.argv[0]) + " <first_result.csv> <second_result.csv> <template.ini>"
    sys.exit(1)

results_file0 = sys.argv[1]
results_file1 = sys.argv[2]
config_file = sys.argv[3]

global_options = {}
c = ConfigParser.RawConfigParser(allow_no_value=True)
c.read(config_file)
s = c.sections()[0]
o = c.options(s)
config = []
for opt in o:
    value = c.get(s, opt)
    global_options[opt] = value
bss = global_options['bs'].split(' ')
iodepths = global_options['iodepth'].split(' ')
for bs in bss:
    for iodepth in iodepths:
        if global_options['rw'] == "rw" or global_options['rw'] == "randrw":
            config.append("B%sI%sR" % (bs, iodepth))
            config.append("B%sI%sW" % (bs, iodepth))
        elif global_options['rw'] == "read" or global_options['rw'] == "randread":
            config.append("B%sI%sR" % (bs, iodepth))
        elif global_options['rw'] == "write" or global_options['rw'] == "randwrite":
            config.append("B%sI%sW" % (bs, iodepth))

reader = csv.reader(open(results_file0, 'rb'))
results0 = dict(x for x in reader)

reader = csv.reader(open(results_file1, 'rb'))
results1 = dict(x for x in reader)

ordered_result0 = []
ordered_result1 = []

for c in config:
    value0 = results0[c].replace("[", "")
    value0 = value0.replace("]", "")
    value1 = results1[c].replace("[", "")
    value1 = value1.replace("]", "")
    ordered_result0.append(int(value0))
    ordered_result1.append(int(value1))

N = len(config)
ind = np.arange(N)
width = 0.35
fig, ax = plt.subplots()

rects1 = ax.bar(ind, tuple(ordered_result0), width, color='b')
rects2 = ax.bar(ind+width, tuple(ordered_result1), width, color='r')

ax.set_ylabel('iops')
ax.set_title('configuration')
ax.set_xticks(ind+width)
ax.set_xticklabels(tuple(config), rotation='vertical')

def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.text(rect.get_x()+rect.get_width()/2., 1.05*height, '%d'%int(height),
                ha='center', va='bottom', rotation='vertical')

autolabel(rects1)
autolabel(rects2)
plt.savefig("result.png")
plt.show()