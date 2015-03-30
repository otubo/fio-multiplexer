# Fio multiplexer tool
The fio multiplexer tool is a simple tool to generate all possible different
combinations between block size and iodepth in order to find gaps and
bottlenecks in your setups. It is originally designed to run benchmarks against
different Qemu configurations and find the best one.

# Run Stress Benchmarks
The tool is devided into two scripts:

1. Usage:
 * `Usage: ./run.py [[-c|--config=] <config.ini>] [[-v|--vms=] <vms.ini>] [-h|--help]
    -c|--config         configuration file that will be used as base for
                        fio tool
    -v|--vms            configuration file that describes every virtual
                        machine setup that will be envolved on the run
    -h|--help           displays this help message`

1. Arguments:
 * `config.ini`: fio will take `config.ini` as a base for all the runs
   except for three configurations, that are not written as standard fio option,
   but special for the script:
    * `bs=4 8 16 32 64 128 256 512`
    * `iodepth=1 2 4 8 16 32 64 128 512`
    * `number_of_runs=10`
 * The script outputs a CSV file with an average for each separate test.

1. `./plot.py <first_result.csv> <second_result.csv> <template.ini>`
 * `current setup csv`: the first result you want to compare
 * `new setup`: the new result you want to compare
 * `template.ini`: the same template file you used to run the tests.

# TODO:
 * discard `template.ini` from plot.py
 * automatic installation and dependency resolver
