#!/bin/bash

# --- CONFIGURATION ---
PROGRAM="./stream"
# The vCPUs belonging to ONE P-Core (vCPU 0 and its Hyperthread vCPU 4). 
# CHANGE THIS MASK if your core IDs are different!
SINGLE_CORE_MASK="0,4"
OUTPUT_FILE="linux_scaling_results.txt"

# Array of all available vCPUs for 8 physical cores (4 P-cores + 4 E-cores)
# P-cores (Primary): 0, 1, 2, 3 | P-cores (HT): 4, 5, 6, 7 | E-cores: 8, 9, 10, 11
# We use the primary threads of 8 cores for 8x1 (1 thread per core) test
ALL_PRIMARY_VCPUS="0,1,2,3,8,9,10,11"

# Clear previous results
> $OUTPUT_FILE

echo "--- OpenMP Scaling Study ---" | tee -a $OUTPUT_FILE
echo "Single Core Target Mask (P-Core 0): $SINGLE_CORE_MASK" | tee -a $OUTPUT_FILE
echo "--------------------------" | tee -a $OUTPUT_FILE
echo "" | tee -a $OUTPUT_FILE

# --- PART 1: OVER-SUBSCRIPTION (THREADS on ONE CORE) ---
echo "## Part 1: Threads Incrementing on a Single Core (1C x 1T to 1C x 8T)" | tee -a $OUTPUT_FILE
echo "All runs bound to vCPUs: $SINGLE_CORE_MASK (P-Core 0)" | tee -a $OUTPUT_FILE

# Disable OpenMP affinity. Taskset handles the binding, OMP runs the threads.
export OMP_PROC_BIND=false

for T in {1..8}; do
    export OMP_NUM_THREADS=$T
    echo "Running 1 Core with $T Threads (Over-subscribed)..." | tee -a $OUTPUT_FILE
    
    # Run with taskset to confine the entire process to the single core's vCPUs
    taskset -c $SINGLE_CORE_MASK $PROGRAM >> $OUTPUT_FILE 2>&1
    
    echo "--- END 1C x $T T ---" >> $OUTPUT_FILE
done

# --- PART 2: CORE SCALING (2C x 1T to 8C x 8T) ---
echo "" | tee -a $OUTPUT_FILE
echo "## Part 2: Core Scaling (N Cores x M Threads)" | tee -a $OUTPUT_FILE

# Enable OpenMP affinity for proper thread distribution
export OMP_PROC_BIND=spread 

# Array of core counts (C) and the corresponding number of threads (T)
# C_STEP defines the number of cores to use, T_STEP defines threads per core
# We will use the primary vCPUs (0, 1, 2, 3, 8, 9, 10, 11) for true core scaling.

# Primary vCPUs list, ordered to allow slicing for N cores
VCPU_LIST=(0 1 2 3 8 9 10 11) # 4 P-primary, 4 E-primary

for C_STEP in {2..8}; do # N Cores: 2 to 8
    
    # Select the first C_STEP primary vCPUs for binding
    VCPU_SLICE=${VCPU_LIST[@]:0:$C_STEP}
    VCPU_BINDING="${VCPU_SLICE// /,}"
    
    # Iterate through thread counts T from 1 up to C_STEP
    for T in {1..8}; do 
        if [ "$T" -le "$C_STEP" ] || [ "$T" -eq "$C_STEP"*2 ]; then
            
            # --- T <= C_STEP: 1 thread per core, using OMP_PLACES for primary vCPUs ---
            if [ "$T" -le "$C_STEP" ]; then
                export OMP_NUM_THREADS=$T
                # OMP_PLACES restricts threads to the primary vCPUs of the C_STEP cores
                export OMP_PLACES="{${VCPU_BINDING}}" 
                
                echo "Running $C_STEP Cores with $T Threads (1T/core, primary vCPUs)..." | tee -a $OUTPUT_FILE

            # --- T = C_STEP * 2: 2 threads per core (using Hyperthreading/SMT) ---
            # This only makes sense for P-cores, but we run it for the sake of completeness.
            elif [ "$T" -eq "$C_STEP"*2 ]; then
                export OMP_NUM_THREADS=$T
                # For 2T/core, we need to bind to the primary vCPUs AND their secondary/HT vCPUs
                # This is complex to automate robustly, so we use the C_STEP primary vCPUs
                # and rely on OMP_PROC_BIND=spread to utilize the available HT/secondary vCPUs.
                export OMP_PLACES="{${VCPU_BINDING}}" 
                
                echo "Running $C_STEP Cores with $T Threads (2T/core, using SMT/HT)..." | tee -a $OUTPUT_FILE
            
            fi
            
            $PROGRAM >> $OUTPUT_FILE 2>&1
            echo "--- END ${C_STEP}C x $T T ---" >> $OUTPUT_FILE
        fi
    done
done

echo "" | tee -a $OUTPUT_FILE
echo "Script finished. Results saved to $OUTPUT_FILE"

# Clean up environment variables
unset OMP_NUM_THREADS
unset OMP_PROC_BIND
unset OMP_PLACES