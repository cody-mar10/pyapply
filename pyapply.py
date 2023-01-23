#!/usr/bin/env python3
import argparse
from typing import List


def main(mapfile: str, cmd: str, args: List[str]):
    # [X] 0) setup command line parsing
    # 1) prepare arguments for cmd
    # 1a) read config file
    # 1b) break args into varargs and constargs
    # 1c) mapping variable args to values in config file

    # 2) pass all args to the cmd

    ### OPTIONAL
    # 3) log all the commands that actually get ran
    # 4) parallelized processing? prob useful with new server
    # 4a) subset is to parallelize with jobs that don't already do multiprocessing
    pass


# were running this script from the command line
if __name__ == "__main__":
    usage_msg = (
        "usage: pyapply.py [-h] mapfile cmd [OPTIONS (-i{VARARG} -c/--CONSTARG)]"
    )
    description = (
        "apply any command/script to a set of variable inputs in the `mapfile`\n\n"
        "VARIABLE ARGS:\n\tall variable args that are specified in the mapfile must be delivered to the\n"
        "\tcommand line like this: -i{input} where the `-i` is the flag for the command\n"
        "\tand the {input} part specifies the header in the mapfile. Note there is no space.\n"
        "CONSTANT ARGS:\n\tall constant args (args that are the same for each command) can be supplied\n"
        "\tas if they were being directly passed to the command (ie --threads 10)\n"
        "\tusing the flag that is required by the command.\n"
        "EXAMPLE:\n\tThis uses the built-in unix command `ls`:\n\t"
        "pyapply.py mapfile ls {input} -laFGH\n"
        "\nFinally, the order matters! The command must be in this order:\n"
        "pyapply.py mapfile cmd [OPTIONS]"
    )
    parser = argparse.ArgumentParser(
        usage=usage_msg,
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "mapfile",
        help="tab-delimited file that has the variable arg values, where each column has a header that matches the {values} passed on the command line",
    )
    parser.add_argument("cmd", help="path to an executable")

    config, args = parser.parse_known_args()
    main(mapfile=config.mapfile, cmd=config.cmd, args=args)
