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

*A compiler that supports OpenMP is required in order to enable OpenPM compilation*
 
4. Use 
```bash
./stream
``` 
in order to run the produced executable.

### Minimum Array Size

Use the following formula to compute the required array size in elements of which needs to be changed for STREAM_ARRAY_SIZE within the stream.c file:

$$\text{Array Size (elements)} \ge 4 \times \frac{\text{Total L3 Cache (bytes)}}{\text{Size of STREAM\_TYPE (bytes)}}$$

If using STREAM_TYPE double, then size would be 8 bytes.

*Changing the line for STREAM_ARRAY_SIZE in stream.c is important for forcing traffic.*



