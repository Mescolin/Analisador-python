import pandas as pd
import os
from jinja2 import Template

TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Relatório de Análise - ASVS</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h2 { color: #2c3e50; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #eee; }
        img { max-width: 100%; height: auto; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Relatório de Análise de Histórias de Usuário com ASVS</h1>

    <h2>Estatísticas Gerais</h2>
    {{ estatisticas_gerais }}

    <h2>Frequência de Requisitos Marcados</h2>
    {{ freq_requisitos }}

    <h2>Concordância entre Analistas</h2>
    {{ concordancia }}

    <h2>Detalhes por História (Interseção e União)</h2>
    {{ detalhes_historia }}

    <h2>Marcações por Analista e História</h2>
    {{ analista_historia }}
    <img src="por_analista_historia_grafico.png" alt="Gráfico - Frequência por Questão Geral">

    <h2>Convergência por Questão Geral</h2>
    {{ convergencia }}
</body>
</html>
"""

def gerar_relatorio_html(output_dir="output"):
    def render_df(file):
        return pd.read_csv(os.path.join(output_dir, file)).to_html(index=False, classes='tabela')

    html = Template(TEMPLATE).render(
        estatisticas_gerais=render_df("estatisticas_gerais.csv"),
        freq_requisitos=render_df("frequencia_requisitos.csv"),
        concordancia=render_df("concordancia_analistas.csv"),
        detalhes_historia=render_df("detalhes_por_historia.csv"),
        analista_historia=render_df("por_analista_historia.csv"),
        convergencia=render_df("convergencia_questao_geral.csv")
    )

    path = os.path.join(output_dir, "relatorio_analise.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Relatório HTML salvo em: {path}")

if __name__ == "__main__":
    gerar_relatorio_html()
