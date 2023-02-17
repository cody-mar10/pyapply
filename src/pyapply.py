#!/usr/bin/env python3
import argparse
import logging
import multiprocessing
import os
import subprocess
from collections import defaultdict
from typing import DefaultDict, Dict, List, Tuple


def parse_args() -> Tuple[argparse.Namespace, List[str]]:
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

    return parser.parse_known_args()


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
    logging.info(f"Reading mapfile: {mapfile}")
    with open(mapfile) as fp:
        header = fp.readline().rstrip().split("\t")
        vararg_map: DefaultDict[str, List[str]] = defaultdict(list)
        for line in fp:
            values = line.rstrip().split("\t")
            for column, value in zip(header, values):
                vararg_map[column].append(value)
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


def get_commands_list(
    vararg_map: DefaultDict[str, List[str]],
    constargs: List[str],
    column2flag: Dict[str, str],
) -> List[List[str]]:
    """Given a list of `constargs`, the variable arguments map dictionary,
    and a map from the variable args header names to the specific flags,
    put all flags and arguments into a single object to group each
    command instance together.

    Args:
        vararg_map (DefaultDict[str, List[str]]): variable arg name mapped to a list of all
            values for that specific arg. Each item in the list represents a single
        constargs (List[str]): list of all constant args, prepended with the executable name or path
        column2flag (Dict[str, str]): maps column name in `mapfile` to the corresponding
            flag for the command/executable

    Returns:
        List[List[str]]: list of commands where each item is a commands
            list that can be passed directly to `subprocess.run`
    """
    commands = defaultdict(lambda: constargs.copy())
    for colname, values in vararg_map.items():
        flag = column2flag[colname]
        for idx, value in enumerate(values):
            value = value.split(",")
            commands[idx].append(flag)
            commands[idx].extend(value)

    return list(commands.values())


def run_command(command: List[str]):
    logging.info(" ".join(command))
    subprocess.run(command)


def main():
    config, args = parse_args()
    mapfile: str = config.mapfile
    cmd: str = config.cmd

    # FIXME: if providing full path to executable
    logfile = f"{cmd}_commands.log"
    logging.basicConfig(
        filename=logfile,
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    vararg_map = read_mapfile(mapfile)
    varargs, constargs = split_args(args)

    constargs.insert(0, cmd)

    if len(vararg_map) != len(varargs):
        msg = "Number of variable args passed does not equal the number of columns in the mapfile."
        logging.error(msg)
        raise RuntimeError(msg)

    column2flag = map_headers_to_flag(varargs)
    commands = get_commands_list(vararg_map, constargs, column2flag)

    # SEQUENTIAL VERSION
    # for command in commands:
    #     run_command(command)

    # PARALLEL VERSION

    # TODO: add args to specify number of parallel workers
    # TODO: add args to specify what the flag for the specific tool's cpu arg is
    jobs = min(10, len(commands), (os.cpu_count() - 10))
    with multiprocessing.Pool(processes=jobs) as pool:
        #### DO STUFF ONLY WITHIN PROCESS POOL
        pool.map(run_command, commands)

        ## USED FOR FUNCS WITH MULTIPLE ARGS
        # pool.starmap(
        #     get_commands_list,
        #     zip(ARGS1, ARGS2, ARGS2)
        # )

    # PROCESS POOL DELETED

    ### OPTIONAL
    # 3) [X] log all the commands that actually get ran
    # 4) parallelized processing? prob useful with new server
    # 4a) subset is to parallelize with jobs that don't already do multiprocessing
    # 5) make a config file maker
    # 5a) can unpack wildcards with pathlib or glob


# were running this script from the command line
if __name__ == "__main__":
    main()
