# Description
For scripts/executables/tools that can only operate on a single input sample at once, this script will map all the required, variable, and constant args to the command line executable.

# Installation
Only python 3.6+ is required. This script will make no assumptions about the environment other than having python 3.6+ and the target executable available. You can install python by any preferred method, such as using conda.

# Usage
The syntax of `pyapply` is:
```bash
pyapply.py MAPFILE EXEC -v{VARARGS} -c CONSTARGS
```

## Variable args
Variable arguments get changed each time the `EXEC` is ran. For example, these could specify different input files to run `EXEC` on. Variable arguments must take the form of `-v{VARARGS}` with no space. This syntax specifies two things:
  1. What flag in the executable does this apply to
  2. What column in the `MAPFILE` has the actual values there.

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


# Example
Example using [`vRhyme`](https://github.com/AnantharamanLab/vRhyme):

This assumes that `vRhyme` has been installed and is located in a directory that is in your `$PATH` environment variable.

The provided `vRhyme_config.tsv` file indicates 3 different `vRhyme` jobs that will take in one input viral scaffolds fasta file alongside the corresponding `.bam` mapping files to conduct viral binning per input and set of BAMs.

The command that would get run at the command line would look like this:
```bash
./pyapply.py vRhyme_config.tsv vRhyme -i{input} -b{bam} -t 10
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

