import pandas as pd
import os
import json

# === CONFIGURAÇÕES ===
CAMINHO_PLANILHA_IA = "Planilha/resultado-maju.xlsx"
DIRETORIO_ANALISES = "output"  # Onde estão os arquivos CSV dos analistas
ARQUIVO_ANALISTA = "por_analista_historia.csv"  # Deve ter story_number e specific_question

# === CARREGAR MARCAÇÕES DA IA ===
def carregar_marcacoes_ia(xlsx_path):
    xls = pd.ExcelFile(xlsx_path)
    ia_por_historia = {}

    for sheet in xls.sheet_names:
        historia_num = int(sheet.replace("H", ""))
        try:
            df = xls.parse(sheet)
            if 'Resultados' in df.columns:
                linha_ia = df[df.iloc[:, 0].astype(str).str.upper() == 'IA']
                if not linha_ia.empty:
                    q_cols = [col for col in df.columns if col.startswith('Q') and col[1:].isdigit()]
                    marcada = [col for col in q_cols if int(linha_ia.iloc[0][col]) == 1]
                    ia_por_historia[historia_num] = sorted(marcada)
        except Exception as e:
            print(f"Erro ao processar {sheet}: {e}")

    return ia_por_historia

# === CARREGAR MARCAÇÕES DOS ANALISTAS ===
def carregar_marcacoes_analistas(csv_path):
    df = pd.read_csv(csv_path)
    marcacoes = {}
    for _, row in df.iterrows():
        historia = int(row['story_number'])
        qe = row['specific_question']
        if pd.notna(qe):
            if historia not in marcacoes:
                marcacoes[historia] = set()
            if isinstance(qe, str):
                matches = pd.Series(qe).str.extractall(r'(Q\d{1,2})')[0].dropna().tolist()
                marcacoes[historia].update(matches)
    return marcacoes

# === COMPARAR ===
def comparar(ia, analistas):
    historias = sorted(set(ia.keys()) | set(analistas.keys()))
    resultados = []
    for h in historias:
        q_ia = set(ia.get(h, []))
        q_an = set(analistas.get(h, []))
        resultados.append({
            'story_number': h,
            'marcacoes_ia': sorted(q_ia),
            'marcacoes_analistas': sorted(q_an),
            'intersecao': sorted(q_ia & q_an),
            'so_ia': sorted(q_ia - q_an),
            'so_analistas': sorted(q_an - q_ia),
            'acuracia': round(len(q_ia & q_an) / len(q_ia) * 100, 2) if q_ia else 0.0
        })
    return pd.DataFrame(resultados)

# === EXECUTAR ===
def main():
    ia = carregar_marcacoes_ia(CAMINHO_PLANILHA_IA)
    analistas = carregar_marcacoes_analistas(os.path.join(DIRETORIO_ANALISES, ARQUIVO_ANALISTA))
    comparacao = comparar(ia, analistas)
    output_path = os.path.join(DIRETORIO_ANALISES, "comparacao_ia_analistas.csv")
    comparacao.to_csv(output_path, index=False)
    print(f"Arquivo gerado: {output_path}")

if __name__ == "__main__":
    main()
