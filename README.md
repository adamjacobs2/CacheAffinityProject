# CacheAffinityProject

## Relevant Links
- https://sourceforge.net/projects/lmbench/
- https://www.cs.virginia.edu/stream/

## How to run LMBench


## How to run STREAM 
1. Download C code from relevant links (stream.c) along with the timer used for measuring (mysecond.c) and the makefile for compiling
2. Compile for a single cpu using
```bash
gcc -O stream.c -o stream
```
3. compile for muliprocessors using 
```bash
gcc -O2 -fopenmp -D_OPENMP stream.c -o stream
``` 
to compile the code followed by 
```bash
export OMP_NUM_THREADS= num_cores
``` 
to assign number of cores used.
4. Use 
```bash
./stream
``` 
in order to run the produced executable.