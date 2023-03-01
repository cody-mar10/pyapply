#!/usr/bin/env python3
import argparse
import logging
import multiprocessing
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import DefaultDict, Dict, List, Optional, Tuple


@dataclass
class Args:
    mapfile: Path
    cmd: Path
    max_cpus: int
    cpu_arg: Optional[str]
    cpu_one: bool
    cmd_args: List[str]


def parse_args() -> Args:
    usage_msg = "pyapply.py [-h] mapfile cmd [OPTIONS (-i{VARARG} -c/--CONSTARG)]"
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

    cpu_flag_args = parser.add_argument_group(
        "CPU ARG -- ONE REQUIRED WITH --py-maxcpus"
    ).add_mutually_exclusive_group(required="--py-maxcpus" in sys.argv)

    parser.add_argument(
        "mapfile",
        type=Path,
        help="tab-delimited file that has the variable arg values, where each column has a header that matches the {values} passed on the command line",
    )
    parser.add_argument("cmd", type=Path, help="path to an executable")
    parser.add_argument(
        "--py-maxcpus",
        type=int,
        metavar="INT",
        default=-1,
        help="max number of cpus to use overall with parallelization (default: %(default)s = run sequentially)",
    )
    cpu_flag_args.add_argument(
        "--py-cpuarg",
        metavar="FLAG",
        help="cmd flag for controlling multithreading/multiprocessing. USAGE: --py-cpuarg=FLAG -- since the argument will usually start with a '-', you must use the '=' sign. If cmd can only use 1 CPU and you want to run it in parallel, use --py-onecpu.",
    )
    cpu_flag_args.add_argument(
        "--py-cpuone",
        action="store_true",
        help="use if cmd can only use 1 cpu with no option to change",
    )

    config, args = parser.parse_known_args()
    return Args(
        mapfile=config.mapfile,
        cmd=config.cmd,
        max_cpus=config.py_maxcpus,
        cpu_arg=config.py_cpuarg,
        cpu_one=config.py_cpuone,
        cmd_args=args,
    )


def read_mapfile(mapfile: Path) -> DefaultDict[str, List[str]]:
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
        mapfile (Path): tab-delimited file that maps variable arguments to
            specific values

    Returns:
        DefaultDict[str, List[str]]: variable arg name mapped to a list of all
            values for that specific arg. Each item in the list represents a single
    """
    logging.info(f"Reading mapfile: {mapfile}")
    with mapfile.open() as fp:
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


def parse_cmd_cpu(constargs: List[str], cpu_arg: str) -> int:
    try:
        cmd_cpu_idx = constargs.index(cpu_arg) + 1
        cmd_cpu = int(constargs[cmd_cpu_idx])
    except ValueError:
        # cpu_arg is not in constargs
        logging.warning(
            f"{cpu_arg} not found as a constant arg. Setting cpu usage per job to be 1. If your job can only use 1 cpu, then ignore this warning."
        )
        cmd_cpu = 1

    return cmd_cpu


def run_command(job_id: int, command: List[str]):
    cmd_str = " ".join(command)
    logging.info(f"JOB {job_id}: {cmd_str}")
    try:
        subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as err:
        logging.error(f"JOB {job_id}: {err.stderr.decode().rstrip()}")
    else:
        logging.info(f"JOB {job_id}: Ran sucessfully")


def main():
    args = parse_args()
    mapfile = args.mapfile
    cmd = args.cmd
    max_cpus = args.max_cpus
    cpu_arg = args.cpu_arg
    cpu_one = args.cpu_one

    logfile = f"{cmd.stem}_commands.log"
    logging.basicConfig(
        filename=logfile,
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    vararg_map = read_mapfile(mapfile)
    varargs, constargs = split_args(args.cmd_args)

    constargs.insert(0, cmd.as_posix())

    if len(vararg_map) != len(varargs):
        msg = "Number of variable args passed does not equal the number of columns in the mapfile."
        logging.error(msg)
        raise RuntimeError(msg)

    column2flag = map_headers_to_flag(varargs)
    commands = get_commands_list(vararg_map, constargs, column2flag)
    n_tasks = len(commands)

    if cpu_one:
        # JOB only uses 1 CPU by default
        cmd_cpus = 1
    elif cpu_arg is not None:
        cmd_cpus = parse_cmd_cpu(constargs, cpu_arg)
    else:
        # --py-cpuarg was not supplied with --py-maxcpus
        # forces running to go back to sequential mode
        cmd_cpus = max_cpus

    if max_cpus <= cmd_cpus:
        # DEFAULTS BACK TO SEQUENTIAL
        # This is basically the default state
        logging.info(f"Running {n_tasks} tasks sequentially")
        for job_id, command in enumerate(commands):
            run_command(job_id, command)
    else:
        # PARALLEL BLOCK
        jobs = max_cpus // cmd_cpus
        logging.info(f"Running {n_tasks} tasks in parallel batches of {jobs}")
        with multiprocessing.Pool(processes=jobs) as pool:
            pool.starmap(run_command, enumerate(commands))


if __name__ == "__main__":
    main()
