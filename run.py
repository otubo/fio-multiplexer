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
import getopt
import paramiko
import time

vms_file = None
template_file = None

timestamp=datetime.datetime.now().strftime("%Y%m%d%H%M%S")

# dictionary that is in the format:
#   {'config_name': [list, of, values]}
iops=OrderedDict()
bw=OrderedDict()
lat=OrderedDict()
cpu=OrderedDict()
# dictionary that is in the format:
#   {'config_name': 'average for this config'}
average_iops=OrderedDict()
average_bw=OrderedDict()
average_lat=OrderedDict()
average_cpu=OrderedDict()
# dictionary that holds all global options defined in the [global] section of
# the template.ini file.
global_options = {}
# all the different filenames for each configuration generated
filenames=[]
# block sizes and iodepth arrays
bss = 0
iodepths = 0
# main array to hold all VM definitions
vms = {}

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

# print information back to user depending on how much verbosity is set
# info_type can be:
#   I: Info
#   W: Warning
#   E: Error
#   V: Verbose
def print_verbose(info_type, string):
    # TODO: add logic to add more information depending on verbosity config
    print "[%s] %s" % (info_type, string)

# parse lines from `fio' command output and return 'opt's value
def parse_lines(lines, opt):
    regex="(.*)%s=(.*)" % opt
    regex_strip_value="(%s=[0-9]+)" % opt

    if opt == "cpu":
        regex="(.*)sys=(.*)"
        regex_strip_value="(sys=[0-9]+.[0-9]+)"
    elif opt == "lat":
        regex="\s+%s(.*)" % opt
        regex_strip_value="(avg=[0-9]+[\.][0-9]+)"
    elif opt == "bw":
        regex_strip_value="(%s=[0-9]+KB/s)" % opt

    for line in lines:
        if re.match(regex, line):
            out=re.split(regex_strip_value, line)[1]
            out_value=string.split(out, "=")[1]
            if out_value == "":
                return -1
            out_value=re.sub(r'[^\w]', '', out_value)
            out_value=re.sub(r'KBs', '', out_value)
            return out_value

# create a new configuration file in the format "out/000%d.ini" for each
# configuration generated. Also appends the new filename to the array
# filenames, declares a new empty array in the dictionary of values and a new
# empty array to average_XXX_dictionary.
def create_one_job(bs, iodepth, rw, i):
    global iops
    global bw
    global lat
    global cpu
    global average_iops
    global average_bw
    global average_lat
    global average_cpu
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.add_section("global")

    # skip these options, we're gonna get them later
    for opt in global_options.keys():
        if opt == "bs" or opt == "iodepth" or \
            opt == "rw" or opt == "number_of_runs":
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

    # update filenames array
    filenames.append(filename)

    # create new array in the dictionary of values
    iops[section] = []
    bw[section] = []
    lat[section] = []
    cpu[section] = []

    # create new array on the average dictionary
    average_iops[section] = []
    average_bw[section] = []
    average_lat[section] = []
    average_cpu[section] = []

# open template.ini, grab all global options and transform the list of block
# sizes and iodepths into interable arrays
def parse_template(template):
    print_verbose("V", "parsing template.ini")
    global global_options
    global bss
    global iodepths

    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(template_file)
    global_section = config.sections()[0]
    options = config.options(global_section)
    for option in options:
        value = config.get(global_section, option)
        global_options[option] = value
    bss = global_options['bs'].split(' ')
    iodepths = global_options['iodepth'].split(' ')

# open vms.ini and parse all configuration options for each vm declared
def parse_vms(vms_file):
    print_verbose("V", "parsing vms.ini")
    global vms

    i=0
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(vms_file)
    for section in config.sections():
        vms[section] = {}
        options = config.options(section)
        vms[section]['id'] = i
        vms[section]['name'] = section
        for option in options:
            vms[section][option] = config.get(section, option)
        i+=1

def cleanup_old_config():
    # clean up old config files if there's any
    print_verbose("V", "cleaning up old configuration")
    print_verbose("V", "removing out/")
    shutil.rmtree("out/", ignore_errors=True)
    print_verbose("V", "creating new out/")
    os.mkdir("out")

def create_all_jobs(bss, iodepths):
    print_verbose("V", "creating all new job files inside out/")
    # create config files
    i=0
    for bs in bss:
        for iodepth in iodepths:
            if global_options['rw'] == "rw":
                create_one_job(bs, iodepth, "read", i)
                i+=1
                create_one_job(bs, iodepth, "write", i)
                i+=1
            elif global_options['rw'] == "randrw":
                create_one_job(bs, iodepth, "randread", i)
                i+=1
                create_one_job(bs, iodepth, "randwrite", i)
                i+=1
            else:
                create_one_job(bs, iodepth, global_options['rw'], i)
                i+=1

def spawn_virtual_machine(vm):
    print_verbose("I", "spawning new virtual machine id: %d" % vm['id'])
    return subprocess.Popen(["./startvm.sh", vm['qemu_bin'], vm['rootfs'],
        vm['external_disk'], vm['iothreads'], str(vm['id'])])

def scp_job_files(vm):
    print_verbose("I", "copying all job files to virtual machine %d" % vm['id'])
    while True:
        try:
            t = paramiko.Transport(('localhost', 5000+int(vm['id'])))
        except paramiko.SSHException:
            # SSH not available yet, it means the virtual machine is not
            # up yet, sleep 5 and retry
            print_verbose("W", "scp failed, perhaps virtual machine is not up yet, sleep 5 and try again...")
            time.sleep(5)
            continue
        break

    t.connect(username=vm['user'], password=vm['password'])
    sftp = paramiko.SFTPClient.from_transport(t)
    try:
        # XXX this should be inside cleanup_old_config
        sftp.remove("/tmp/out/*")
        sftp.rmdir("/tmp/out")
    except IOError:
        pass

    sftp.mkdir("/tmp/out")

    for filename in filenames:
        sftp.put(filename, "/tmp/%s" % filename)

    sftp.close()
    t.close()

def stop_vm(vm):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect('localhost', port=5000+int(vm['id']), username=vm['user'],
            password=vm['password'], allow_agent=False, look_for_keys=False)
    stdin , stdout, stderr = c.exec_command("shutdown -h now")
    c.close()

def stop_all_vms(vms):
    for vm in vms:
        stop_vm(vms[vm])

def mount_testing_device(vm):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect('localhost', port=5000+int(vm['id']), username=vm['user'],
            password=vm['password'], allow_agent=False, look_for_keys=False)
    stdin , stdout, stderr = c.exec_command("ls /dev/disk/by-uuid")
    disk_list = stdout.read().replace("\n", " ").split(" ")
    del disk_list[-1]
    for disk in disk_list:
        cmd = "mount|grep %s" % disk
        stdin, stdout, stderr = c.exec_command(cmd)
        if not stdout.read() and not stderr.read():
            print_verbose("V", "mounting device %s on %s inside virtual machine %d"
                    % (disk,global_options['directory'], vm['id']))
            cmd = "mount /dev/disk/by-uuid/%s %s" % (disk,
                    global_options['directory'])
            stdin, stdout, stderr = c.exec_command(cmd)

    c.close()

def start_jobs(vm, nruns):
    print_verbose("I", "starting jobs on virtual machine %d" % vm['id'])
    global iops
    global bw
    global lat
    global cpu
    global average_iops
    global average_bw
    global average_lat
    global average_cpu

    local_iops = iops
    local_bw = bw
    local_lat = lat
    local_cpu = cpu
    local_average_iops = average_iops
    local_average_bw = average_bw
    local_average_lat = average_lat
    local_average_cpu = average_cpu

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect('localhost', port=5000+int(vm['id']), username=vm['user'],
            password=vm['password'], allow_agent=False, look_for_keys=False)
    k=0
    for filename in filenames:
        i=0
        printn(local_iops.keys()[k])
        while int(i) < int(nruns):
            # TODO: change this to a non hard-coded path
            stdin, stdout, stderr = c.exec_command("fio /tmp/%s" % filename)
            output = stdout.read()
            output_lines = string.split(output, "\n")
            ret_iops = parse_lines(output_lines, "iops")
            ret_bw = parse_lines(output_lines, "bw")
            ret_lat = parse_lines(output_lines, "lat")
            ret_cpu = parse_lines(output_lines, "cpu")

            # the following line is here just for testing purposes :)
            #ret_iops=math.floor(random.random()*100000)
            #ret_bw=math.floor(random.random()*100000)
            #ret_lat=math.floor(random.random()*100000)
            #ret_cpu=math.floor(random.random()*100000)

            if ret_iops == -1 or ret_bw == -1 or ret_lat == -1 or ret_cpu == -1:
                printn("!")
                continue
            else:
                local_iops[local_iops.keys()[k]].append(int(ret_iops))
                local_bw[local_bw.keys()[k]].append(int(ret_bw))
                local_lat[local_lat.keys()[k]].append(int(ret_lat))
                local_cpu[local_cpu.keys()[k]].append(int(ret_cpu))
            printn("*")
            i+=1

        print "DONE"
        # calculate the floor of the average and append to average_iops
        # dictionary
        # XXX too many things duplicated
        # XXX This piece of code is barely readable the way it is right now,
        # some change would be nice
        local_average_iops[local_iops.keys()[k]].append(
                int(math.floor(sum(local_iops[local_iops.keys()[k]])/
                    float(len(local_iops[local_iops.keys()[k]])))))

        local_average_bw[local_bw.keys()[k]].append(
                int(math.floor(sum(local_bw[local_bw.keys()[k]])/
                    float(len(local_bw[local_bw.keys()[k]])))))

        local_average_lat[local_lat.keys()[k]].append(
                int(math.floor(sum(local_lat[local_lat.keys()[k]])/
                    float(len(local_lat[local_lat.keys()[k]])))))

        local_average_cpu[local_cpu.keys()[k]].append(
                int(math.floor(sum(local_cpu[local_cpu.keys()[k]])/
                    float(len(local_cpu[local_cpu.keys()[k]])))))
        k+=1
    c.close()

    # TODO: perhaps saving into chunks is better, imagine if, for some god forsaken
    # reason, the script breaks and all the previous iops are lost :/
    # XXX: too manu things duplicated
    if int(vm['iothreads']) == 1:
        result_folder_name = "%s_%s_iothreads" % (timestamp, vm['name'])
    else:
        result_folder_name = "%s_%s_virtio-blk" % (timestamp, vm['name'])
    os.mkdir(result_folder_name)

    writer_iops = csv.writer(open('%s/iops.csv' % result_folder_name, 'wb'))
    for key, value in local_average_iops.items():
           writer_iops.writerow([key, value])

    writer_bw = csv.writer(open('%s/bw.csv' % result_folder_name, 'wb'))
    for key, value in local_average_bw.items():
           writer_bw.writerow([key, value])

    writer_lat = csv.writer(open('%s/lat.csv' % result_folder_name, 'wb'))
    for key, value in local_average_lat.items():
           writer_lat.writerow([key, value])

    writer_cpu = csv.writer(open('%s/cpu.csv' % result_folder_name, 'wb'))
    for key, value in local_average_cpu.items():
           writer_cpu.writerow([key, value])

    stop_vm(vm)

def main():
    # parse command line options
    global template_file
    global vms_file
    global vms

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hv:t:", ["help", "vms=",
            "template="])
    except getopt.error, msg:
        print msg
        print "for help use --help"
        return 2
    # process options
    for o, a in opts:
        if o in ("-h", "--help"):
            print __doc__
            return 0
        elif o in ("-v", "--vms"):
            vms_file=a
        elif o in ("-t", "--template"):
            template_file=a

    #if nothing is set, go back to default
    if template_file == None:
        print_verbose("I", "No configuration given, using default template.ini")
        template_file = "template.ini"

    if vms_file == None:
        print_verbose("I", "No configuration given, using default vms.ini")
        vms_file = "vms.ini"

    parse_template(template_file)
    parse_vms(vms_file)
    cleanup_old_config()
    create_all_jobs(bss, iodepths)

    for vm in vms:
        spawn_virtual_machine(vms[vm])
        scp_job_files(vms[vm])
        mount_testing_device(vms[vm])

    #everything is set, start `fio'
    for vm in vms:
        start_jobs(vms[vm], global_options['number_of_runs'])

    return 0

if __name__ == "__main__":
    sys.exit(main())
