# Fio multiplexer tool
The fio multiplexer tool is a simple tool to generate all possible different
combinations between block size and iodepth in order to find gaps and
bottlenecks in your setups. It is originally designed to run benchmarks against
different Qemu configurations and find the best one.

# Run Stress Benchmarks
The tool is devided into two scripts:

1. `./run.py <number of runs> <template.ini>`
 * `number of runs`: fio will run as many times as specified on this argument
 * `template.ini`: fio will take `template.ini` as a base for all the runs
   except for two configurations, that are not written as standard fio option,
   but special for the script to understand the ranges:
    * `bs=4 8 16 32 64 128 256 512`
    * `iodepth=1 2 4 8 16 32 64 128 512`
 * The script outputs a CSV file with an average for each separate test.

1. `./plot.py <first_result.csv> <second_result.csv> <template.ini>`
 * `current setup csv`: the first result you want to compare
 * `new setup`: the new result you want to compare
 * `template.ini`: the same template file you used to run the tests.

# TODO:
 * discard `template.ini` from plot.py
 * automatic installation and dependency resolver
