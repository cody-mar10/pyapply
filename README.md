# Description
For scripts/executables/tools that can only operate on a single input sample at once, this script will map all the required, variable, and constant args to the command line executable.

# Installation
Only python 3.7+ is required (specifically you need `setuptools`, which is a python built-in to be at least v61 so that pyproject.toml build files can be used correctly.). This script will make no assumptions about the environment other than having python 3.7+ and the target executable available. You can install python by any preferred method, such as using conda. Within any virtual environment that you wish to use pyapply, just run:

```bash
pip3 install .
```

This will install the `pyapply` executable.

# Usage
The syntax of `pyapply` is:
```bash
pyapply MAPFILE EXEC -v{VARARGS} -c CONSTARGS
```

## Variable args
Variable arguments get changed each time the `EXEC` is ran. For example, these could specify different input files to run `EXEC` on. Variable arguments must take the form of `-v{VARARGS}` with no space. This syntax specifies two things:
  1. What flag in the executable does this apply to (`-v` in this case)
  2. What column in the `MAPFILE` has the actual values there (`VARARGS` in this case).

Suppose that our `MAPFILE` looks like this:
```
VARARGS
0
1
2
3
```

This would lead to our `EXEC` being passed `-v 0`, then `-v 1`, and so on until the final value specified in the `MAPFILE`. Note: The `MAPFILE` must have as many columns as variable args in the command line that are passed to the `pyapply.py` script.

## Constant args
Constant args get applied *each* time the `EXEC` is ran. These get passed directly to the `EXEC` executable. In the above scenario with the indicated `MAPFILE`, this essentially equates to:
```bash
EXEC -v 0 -c CONSTARGS
EXEC -v 1 -c CONSTARGS
EXEC -v 2 -c CONSTARGS
EXEC -v 3 -c CONSTARGS
```

# Parallelism
The default mode of `pyapply` is to process jobs sequentially. While this is always easier
to get right, support for parallel processing of jobs has been added with effort to prevent
the user from using too many resources. The major problem is that running jobs in parallel
can lead to using more resources than expected if the individual jobs additionally parallelize.

For example, suppose a job uses 10 threads, but the users want to run these jobs in parallel
batches of 5. That would mean that the total CPU usage becomes 50, rather than just 10.

To account for this, three cli arguments have been added to safely process jobs in parallel:
| Flag           | Description                                                                                                                                                                                                                                                                |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--py-maxcpus` | Sets the maximum amount of CPUs to use overall. Users *cannot* directly set the number of parallel jobs. Instead, they will set the max usage, and simple math will decide how many jobs to run in parallel based on how many CPUs each individual job is expected to use. |
| `--py-cpuarg`  | Clarifies which flag for the job cmd sets CPU usage. Usage at command line: `--py-cpuarg=FLAG` (ie `--py-cpuarg=-t`). Mutually exclusive with `--py-cpuone`.                                                                                                               |
| `--py-cpuone`  | Use if job cmd only allows 1 CPU to be used with no way to change (or if that is the desired default). Mutually exclusive with `--py-cpuarg`.                                                                                                                              |

# Example
Example using [`vRhyme`](https://github.com/AnantharamanLab/vRhyme):

This assumes that `vRhyme` has been installed and is located in a directory that is in your `$PATH` environment variable.

The provided `vRhyme_config.tsv` file indicates 3 different `vRhyme` jobs that will take in one input viral scaffolds fasta file alongside the corresponding `.bam` mapping files to conduct viral binning per input and set of BAMs.


## Sequential run
The command that would get run at the command line would look like this:
```bash
pyapply vRhyme_config.tsv vRhyme -i{input} -b{bam} -t 10
```

This command would effectively then produce the following 3 sequential calls:
```bash
# call 1
vRhyme -i data/EPR/EPR_4281-140.phages_combined.fna \
       -b data/EPR/bamfiles/EPR_4281-140_SRR7968104_trim.sorted.bam \
          data/EPR/bamfiles/EPR_4281-140_SRR8439171_trim.sorted.bam \
       -t 10

# call 2
vRhyme -i data/EPR/EPR_PIR-30.phages_combined.fna \
       -b data/EPR/bamfiles/EPR_PIR-30_SRR7968104_trim.sorted.bam \
          data/EPR/bamfiles/EPR_PIR-30_SRR8439171_trim.sorted.bam \
       -t 10

# call 3
vRhyme -i data/Guaymas/Guaymas_4559-240.phages_combined.fna \
       -b data/Guaymas/bamfiles/Guaymas_4559-240_SRR7968106_trim.sorted.bam \
          data/Guaymas/bamfiles/Guaymas_4559-240_SRR7968107_trim.sorted.bam \
          data/Guaymas/bamfiles/Guaymas_4559-240_SRR7968109_trim.sorted.bam \
          data/Guaymas/bamfiles/Guaymas_4559-240_SRR7968125_trim.sorted.bam \
       -t 10
```

## Parallel run
```bash
pyapply vRhyme_config.tsv vRhyme -i{input} -b{bam} -t 10 --py-maxcpus 30 --py-cpuarg=-t
```

The above command would submit all 3 jobs in parallel since each job uses 10 CPUs,
and we're capping max CPU usage to be 30.
