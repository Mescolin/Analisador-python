import pandas as pd
from collections import defaultdict
import os

# === CONFIGURAÇÃO ===
ARQUIVO_COMPARACAO = "output/comparacao_ia_analistas.csv"
ARQUIVO_SAIDA = "output/analise_por_questao_geral.csv"

# === MAPEAMENTO DAS QUESTÕES ESPECÍFICAS PARA QUESTÕES GERAIS ===
mapa_qx_para_geral = {
    'Q1': 'Controle de Autenticação',
    'Q2': 'Controle de Autenticação',
    'Q3': 'Controle de Autenticação',
    'Q4': 'Controle de Autenticação',
    'Q5': 'Gerenciamento de Sessão',
    'Q6': 'Gerenciamento de Sessão',
    'Q7': 'Autorização e Acesso',
    'Q8': 'Segurança de Dados / API',
    'Q9': 'Funções Administrativas',
    'Q10': 'Entrada de Usuário / Ambiente',
    'Q11': 'Saída de Dados',
    'Q12': 'Serialização / Objetos',
    'Q13': 'Análise XML',
    'Q14': 'Desserialização',
    'Q15': 'Análise JSON',
    'Q16': 'Logs e Armazenamento',
    'Q17': 'Upload de Arquivos',
    'Q18': 'API RESTful'
}

# === CARREGAR DADOS ===
df = pd.read_csv(ARQUIVO_COMPARACAO)

# === AGRUPAR POR QUESTÃO GERAL ===
resumo = defaultdict(lambda: {"acertos": 0, "so_ia": 0, "so_humanos": 0})

for _, row in df.iterrows():
    ia = eval(row['marcacoes_ia']) if pd.notna(row['marcacoes_ia']) else []
    humanos = eval(row['marcacoes_analistas']) if pd.notna(row['marcacoes_analistas']) else []
    intersecao = set(ia) & set(humanos)
    so_ia = set(ia) - set(humanos)
    so_humanos = set(humanos) - set(ia)

    for q in intersecao:
        geral = mapa_qx_para_geral.get(q)
        if geral:
            resumo[geral]["acertos"] += 1
    for q in so_ia:
        geral = mapa_qx_para_geral.get(q)
        if geral:
            resumo[geral]["so_ia"] += 1
    for q in so_humanos:
        geral = mapa_qx_para_geral.get(q)
        if geral:
            resumo[geral]["so_humanos"] += 1

# === CONSTRUIR DATAFRAME FINAL ===
dados = []
for geral, valores in resumo.items():
    total = valores['acertos'] + valores['so_ia'] + valores['so_humanos']
    acuracia = round(valores['acertos'] / total * 100, 2) if total else 0
    dados.append({
        "questao_geral": geral,
        "acertos": valores['acertos'],
        "so_ia": valores['so_ia'],
        "so_humanos": valores['so_humanos'],
        "acuracia_percentual": acuracia
    })

df_resultado = pd.DataFrame(dados).sort_values(by="acuracia_percentual", ascending=False)
df_resultado.to_csv(ARQUIVO_SAIDA, index=False)
print(f"Análise por questão geral salva em: {ARQUIVO_SAIDA}")
