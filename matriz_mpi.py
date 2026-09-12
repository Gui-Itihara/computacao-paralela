from mpi4py import MPI
import random
import time
import sys

N = int(sys.argv[1])

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

if rank == 0:
    A = [[random.random() for _ in range(N)] for _ in range(N)]
    B = [[random.random() for _ in range(N)] for _ in range(N)]
else:
    A = None
    B = None

inicio = time.time()

A = comm.bcast(A, root=0)
B = comm.bcast(B, root=0)

linhas_por_processo = N // size
resto = N % size

if rank < resto:
    linha_inicio = rank * (linhas_por_processo + 1)
    linha_fim = linha_inicio + linhas_por_processo + 1
else:
    linha_inicio = rank * linhas_por_processo + resto
    linha_fim = linha_inicio + linhas_por_processo

C_local = []
for i in range(linha_inicio, linha_fim):
    linha = [0.0] * N
    for j in range(N):
        soma = 0.0
        for k in range(N):
            soma += A[i][k] * B[k][j]
        linha[j] = soma
    C_local.append(linha)

resultados = comm.gather(C_local, root=0)

if rank == 0:
    C = []
    for parte in resultados:
        C.extend(parte)
    fim = time.time()
    print(f"[MPI] N={N} | Processos={size} | Tempo: {(fim-inicio)*1000:.2f} ms")
