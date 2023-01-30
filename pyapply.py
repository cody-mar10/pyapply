#!/usr/bin/env python3
import argparse
import subprocess
from collections import defaultdict
from typing import List, DefaultDict, Dict, Tuple


def read_mapfile(mapfile: str) -> DefaultDict[str, List[str]]:
    """Read the `mapfile` into a dictionary to map the column names
    to specific value instances. The `mapfile` needs to be in the format:

    ```
    VARARG1 VARARG2
    val11   val21
    val12   val22
    ```

    At the command line, you'd pass the following flags with the above `mapfile`:

    `-v1{VARARG1} -v2{VARARG2}`

    Args:
        mapfile (str): tab-delimited file that maps variable arguments to
            specific values

    Returns:
        DefaultDict[str, List[str]]: variable arg name mapped to a list of all
            values for that specific arg. Each item in the list represents a single
    """
    with open(mapfile) as fp:
        header = fp.readline().rstrip().split("\t")
        vararg_map: DefaultDict[str, List[str]] = defaultdict(list)
        for line in fp:
            values = line.rstrip().split("\t")
            for column, value in zip(header, values):
                vararg_map[column].append(value.replace(",", " "))
    return vararg_map


def split_args(args: List[str]) -> Tuple[List[str], List[str]]:
    """Split the list of arguments that are for the command/executable into
    constant and variable args based on their flags from the command line.
    All variable args take the form of `-v{VARARG}`. Constant args are
    everything else.

    Args:
        args (List[str]): arguments for the command/executable

    Returns:
        Tuple[List[str], List[str]]: (variable args, constant args)
    """
    varargs: List[str] = list()
    constargs: List[str] = list()
    for arg in args:
        if "{" in arg:
            # store var args
            varargs.append(arg)
        else:
            # store constant args
            constargs.append(arg)
    return varargs, constargs


def map_headers_to_flag(varargs: List[str]) -> Dict[str, str]:
    """Parse the variable args list, and map the name of the header in the
    `mapfile` to the specific flag that the command/executable takes as input.

    Args:
        varargs (List[str]): variable args passed at the command line

    Returns:
        Dict[str, str]: maps column name in `mapfile` to the corresponding
            flag for the command/executable
    """
    column2flag: Dict[str, str] = dict()
    for arg in varargs:
        flag, column = arg.split("{")
        column = column.replace("}", "")
        column2flag[column] = flag
    return column2flag


def main(mapfile: str, cmd: str, args: List[str]):
    # [X] 0) setup command line parsing
    # [X] 1) prepare arguments for cmd
    # [X] 1a) read config file
    # [X] 1b) break args into varargs and constargs

    vararg_map = read_mapfile(mapfile)
    varargs, constargs = split_args(args)

    if len(vararg_map) != len(varargs):
        raise RuntimeError(
            "Number of variable args passed does not equal the number of columns in the mapfile."
        )

    # [X] 1c) mapping variable args to values in config file
    column2flag = map_headers_to_flag(varargs)

    # 2) pass all args to the cmd
    # TODO: figure out how run the vrhyme commands using a loop

    # ie the FIRST command should look like this:
    # COMMAND = "vRhyme -i data/EPR/EPR_4281-140.phages_combined.fna -b data/EPR/bamfiles/EPR_4281-140_SRR7968104_trim.sorted.bam data/EPR/bamfiles/EPR_4281-140_SRR8439171_trim.sorted.bam -t 10"
    # subprocess.run(COMMAND)

    ### OPTIONAL
    # 3) log all the commands that actually get ran
    # 4) parallelized processing? prob useful with new server
    # 4a) subset is to parallelize with jobs that don't already do multiprocessing
    # 5) make a config file maker
    # 5a) can unpack wildcards with pathlib or glob
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
    print(config, args)
    main(mapfile=config.mapfile, cmd=config.cmd, args=args)
