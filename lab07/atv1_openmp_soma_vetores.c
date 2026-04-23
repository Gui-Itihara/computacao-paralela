/*
 * Arquivo: omp_soma_vetores.c
 * ----------------------------
 * Objetivo: Demonstrar a simplicidade de paralelizar um laço com OpenMP.
 * O programa calcula C = A + B para vetores grandes.
 *
 * Como compilar e executar:
 * $ gcc -o soma_vetores -fopenmp omp_soma_vetores.c
 * $ export OMP_NUM_THREADS=4
 * $ ./soma_vetores
 */

#include <stdio.h>
#include <stdlib.h>
#include <omp.h>

#define N 20000000 // Tamanho dos vetores

// Alocação estática para evitar estouro da pilha (stack overflow)
double a[N], b[N], c[N];

int main() {
    double start_time, end_time;

    // --- 1. Inicialização dos Vetores ---
    // Este laço também pode ser paralelizado para acelerar a inicialização.
    printf("Inicializando vetores...\n");
    #pragma omp parallel for
    for (int i = 0; i < N; i++) {
        a[i] = 1.0;
        b[i] = 2.0;
    }

    // --- 2. Soma Paralela ---
    printf("Calculando a soma paralela...\n");
    start_time = omp_get_wtime();

    // A MÁGICA ACONTECE AQUI!
    // Esta única diretiva instrui o OpenMP a dividir as iterações do laço 'for'
    // entre as threads disponíveis. O compilador cuida de todo o trabalho pesado.
    #pragma omp parallel for
    for (int i = 0; i < N; i++) {
        c[i] = a[i] + b[i];
    }

    end_time = omp_get_wtime();
    printf("Tempo de execução paralela: %f segundos\n", end_time - start_time);

    // --- Comparação de Simplicidade com Pthreads (em comentário) ---
    /*
     * Análise de Simplicidade vs. Pthreads:
     *
     * Para fazer o mesmo com Pthreads, precisaríamos de um código muito mais complexo:
     * 1. Definir uma struct para passar os argumentos para cada thread (ponteiros
     * para os vetores e os limites de início/fim do laço).
     * 2. Escrever uma função separada para a thread (ex: `void* soma_parcial(void* args)`).
     * 3. Na função `main`, criar um array de `pthread_t` para gerenciar as threads.
     * 4. Iniciar um laço para chamar `pthread_create` para cada thread, passando os
     * argumentos corretos.
     * 5. Iniciar outro laço para chamar `pthread_join`, esperando todas as threads
     * terminarem.
     * 6. Lidar com o gerenciamento de memória e a passagem de dados.
     *
     * Com OpenMP, uma única linha (#pragma omp parallel for) substitui tudo isso.
     * É drasticamente mais simples e produtivo para paralelismo de dados.
     */

    return 0;
}