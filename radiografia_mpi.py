from mpi4py import MPI
import numpy as np
import time
import sys

# =========================================================
# Inicialização do ambiente MPI (Etapa 1)
# =========================================================
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Permite passar o tamanho da imagem e ligar/desligar o atraso artificial
# por linha de comando:
# mpirun ... python3 radiografia_mpi.py <linhas> <colunas> <com_atraso: 0 ou 1>
ROWS = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
COLS = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
SIMULAR_ATRASO = bool(int(sys.argv[3])) if len(sys.argv) > 3 else True

LIMIAR_LEVE = 200
LIMIAR_ALTO = 230
PERCENTUAL_CRITICO = 5.0  # % de pixels suspeitos para faixa ser "crítica"


# =========================================================
# Etapa 2 – Geração da radiografia simulada (somente rank 0)
# =========================================================
def gerar_radiografia(rows, cols):
    """
    Gera uma radiografia simulada com um padrão coerente:
      - fundo externo do corpo: bem escuro (0-25)
      - região central do tórax (tecido mole): tons intermediários (60-100)
      - dois pulmões (esquerdo e direito) dentro do tórax: mais escuros (20-55)
      - manchas claras artificiais dentro dos pulmões simulando áreas suspeitas
    """
    img = np.random.randint(0, 25, size=(rows, cols)).astype(np.int32)

    r0, r1 = int(rows * 0.05), int(rows * 0.95)
    c0, c1 = int(cols * 0.10), int(cols * 0.90)
    img[r0:r1, c0:c1] = np.random.randint(60, 100, size=(r1 - r0, c1 - c0))

    le0, le1 = c0, c0 + (c1 - c0) // 2 - int(cols * 0.03)
    img[r0:r1, le0:le1] = np.random.randint(20, 55, size=(r1 - r0, le1 - le0))

    rd0, rd1 = c0 + (c1 - c0) // 2 + int(cols * 0.03), c1
    img[r0:r1, rd0:rd1] = np.random.randint(20, 55, size=(r1 - r0, rd1 - rd0))

    n_manchas = max(4, (rows * cols) // 200000)
    for _ in range(n_manchas):
        lado = np.random.choice(["esq", "dir"])
        if lado == "esq":
            cy = np.random.randint(r0, r1)
            cx = np.random.randint(le0, le1)
        else:
            cy = np.random.randint(r0, r1)
            cx = np.random.randint(rd0, rd1)
        raio = np.random.randint(max(2, rows // 100), max(3, rows // 40))
        y0, y1 = max(0, cy - raio), min(rows, cy + raio)
        x0, x1 = max(0, cx - raio), min(cols, cx + raio)
        intensidade = np.random.randint(200, 256)
        img[y0:y1, x0:x1] = np.clip(
            img[y0:y1, x0:x1] + np.random.randint(intensidade - 30, intensidade, size=(y1 - y0, x1 - x0)),
            0, 255
        )

    return np.clip(img, 0, 255).astype(np.int32)


radiografia = None
if rank == 0:
    print(f"\n=== Análise Distribuída de Radiografia (MPI) ===")
    print(f"Gerando radiografia simulada {ROWS}x{COLS} no processo root...\n")
    radiografia = gerar_radiografia(ROWS, COLS)

# =========================================================
# Etapa 3 – Parâmetros de análise + Broadcast (MPI_Bcast)
# =========================================================
parametros = None
if rank == 0:
    parametros = {
        "rows": ROWS,
        "cols": COLS,
        "limiar_leve": LIMIAR_LEVE,
        "limiar_alto": LIMIAR_ALTO,
        "percentual_critico": PERCENTUAL_CRITICO,
    }

parametros = comm.bcast(parametros, root=0)

ROWS = parametros["rows"]
COLS = parametros["cols"]
LIMIAR_LEVE = parametros["limiar_leve"]
LIMIAR_ALTO = parametros["limiar_alto"]
PERCENTUAL_CRITICO = parametros["percentual_critico"]

# =========================================================
# Etapa 4 – Barrier inicial (MPI_Barrier)
# Garante que todos os processos já têm os parâmetros
# antes de iniciar a etapa de análise.
# =========================================================
comm.Barrier()
t_inicio = MPI.Wtime()

# =========================================================
# Etapa 5 – Divisão da radiografia com Scatter (MPI_Scatter)
# Divide por faixas horizontais (linhas). Trata o caso em que
# o número de linhas não é divisível pelo número de processos:
# os primeiros (ROWS % size) processos recebem uma linha extra.
# =========================================================
partes = None
faixas = None  # guarda (linha_inicio, linha_fim) de cada processo
if rank == 0:
    base = ROWS // size
    resto = ROWS % size
    partes = []
    faixas = []
    linha_atual = 0
    for p in range(size):
        n_linhas = base + (1 if p < resto else 0)
        inicio, fim = linha_atual, linha_atual + n_linhas
        partes.append(radiografia[inicio:fim, :])
        faixas.append((inicio, fim))
        linha_atual = fim

faixas = comm.bcast(faixas, root=0)  # todo processo sabe sua própria faixa (e das outras, se precisar)
minha_faixa = comm.scatter(partes, root=0)
linha_inicio, linha_fim = faixas[rank]

# =========================================================
# Etapa 6 – Análise local de cada processo
# =========================================================
meio_col = COLS // 2  # divide colunas em pulmão esquerdo / direito

pixels_analisados = minha_faixa.size
soma_local = int(minha_faixa.sum())
media_local = soma_local / pixels_analisados if pixels_analisados > 0 else 0
max_local = int(minha_faixa.max()) if pixels_analisados > 0 else 0

suspeitos_local = int(np.sum(minha_faixa > LIMIAR_LEVE))
altamente_suspeitos_local = int(np.sum(minha_faixa > LIMIAR_ALTO))

parte_esquerda = minha_faixa[:, :meio_col]
parte_direita = minha_faixa[:, meio_col:]
suspeitos_esquerda_local = int(np.sum(parte_esquerda > LIMIAR_LEVE))
suspeitos_direita_local = int(np.sum(parte_direita > LIMIAR_LEVE))

# =========================================================
# Etapa 7 – Classificação local da faixa analisada
# Regra objetiva adotada:
#   percentual_suspeito_local = suspeitos_local / pixels_analisados * 100
#   >= PERCENTUAL_CRITICO            -> "crítica"
#   >= PERCENTUAL_CRITICO / 2        -> "atenção"
#   caso contrário                   -> "normal"
# =========================================================
percentual_suspeito_local = (suspeitos_local / pixels_analisados * 100) if pixels_analisados > 0 else 0

if percentual_suspeito_local >= PERCENTUAL_CRITICO:
    classificacao_local = "crítica"
elif percentual_suspeito_local >= PERCENTUAL_CRITICO / 2:
    classificacao_local = "atenção"
else:
    classificacao_local = "normal"

# =========================================================
# Etapa 8 – Simulação de cluster heterogêneo
# Processos de rank ímpar sofrem atraso artificial
# (pode ser desligado passando 0 como terceiro argumento).
# =========================================================
if SIMULAR_ATRASO and rank % 2 == 1:
    time.sleep(1.5)

# =========================================================
# Etapa 9 – Barrier antes da consolidação (MPI_Barrier)
# =========================================================
comm.Barrier()

# =========================================================
# Etapa 10 – Consolidação numérica com Reduce (MPI_Reduce)
# =========================================================
total_pixels = comm.reduce(pixels_analisados, op=MPI.SUM, root=0)
soma_global = comm.reduce(soma_local, op=MPI.SUM, root=0)
total_suspeitos = comm.reduce(suspeitos_local, op=MPI.SUM, root=0)
total_altamente_suspeitos = comm.reduce(altamente_suspeitos_local, op=MPI.SUM, root=0)
total_suspeitos_esquerda = comm.reduce(suspeitos_esquerda_local, op=MPI.SUM, root=0)
total_suspeitos_direita = comm.reduce(suspeitos_direita_local, op=MPI.SUM, root=0)
maior_intensidade_global = comm.reduce(max_local, op=MPI.MAX, root=0)

# =========================================================
# Etapa 11 – Coleta de estatísticas detalhadas com Gather (MPI_Gather)
# =========================================================
relatorio_local = {
    "rank": rank,
    "linha_inicio": linha_inicio,
    "linha_fim": linha_fim,
    "pixels_analisados": pixels_analisados,
    "suspeitos": suspeitos_local,
    "altamente_suspeitos": altamente_suspeitos_local,
    "max_local": max_local,
    "media_local": round(media_local, 2),
    "classificacao": classificacao_local,
}

relatorios = comm.gather(relatorio_local, root=0)

# =========================================================
# Etapa 12 – Relatório final do processo root
# =========================================================
if rank == 0:
    t_fim = MPI.Wtime()
    tempo_total_ms = (t_fim - t_inicio) * 1000

    media_global = soma_global / total_pixels
    percentual_suspeito_global = total_suspeitos / total_pixels * 100

    if total_suspeitos_esquerda > total_suspeitos_direita:
        lado_maior = "ESQUERDO"
    elif total_suspeitos_direita > total_suspeitos_esquerda:
        lado_maior = "DIREITO"
    else:
        lado_maior = "EMPATE"

    if percentual_suspeito_global < 1.0:
        classificacao_geral = "SEM INDÍCIOS RELEVANTES"
    elif percentual_suspeito_global < 5.0:
        classificacao_geral = "ATENÇÃO CLÍNICA"
    else:
        classificacao_geral = "ALTA CONCENTRAÇÃO DE ÁREAS SUSPEITAS"

    print("=" * 65)
    print("RELATÓRIO FINAL – ANÁLISE DISTRIBUÍDA DE RADIOGRAFIA")
    print("=" * 65)
    print(f"Tamanho da imagem:            {ROWS} x {COLS} pixels")
    print(f"Quantidade de processos MPI:  {size}")
    print(f"Limiar de suspeita leve:      > {LIMIAR_LEVE}")
    print(f"Limiar de suspeita alta:      > {LIMIAR_ALTO}")
    print(f"Percentual crítico (faixa):   {PERCENTUAL_CRITICO}%")
    print(f"Atraso artificial (ranks ímpares): {'ATIVADO' if SIMULAR_ATRASO else 'desativado'}")
    print(f"Tempo total de execução:      {tempo_total_ms:.2f} ms")
    print("-" * 65)
    print("ESTATÍSTICAS GLOBAIS")
    print(f"Total de pixels analisados:   {total_pixels}")
    print(f"Intensidade média global:     {media_global:.2f}")
    print(f"Maior intensidade global:     {maior_intensidade_global}")
    print(f"Total de pixels suspeitos:    {total_suspeitos}")
    print(f"Total altamente suspeitos:    {total_altamente_suspeitos}")
    print(f"Percentual da imagem suspeito:{percentual_suspeito_global:.4f}%")
    print("-" * 65)
    print("COMPARAÇÃO ENTRE OS LADOS")
    print(f"Suspeitos pulmão esquerdo:    {total_suspeitos_esquerda}")
    print(f"Suspeitos pulmão direito:     {total_suspeitos_direita}")
    print(f"Lado com maior concentração:  {lado_maior}")
    print("-" * 65)
    print("ESTATÍSTICAS POR PROCESSO")
    for r in relatorios:
        print(
            f"  Rank {r['rank']}: linhas [{r['linha_inicio']}:{r['linha_fim']}] | "
            f"pixels={r['pixels_analisados']} | suspeitos={r['suspeitos']} | "
            f"alt.suspeitos={r['altamente_suspeitos']} | max_local={r['max_local']} | "
            f"classificação={r['classificacao']}"
        )
    print("-" * 65)
    print(f"CLASSIFICAÇÃO GERAL DO EXAME: {classificacao_geral}")
    print("=" * 65)
