#include <stdio.h>
#include <pthread.h>
#include <stdlib.h>

#define NUM_THREADS 4
#define VECTOR_SIZE 1000000

int* vector;
long long global_sum = 0;

typedef struct {
    int thread_id;
    int start;
    int end;
} ThreadArgs;

void* sum_worker_fixed(void* args) {
    ThreadArgs* data =(ThreadArgs*) args;
    long long* local_sum = (long long*)malloc(sizeof(long long));
    *local_sum =0;
    for (int i = data->start; i < data-> end; i++) {
        *local_sum += vector[i];
    }
    free(data);
    return(void*)local_sum;
}

int main() {
    pthread_t threads[NUM_THREADS];

    vector = malloc(sizeof(int)* VECTOR_SIZE);
    long long expected_sum =0;
    for(int i =0; i<VECTOR_SIZE;i++){
        vector[i] = 1;
        expected_sum +=1;
    }
    int chunk_size = VECTOR_SIZE/NUM_THREADS;
    for (long i = 0; i < NUM_THREADS; i++) {
        ThreadArgs* args= (ThreadArgs*)malloc(sizeof(ThreadArgs));
        args->thread_id =i;
        args-> start = i*chunk_size;
        args-> end = (i ==NUM_THREADS -1) ? VECTOR_SIZE : (i+1) * chunk_size;
        pthread_create(&threads[i], NULL, sum_worker_fixed, args);
    }
    long long final_sum =0;
    // Esperar todas as threads terminarem
    for (int i = 0; i < NUM_THREADS; ++i) {
        void* return_value_ptr = NULL;
        pthread_join(threads[i], &return_value_ptr);
        long long* partial_sum_ptr= (long long*) return_value_ptr;
        final_sum += *partial_sum_ptr;
        printf("Thread %d retornou a soma parcial: %lld\n", i, *partial_sum_ptr);
        free(partial_sum_ptr);
    }

    printf("\n--- Resultados ---\n");
    printf("Soma Final calculada: %lld\n", final_sum);
    printf("Soma esperada:          %lld\n", expected_sum);
    
    if (final_sum == expected_sum) {
        printf("Resultado correto, a condição de corrida foi eliminada");
    } else {
        printf("Erro\n");
    }
    
    return 0;
}