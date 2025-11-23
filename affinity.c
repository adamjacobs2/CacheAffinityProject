#define _GNU_SOURCE
#include "pthread.h"
#include <stdio.h>
#include <unistd.h>
#include <time.h>

#define SIZE 100000000
int a[SIZE];


void* thread_function(){
    for(int i = 0; i < SIZE; i++){
        a[i] = i;
    }
}


int main(){
    printf("CPU Affinity demo\n");
    // creating the variables for the threads
    pthread_t thread1; 
    pthread_t thread2;

    // create variable for cpu sets, initialize them to be an empty set, and add the desired cpus to each set
    cpu_set_t  cpusA;
    CPU_ZERO(&cpusA);
    CPU_SET(10, &cpusA);
    CPU_SET(11, &cpusA);

    cpu_set_t  cpusB;
    CPU_ZERO(&cpusB);
    CPU_SET(0, &cpusB);
    CPU_SET(1, &cpusB);

    // variables for timing (using clock() needs to use clock_t type while using time() needs to use time_t type)
    time_t start_t1,end_t1, start_t2, end_t2;
    
    

    int id1 = 1;
    int id2 = 2;

    // create the thread, assingle the function to be executed and its argument
    start_t1=clock();
    if (pthread_create(&thread1, NULL, thread_function, (void *)&id1) != 0) {
        perror("Failed to create thread 1");
        return -1;
    }

    // set the affinity of the thread to the desired cpu set
    pthread_setaffinity_np(thread1, sizeof(cpusA), &cpusA);

    // wait for the thread to finish and store the end time
    if (pthread_join(thread1, NULL) != 0) {
        perror("Failed to join thread 1");
        return -1;
    }
    end_t1 = clock();

    // create the second thread, assign the function to be executed and its argument
    start_t2=clock();
    if (pthread_create(&thread2, NULL, thread_function, (void *)&id2) != 0) {
        perror("Failed to create thread 2");
        return -1;
    }

    // set the affinity of the thread to the desired cpu set
     pthread_setaffinity_np(thread2, sizeof(cpusA), &cpusA);

    // wait for the thread to finish and store the end time
     if (pthread_join(thread2, NULL) != 0) {
        perror("Failed to join thread 1");
        return -1;
    }


    //after the user defined function does its work
    end_t2=clock();
    int t1 =(end_t1-start_t1);
    int t2 =(end_t2-start_t2);
    
    //time_t elapsed = time(timer);
    printf("Thread 1 has finished %d cycles.\n", t1);
    printf("Thread 2 has finished %d cycles.\n", t2);
}

