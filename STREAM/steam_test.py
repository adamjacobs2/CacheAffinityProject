import subprocess
import csv
import re
import os

# --- Configuration ---
STREAM_BINARY = "./stream"
THREAD_RANGE = range(2, 33)  # threads from 2 to 32

# Define vCPU mappings for this run
HA_VCPUS = [0, 1] # High affinity (same P-core)
LA_VCPUS = [0, 2]  # Low affinity (different P-cores)



# --- Helper to generate vCPU list by cycling ---
def generate_vcpus(mapping, num_threads):
    """
    Cycle through the vCPU mapping to assign threads.
    """
    return [mapping[i % len(mapping)] for i in range(num_threads)]

# --- Run STREAM and extract Scale ---
def run_stream(vcpus, threads, test):
    vcpu_str = ",".join(str(v) for v in vcpus)
    env = {"OMP_NUM_THREADS": str(threads), **os.environ}

    result = subprocess.run(
        ["taskset", "-c", vcpu_str, STREAM_BINARY],
        capture_output=True,
        text=True,
        env=env
    ).stdout

    match = re.search(rf"{test.capitalize()}:\s+([\d\.]+)", result)
    if match:
        return float(match.group(1))
    else:
        print(f"WARNING: Scale not found for vCPUs {vcpus}, threads={threads}")
        return None


def main():
    test = choose_kernel()
    CSV_FILE = f"stream_{test}_ha_la.csv"
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["threads", "perf_high_affinity", "perf_low_affinity"])
        for threads in THREAD_RANGE:
            ha_v = generate_vcpus(HA_VCPUS, threads)
            la_v = generate_vcpus(LA_VCPUS, threads)

            
            perf_high = run_stream(ha_v, threads, test)
            perf_low = run_stream(la_v, threads, test)

            print(f"Threads={threads}, HA={perf_high}, LA={perf_low}", "test:", test)
            writer.writerow([threads, perf_high, perf_low])
    
    
    print(f"Results saved to {CSV_FILE}")



def choose_kernel():
    print("Which STREAM kernel do you want to test?")
    print("1) Copy")
    print("2) Scale")
    print("3) Add")
    print("4) Triad")
    choice = input("Enter choice (1–4): ").strip()

    mapping = {
        "1": "COPY",
        "2": "SCALE",
        "3": "ADD",
        "4": "TRIAD"
    }

    if choice not in mapping:
        print("Invalid choice. Defaulting to Triad.")
        return "TRIAD"

    return mapping[choice]

if __name__ == "__main__":
    main()
