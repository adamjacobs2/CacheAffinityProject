import subprocess
import csv
import re
import os
import statistics

# --- Configuration ---
STREAM_BINARY = "./stream"
THREAD_RANGE = range(2, 33, 2)  # threads from 2 to 32

# High-affinity configurations
HA_CONFIGS = [
    [0, 1],
    [2, 3],
]

# Low-affinity configurations
LA_CONFIGS = [
    [0, 2],
    [1, 3],
]


# --- Helper to generate vCPU list by cycling ---
def generate_vcpus(mapping, num_threads):
    return [mapping[i % len(mapping)] for i in range(num_threads)]


# --- Run STREAM and extract the chosen kernel ---
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
        print(f"WARNING: {test.capitalize()} not found for vCPUs {vcpus}, threads={threads}")
        return None


def main():
    test = choose_kernel()
    CSV_FILE = f"stream_{test.lower()}_ha_la.csv"

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["threads", "perf_high_affinity", "perf_low_affinity"])

        for threads in THREAD_RANGE:
            # --- High Affinity average ---
            ha_results = []
            for ha_v in HA_CONFIGS:
                ha_thread_vcpus = generate_vcpus(ha_v, threads)
                perf = run_stream(ha_thread_vcpus, threads, test)
                if perf is not None:
                    ha_results.append(perf)
            perf_high = statistics.mean(ha_results) if ha_results else None

            # --- Low Affinity average ---
            la_results = []
            for la_v in LA_CONFIGS:
                la_thread_vcpus = generate_vcpus(la_v, threads)
                perf = run_stream(la_thread_vcpus, threads, test)
                if perf is not None:
                    la_results.append(perf)
            perf_low = statistics.mean(la_results) if la_results else None

            print(f"Threads={threads}, HA_avg={perf_high}, LA_avg={perf_low}, test={test}")
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
        print("Invalid choice. Defaulting to TRIAD.")
        return "TRIAD"

    return mapping[choice]


if __name__ == "__main__":
    main()
