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
gcc -O stream.c -o stream.exe
```
*A compiler that supports pthreads such as MinGW is required in order to enable pthread compilation*
 
4. Use 
```bash
./stream.exe
``` 
in order to run the produced executable.

5. Use 
```bash
chmod +x test.sh
``` 
in order to run the produced executable.






