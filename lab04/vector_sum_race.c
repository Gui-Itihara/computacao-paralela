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

void* sum_worker (void* args) {
    ThreadArgs* data =(ThreadArgs*) args;
    long long local_sum =0;
    
    for (int i = data->start; i < data-> end; ++i) {
        local_sum += vector[i];
    }
    global_sum += local_sum;
    pthread_exit (NULL);
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
    for (long i = 0; i < NUM_THREADS; ++i) {
        ThreadArgs* args= (ThreadArgs*)malloc(sizeof(ThreadArgs));
        args->thread_id =i;
        args-> start = i*chunk_size;
        args-> end = (i ==NUM_THREADS -1) ? VECTOR_SIZE : (i+1) * chunk_size;
        pthread_create(&threads[i], NULL, sum_worker, args);
    }

    // Esperar todas as threads terminarem
    for (int i = 0; i < NUM_THREADS; ++i) {
        pthread_join(threads[i], NULL);
    }

    printf("\n--- Resultados ---\n");
    printf("Soma Global calculada: %lld\n", global_sum);
    printf("Soma esperada:          %lld\n", expected_sum);
    
    if (global_sum != expected_sum) {
        printf("Diferenca: %lld. CONDICAO DE CORRIDA DETECTADA!\n", expected_sum - global_sum);
    } else {
        printf("Resultado correto!\n");
    }
    
    return 0;
}