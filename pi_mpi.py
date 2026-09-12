from mpi4py import MPI
import random
import time

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

N_TOTAL = 10000000
N_local = N_TOTAL // size

inicio = time.time()

dentro_local = 0
for _ in range(N_local):
    x = random.random()
    y = random.random()
    if x*x + y*y <= 1:
        dentro_local += 1

total_dentro = comm.reduce(dentro_local, op=MPI.SUM, root=0)

if rank == 0:
    pi = 4 * total_dentro / N_TOTAL
    fim = time.time()
    print(f"[MPI] PI aproximado: {pi}")
    print(f"[MPI] Processos={size} | Tempo: {(fim-inicio)*1000:.2f} ms")
