/*-----------------------------------------------------------------------*/
/* Modified STREAM with pthread and cache affinity control               */
/* Based on STREAM 5.10 by John D. McCalpin                             */
/* Modified to add pthread support and CPU affinity testing             */
/*-----------------------------------------------------------------------*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <math.h>
#include <float.h>
#include <limits.h>
#include <sys/time.h>
#include <pthread.h>
#include <windows.h>

/*-----------------------------------------------------------------------*/
/* CONFIGURATION SECTION                                                 */
/*-----------------------------------------------------------------------*/

/* Configure which cores share L3 cache */
/* Example for a CPU with 2 CCXs, each with 4 cores sharing L3:
   Cores 0-3 share L3, Cores 4-7 share L3 */
#define MAX_CORES 16
#define MAX_L3_GROUPS 4

/* Define cores that share L3 cache vs those that don't */
/* Edit this structure to match your CPU topology */
typedef struct {
    int num_l3_cores;           /* Number of cores sharing L3 */
    int l3_cores[MAX_CORES];    /* Core IDs that share L3 cache */
    int num_no_l3_cores;        /* Number of cores NOT sharing L3 */
    int no_l3_cores[MAX_CORES]; /* Core IDs that don't share L3 */
} L3CacheTopology;

/* EDIT THIS TO MATCH YOUR CPU */
/* Example: Cores 0-3 share L3, Cores 4-7 don't share with 0-3 */
L3CacheTopology cpu_topology = {
    .num_l3_cores = 4,
    .l3_cores = {0, 1, 2, 3},        /* Cores that share L3 */
    .num_no_l3_cores = 4,
    .no_l3_cores = {4, 5, 6, 7}      /* Cores that DON'T share L3 with above */
};

#ifndef STREAM_ARRAY_SIZE
#   define STREAM_ARRAY_SIZE	10000000
#endif

#ifndef OFFSET
#   define OFFSET	0
#endif

#ifndef NTIMES
#   define NTIMES	10
#endif

#ifndef STREAM_TYPE
#define STREAM_TYPE double
#endif

/*-----------------------------------------------------------------------*/
/* TEST CONFIGURATION                                                    */
/*-----------------------------------------------------------------------*/
typedef enum {
    NO_AFFINITY, // Sharing L3 cache not considered
    WITH_AFFINITY // Pin threads to cores sharing L3
} AffinityMode;

typedef struct {
    int num_cores;        // Number of physical cores to use 
    int threads_per_core; // Threads per core 
    AffinityMode affinity;
} TestConfig;

static STREAM_TYPE *a, *b, *c;
static double avgtime[4] = {0}, maxtime[4] = {0};
static double mintime[4] = {FLT_MAX, FLT_MAX, FLT_MAX, FLT_MAX};

static char *label[4] = {"Copy:      ", "Scale:     ",
                         "Add:       ", "Triad:     "};

static double bytes[4];

typedef struct {
    int thread_id;
    int core_id;
    ssize_t start_idx;
    ssize_t end_idx;
    STREAM_TYPE scalar;
    int kernel;  /* 0=Copy, 1=Scale, 2=Add, 3=Triad */
} ThreadData;

// Barrier for thread synchronization
static pthread_barrier_t barrier;

/*-----------------------------------------------------------------------*/
/* FUNCTION PROTOTYPES                                                   */
/*-----------------------------------------------------------------------*/
double mysecond();
void checkSTREAMresults();
void* stream_thread_func(void* arg);
int set_thread_affinity(int core_id);
void run_test(TestConfig config);
void print_config(TestConfig config);
int get_core_for_thread(int thread_num, int num_cores, AffinityMode affinity);

/*-----------------------------------------------------------------------*/
/* MAIN                                                                  */
/*-----------------------------------------------------------------------*/
int main(int argc, char* argv[]) {
    int BytesPerWord = sizeof(STREAM_TYPE);
    
    /* Allocate arrays */
    a = (STREAM_TYPE*) malloc((STREAM_ARRAY_SIZE + OFFSET) * sizeof(STREAM_TYPE));
    b = (STREAM_TYPE*) malloc((STREAM_ARRAY_SIZE + OFFSET) * sizeof(STREAM_TYPE));
    c = (STREAM_TYPE*) malloc((STREAM_ARRAY_SIZE + OFFSET) * sizeof(STREAM_TYPE));
    
    if (!a || !b || !c) {
        printf("Failed to allocate memory!\n");
        return 1;
    }
    
    bytes[0] = 2 * sizeof(STREAM_TYPE) * STREAM_ARRAY_SIZE;
    bytes[1] = 2 * sizeof(STREAM_TYPE) * STREAM_ARRAY_SIZE;
    bytes[2] = 3 * sizeof(STREAM_TYPE) * STREAM_ARRAY_SIZE;
    bytes[3] = 3 * sizeof(STREAM_TYPE) * STREAM_ARRAY_SIZE;
    
    printf("=====================================================\n");
    printf("STREAM Benchmark with pthread and Cache Affinity\n");
    printf("=====================================================\n");
    printf("Array size = %llu (elements), Offset = %d (elements)\n",
           (unsigned long long) STREAM_ARRAY_SIZE, OFFSET);
    printf("Memory per array = %.1f MiB (= %.1f GiB).\n",
           BytesPerWord * ((double) STREAM_ARRAY_SIZE / 1024.0/1024.0),
           BytesPerWord * ((double) STREAM_ARRAY_SIZE / 1024.0/1024.0/1024.0));
    printf("Total memory required = %.1f MiB (= %.1f GiB).\n",
           (3.0 * BytesPerWord) * ((double) STREAM_ARRAY_SIZE / 1024.0/1024.),
           (3.0 * BytesPerWord) * ((double) STREAM_ARRAY_SIZE / 1024.0/1024./1024.));
    printf("Each kernel will be executed %d times.\n", NTIMES);
    printf("\n");
    
    /* Print CPU topology */
    printf("CPU L3 Cache Topology Configuration:\n");
    printf("  Cores sharing L3: [");
    for (int c = 0; c < cpu_topology.num_l3_cores; c++) {
        printf("%d", cpu_topology.l3_cores[c]);
        if (c < cpu_topology.num_l3_cores - 1) printf(", ");
    }
    printf("]\n");
    printf("  Cores NOT sharing L3: [");
    for (int c = 0; c < cpu_topology.num_no_l3_cores; c++) {
        printf("%d", cpu_topology.no_l3_cores[c]);
        if (c < cpu_topology.num_no_l3_cores - 1) printf(", ");
    }
    printf("]\n");
    printf("\n");
    
    /* Run all combinations: 1-8 cores x 1-8 threads per core */
    printf("\n=====================================================\n");
    printf("COMPREHENSIVE TEST: All Core/Thread Combinations\n");
    printf("=====================================================\n\n");
    
    for (int cores = 1; cores <= 8; cores++) {
        printf("\n#####################################################\n");
        printf("# TESTING WITH %d CORE%s\n", cores, cores > 1 ? "S" : "");
        printf("#####################################################\n\n");
        
        for (int threads = 1; threads <= 8; threads++) {
            TestConfig config;
            config.num_cores = cores;
            config.threads_per_core = threads;
            
            printf(">>> %d Core%s x %d Thread%s = %d Total Threads <<<\n\n",
                   cores, cores > 1 ? "s" : "",
                   threads, threads > 1 ? "s" : "",
                   cores * threads);
            
            printf("--- WITHOUT Cache Affinity ---\n");
            config.affinity = NO_AFFINITY;
            run_test(config);
            
            printf("\n--- WITH Cache Affinity ---\n");
            config.affinity = WITH_AFFINITY;
            run_test(config);
            
            printf("\n");
        }
    }
    
    free(a);
    free(b);
    free(c);
    
    return 0;
}

// RUN TEST WITH GIVEN CONFIGURATION

void run_test(TestConfig config) {
    int total_threads = config.num_cores * config.threads_per_core;
    pthread_t* threads = malloc(total_threads * sizeof(pthread_t));
    ThreadData* thread_data = malloc(total_threads * sizeof(ThreadData));
    double times[4][NTIMES];
    
    print_config(config);
    
    /* Initialize barrier */
    pthread_barrier_init(&barrier, NULL, total_threads);
    
    /* Initialize arrays */
    for (ssize_t j = 0; j < STREAM_ARRAY_SIZE; j++) {
        a[j] = 1.0;
        b[j] = 2.0;
        c[j] = 0.0;
    }
    
    /* Reset timing arrays */
    for (int i = 0; i < 4; i++) {
        avgtime[i] = 0.0;
        mintime[i] = FLT_MAX;
        maxtime[i] = 0.0;
    }
    
    /* Main timing loop */
    STREAM_TYPE scalar = 3.0;
    
    for (int iter = 0; iter < NTIMES; iter++) {
        /* Run all 4 kernels */
        for (int kernel = 0; kernel < 4; kernel++) {
            /* Setup thread data */
            ssize_t chunk_size = STREAM_ARRAY_SIZE / total_threads;
            
            for (int t = 0; t < total_threads; t++) {
                thread_data[t].thread_id = t;
                thread_data[t].core_id = get_core_for_thread(t, config.num_cores, config.affinity);
                thread_data[t].start_idx = t * chunk_size;
                thread_data[t].end_idx = (t == total_threads - 1) ? 
                                         STREAM_ARRAY_SIZE : (t + 1) * chunk_size;
                thread_data[t].scalar = scalar;
                thread_data[t].kernel = kernel;
            }
            
            /* Start timing */
            double start_time = mysecond();
            
            /* Create threads */
            for (int t = 0; t < total_threads; t++) {
                pthread_create(&threads[t], NULL, stream_thread_func, &thread_data[t]);
            }
            
            /* Wait for threads */
            for (int t = 0; t < total_threads; t++) {
                pthread_join(threads[t], NULL);
            }
            
            /* End timing */
            times[kernel][iter] = mysecond() - start_time;
        }
    }
    
    for (int iter = 1; iter < NTIMES; iter++) {
        for (int kernel = 0; kernel < 4; kernel++) {
            avgtime[kernel] += times[kernel][iter];
            mintime[kernel] = (times[kernel][iter] < mintime[kernel]) ? 
                             times[kernel][iter] : mintime[kernel];
            maxtime[kernel] = (times[kernel][iter] > maxtime[kernel]) ? 
                             times[kernel][iter] : maxtime[kernel];
        }
    }
    
    /* Print results */
    printf("Function    Best Rate MB/s  Avg time     Min time     Max time\n");
    for (int kernel = 0; kernel < 4; kernel++) {
        avgtime[kernel] = avgtime[kernel] / (double)(NTIMES - 1);
        printf("%s%12.1f  %11.6f  %11.6f  %11.6f\n", 
               label[kernel],
               1.0E-06 * bytes[kernel] / mintime[kernel],
               avgtime[kernel],
               mintime[kernel],
               maxtime[kernel]);
    }
    
    pthread_barrier_destroy(&barrier);
    free(threads);
    free(thread_data);
}

// THREAD FUNCTION
void* stream_thread_func(void* arg) {
    ThreadData* data = (ThreadData*)arg;
    
    /* Set thread affinity if core_id >= 0 */
    if (data->core_id >= 0) {
        set_thread_affinity(data->core_id);
    }
    
    /* Wait for all threads to be ready */
    pthread_barrier_wait(&barrier);
    
    /* Execute kernel */
    switch (data->kernel) {
        case 0:  /* Copy: c = a */
            for (ssize_t j = data->start_idx; j < data->end_idx; j++) {
                c[j] = a[j];
            }
            break;
            
        case 1:  /* Scale: b = scalar * c */
            for (ssize_t j = data->start_idx; j < data->end_idx; j++) {
                b[j] = data->scalar * c[j];
            }
            break;
            
        case 2:  /* Add: c = a + b */
            for (ssize_t j = data->start_idx; j < data->end_idx; j++) {
                c[j] = a[j] + b[j];
            }
            break;
            
        case 3:  /* Triad: a = b + scalar * c */
            for (ssize_t j = data->start_idx; j < data->end_idx; j++) {
                a[j] = b[j] + data->scalar * c[j];
            }
            break;
    }
    
    return NULL;
}

// SET THREAD AFFINITY
int set_thread_affinity(int core_id) {
    DWORD_PTR mask = (DWORD_PTR)1 << core_id;
    DWORD_PTR result = SetThreadAffinityMask(GetCurrentThread(), mask);
    return (result != 0) ? 0 : -1;
}

int get_core_for_thread(int thread_num, int num_cores, AffinityMode affinity) {
    if (affinity == NO_AFFINITY) {
        return -1;  /* No affinity set - let OS schedule anywhere */
    }
    
    /* WITH_AFFINITY: Use cores that share L3 cache */
    int core_idx = thread_num % num_cores;
    
    /* Use cores from the L3-sharing group */
    if (core_idx < cpu_topology.num_l3_cores) {
        return cpu_topology.l3_cores[core_idx];
    }
    
    /* If we need more cores than available in L3 group, wrap around */
    return cpu_topology.l3_cores[core_idx % cpu_topology.num_l3_cores];
}

// PRINT CONFIGURATION
void print_config(TestConfig config) {
    int total_threads = config.num_cores * config.threads_per_core;
    printf("Configuration: %d core(s) x %d thread(s) = %d total threads\n",
           config.num_cores, config.threads_per_core, total_threads);
    printf("Affinity: %s\n", 
           config.affinity == WITH_AFFINITY ? "ENABLED (cores share L3)" : "DISABLED");
    
    if (config.affinity == WITH_AFFINITY) {
        printf("Cores used: [");
        for (int t = 0; t < total_threads; t++) {
            int core = get_core_for_thread(t, config.num_cores, config.affinity);
            printf("%d", core);
            if (t < total_threads - 1) printf(", ");
        }
        printf("]\n");
    }
    printf("\n");
}

// TIMING FUNCTION
double mysecond() {
    struct timeval tp;
    gettimeofday(&tp, NULL);
    return ((double) tp.tv_sec + (double) tp.tv_usec * 1.e-6);
}

// VALIDATION (simplified)
void checkSTREAMresults() {
    /* Simplified validation - just check if values are reasonable */
    STREAM_TYPE aj, bj, cj, scalar;
    double epsilon;
    
    aj = 1.0;
    bj = 2.0;
    cj = 0.0;
    aj = 2.0E0 * aj;
    scalar = 3.0;
    
    for (int k = 0; k < NTIMES; k++) {
        cj = aj;
        bj = scalar * cj;
        cj = aj + bj;
        aj = bj + scalar * cj;
    }
    
    if (sizeof(STREAM_TYPE) == 4) {
        epsilon = 1.e-6;
    } else {
        epsilon = 1.e-13;
    }
    
    STREAM_TYPE aAvgErr = fabs(a[0] - aj);
    STREAM_TYPE bAvgErr = fabs(b[0] - bj);
    STREAM_TYPE cAvgErr = fabs(c[0] - cj);
    
    if (fabs(aAvgErr/aj) < epsilon && 
        fabs(bAvgErr/bj) < epsilon && 
        fabs(cAvgErr/cj) < epsilon) {
        printf("Solution Validates\n");
    } else {
        printf("Solution does NOT validate\n");
    }
}