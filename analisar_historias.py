import os
import json
import pandas as pd
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
from typing import Dict, List, Set, Any, Tuple
import re

class UserStoryAnalyzer:
    """
    Classe para analisar histórias de usuário e requisitos ASVS associados.
    """
    
    def __init__(self, data_dir: str):
        """
        Inicializa o analisador com o diretório que contém os arquivos JSON.
        
        Args:
            data_dir: Caminho para o diretório contendo os arquivos JSON
        """
        self.data_dir = data_dir
        self.stories = []
        self.requirements_by_id = {}
        self.section_names = {}
        self.user_analysis = defaultdict(list)
        self.story_pattern = re.compile(r"g\d+(\w+)_(\d+)\.json")
    
    def load_stories(self) -> None:
        """
        Carrega todas as histórias de usuário dos arquivos JSON no diretório especificado,
        incluindo subdiretórios para diferentes analistas.
        """
        analysts_dirs = [d for d in os.listdir(self.data_dir) 
                        if os.path.isdir(os.path.join(self.data_dir, d))]
        
        total_files = 0
        
        # Se não houver subpastas, procurar arquivos diretamente no diretório principal
        if not analysts_dirs:
            files = [f for f in os.listdir(self.data_dir) if f.endswith('.json')]
            total_files += len(files)
            
            for filename in files:
                self._process_file(filename, os.path.join(self.data_dir, filename), None)
        else:
            # Processar arquivos nas subpastas de cada analista
            for analyst_dir in analysts_dirs:
                analyst_path = os.path.join(self.data_dir, analyst_dir)
                files = [f for f in os.listdir(analyst_path) if f.endswith('.json')]
                total_files += len(files)
                
                print(f"Processando {len(files)} arquivos do analista: {analyst_dir}")
                
                for filename in files:
                    self._process_file(filename, os.path.join(analyst_path, filename), analyst_dir)
        
        print(f"Total de {total_files} arquivos JSON processados de {len(analysts_dirs) if analysts_dirs else 1} analistas")
    
    def _process_file(self, filename: str, filepath: str, analyst_dir: str = None) -> None:
        """
        Processa um arquivo JSON individual.
        
        Args:
            filename: Nome do arquivo
            filepath: Caminho completo do arquivo
            analyst_dir: Nome do diretório do analista (se aplicável)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
            # Extrai identificador do analista e número da história
            match = self.story_pattern.match(filename)
            if match:
                analyst_id = match.group(1)
                story_number = match.group(2)
            else:
                # Fallback para caso o padrão não seja encontrado
                parts = filename.split('_')
                analyst_id = parts[0] if len(parts) > 0 else "unknown"
                story_number = parts[1].split('.')[0] if len(parts) > 1 else "unknown"
            
            # Se temos o nome do analista da pasta, usamos como prioridade
            if analyst_dir:
                analyst_id = analyst_dir
            
            # Adiciona metadados ao registro
            data['_metadata'] = {
                'filename': filename,
                'analyst_id': analyst_id,
                'story_number': story_number
            }
            
            self.stories.append(data)
            
            # Organiza por analista e número da história
            self.user_analysis[(analyst_id, story_number)].append(data)
            
            # Coleta informações sobre requisitos e seções
            self._extract_requirements_info(data)
            
        except json.JSONDecodeError:
            print(f"Erro ao processar o arquivo {filepath}: JSON inválido")
        except Exception as e:
            print(f"Erro ao processar o arquivo {filepath}: {str(e)}")
    
    def _extract_requirements_info(self, data: Dict) -> None:
        """
        Extrai informações sobre requisitos e seções do ASVS.
        
        Args:
            data: Dados da história de usuário
        """
        for question in data.get('questions', []):
            for specific_question in question.get('questoesEspecificas', []):
                for requirement in specific_question.get('requirements', []):
                    req_id = requirement.get('id_externo')
                    if req_id:
                        self.requirements_by_id[requirement['id']] = {
                            'id': requirement['id'],
                            'id_externo': req_id,
                            'descricao': requirement['descricao'],
                            'nivel': requirement.get('nivel', 'N/A'),
                            'secao_id': requirement.get('fk_Secao_id')
                        }
    
    def get_marked_requirements(self, story_data: Dict) -> List[Dict]:
        """
        Obtém todos os requisitos marcados em uma história.
        
        Args:
            story_data: Dados da história de usuário
            
        Returns:
            Lista de requisitos marcados
        """
        marked_requirements = []
        
        for question in story_data.get('questions', []):
            for specific_question in question.get('questoesEspecificas', []):
                for requirement in specific_question.get('requirements', []):
                    if requirement.get('marked', False):
                        marked_requirements.append(requirement)
        
        return marked_requirements
    
    def get_requirement_frequency(self) -> Dict[str, int]:
        """
        Calcula a frequência com que cada requisito foi marcado em todas as histórias.
        
        Returns:
            Dicionário com IDs externos de requisitos e suas frequências
        """
        req_count = Counter()
        
        for story in self.stories:
            marked_reqs = self.get_marked_requirements(story)
            for req in marked_reqs:
                req_count[req.get('id_externo')] += 1
        
        return dict(req_count)
    
    def get_story_requirement_matrix(self) -> pd.DataFrame:
        """
        Cria uma matriz de histórias de usuário x requisitos marcados.
        
        Returns:
            DataFrame com histórias nas linhas e requisitos nas colunas
        """
        # Obter todos os IDs externos dos requisitos
        all_req_ids = sorted(set(req['id_externo'] for req in self.requirements_by_id.values()))
        
        # Preparar dados para o DataFrame
        data = []
        
        for story in self.stories:
            story_id = story['userStory']['id']
            analyst_id = story['_metadata']['analyst_id']
            story_number = story['_metadata']['story_number']
            
            row = {
                'story_id': story_id,
                'analyst_id': analyst_id,
                'story_number': story_number,
                'what': story['userStory'].get('what', ''),
                'who': story['userStory'].get('who', ''),
                'why': story['userStory'].get('why', '')
            }
            
            # Marcar quais requisitos foram selecionados
            marked_reqs = self.get_marked_requirements(story)
            marked_req_ids = [req.get('id_externo') for req in marked_reqs]
            
            for req_id in all_req_ids:
                row[f'req_{req_id}'] = 1 if req_id in marked_req_ids else 0
            
            data.append(row)
        
        return pd.DataFrame(data)
    
    def get_analyst_agreement(self) -> pd.DataFrame:
        """
        Calcula o nível de concordância entre analistas para cada história.
        
        Returns:
            DataFrame com estatísticas de concordância
        """
        agreement_data = []
        
        # Agrupar por número da história
        stories_by_number = defaultdict(list)
        for story in self.stories:
            story_number = story['_metadata']['story_number']
            stories_by_number[story_number].append(story)
        
        # Para cada história, ver a concordância entre os analistas
        for story_number, story_variants in stories_by_number.items():
            # Pular se tivermos apenas um analista para esta história
            if len(story_variants) <= 1:
                continue
            
            # Coletar requisitos marcados por cada analista
            analyst_requirements = {}
            for story in story_variants:
                analyst_id = story['_metadata']['analyst_id']
                marked_reqs = set(req.get('id_externo') for req in self.get_marked_requirements(story))
                analyst_requirements[analyst_id] = marked_reqs
            
            # Se tivermos pelo menos 2 analistas
            if len(analyst_requirements) >= 2:
                # Calcular união e interseção de todos os requisitos marcados
                all_marked = set()
                common_marked = None
                
                for reqs in analyst_requirements.values():
                    all_marked.update(reqs)
                    if common_marked is None:
                        common_marked = reqs
                    else:
                        common_marked &= reqs
                
                if common_marked is None:
                    common_marked = set()
                
                # Calcular métricas de concordância
                total_requirements = len(all_marked)
                common_requirements = len(common_marked)
                
                if total_requirements > 0:
                    agreement_ratio = common_requirements / total_requirements
                else:
                    agreement_ratio = 1.0  # Se não há requisitos marcados, consideramos concordância total
                
                # Adicionar aos dados
                agreement_data.append({
                    'story_number': story_number,
                    'story_id': story_variants[0]['userStory']['id'],
                    'analysts_count': len(analyst_requirements),
                    'total_unique_requirements': total_requirements,
                    'common_requirements': common_requirements,
                    'agreement_ratio': agreement_ratio,
                    'what': story_variants[0]['userStory'].get('what', ''),
                    'who': story_variants[0]['userStory'].get('who', ''),
                    'why': story_variants[0]['userStory'].get('why', '')
                })
        
        return pd.DataFrame(agreement_data)
    
    def generate_report(self, output_dir: str = "./output") -> None:
        """
        Gera um relatório completo da análise.
        
        Args:
            output_dir: Diretório onde os arquivos de saída serão salvos
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 1. Carregar histórias se ainda não tiver carregado
        if not self.stories:
            self.load_stories()
        
        print(f"Analisando {len(self.stories)} histórias de usuário...")
        
        # 2. Estatísticas gerais
        total_stories = len(set(story['userStory']['id'] for story in self.stories))
        total_analysts = len(set(story['_metadata']['analyst_id'] for story in self.stories))
        total_requirements = len(set(req['id_externo'] for req in self.requirements_by_id.values()))
        total_marked = sum(len(self.get_marked_requirements(story)) for story in self.stories)
        
        general_stats = pd.DataFrame([{
            'total_unique_stories': total_stories,
            'total_analysts': total_analysts,
            'total_unique_requirements': total_requirements,
            'total_marked_requirements': total_marked,
            'avg_requirements_per_story': total_marked / len(self.stories) if self.stories else 0
        }])
        
        general_stats.to_csv(os.path.join(output_dir, "estatisticas_gerais.csv"), index=False)
        
        # 3. Frequências dos requisitos
        req_freq = self.get_requirement_frequency()
        req_freq_df = pd.DataFrame([
            {'requisito_id': req_id, 'frequencia': freq, 'descricao': self._get_requirement_description(req_id)}
            for req_id, freq in req_freq.items()
        ]).sort_values('frequencia', ascending=False)
        
        req_freq_df.to_csv(os.path.join(output_dir, "frequencia_requisitos.csv"), index=False)
        
        # 4. Matriz de histórias x requisitos
        matrix_df = self.get_story_requirement_matrix()
        matrix_df.to_csv(os.path.join(output_dir, "matriz_historias_requisitos.csv"), index=False)
        
        # 5. Concordância entre analistas
        agreement_df = self.get_analyst_agreement()
        agreement_df.to_csv(os.path.join(output_dir, "concordancia_analistas.csv"), index=False)
        
        # 6. Visualizações
        self._generate_visualizations(output_dir, req_freq_df, agreement_df)
        
        # 7. Relatório HTML
        self._generate_html_report(output_dir, general_stats, req_freq_df, agreement_df)
        
        print(f"Relatório gerado com sucesso no diretório: {output_dir}")
    
    def _get_requirement_description(self, req_id_externo: str) -> str:
        """Obtém a descrição de um requisito pelo ID externo."""
        for req in self.requirements_by_id.values():
            if req.get('id_externo') == req_id_externo:
                return req.get('descricao', 'Descrição não disponível')
        return 'Requisito não encontrado'
    
    def _generate_visualizations(self, output_dir: str, req_freq_df: pd.DataFrame, agreement_df: pd.DataFrame) -> None:
        """
        Gera visualizações a partir dos dados analisados.
        
        Args:
            output_dir: Diretório onde as visualizações serão salvas
            req_freq_df: DataFrame com frequências dos requisitos
            agreement_df: DataFrame com concordância entre analistas
        """
        # 1. Top 10 requisitos mais frequentes
        plt.figure(figsize=(12, 6))
        top_reqs = req_freq_df.head(10)
        plt.barh(top_reqs['requisito_id'], top_reqs['frequencia'])
        plt.xlabel('Frequência')
        plt.ylabel('ID do Requisito')
        plt.title('Top 10 Requisitos ASVS Mais Frequentes')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "top10_requisitos.png"))
        plt.close()
        
        # 2. Histograma de concordância
        if not agreement_df.empty:
            plt.figure(figsize=(10, 6))
            plt.hist(agreement_df['agreement_ratio'], bins=10, edgecolor='black')
            plt.xlabel('Nível de Concordância')
            plt.ylabel('Número de Histórias')
            plt.title('Distribuição do Nível de Concordância Entre Analistas')
            plt.savefig(os.path.join(output_dir, "histograma_concordancia.png"))
            plt.close()
    
    def _generate_html_report(self, output_dir: str, general_stats: pd.DataFrame, 
                              req_freq_df: pd.DataFrame, agreement_df: pd.DataFrame) -> None:
        """
        Gera um relatório HTML com os resultados da análise.
        
        Args:
            output_dir: Diretório onde o relatório será salvo
            general_stats: DataFrame com estatísticas gerais
            req_freq_df: DataFrame com frequências dos requisitos
            agreement_df: DataFrame com concordância entre analistas
        """
        html_content = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Relatório de Análise de Histórias de Usuário e Requisitos ASVS</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                }}
                h1, h2, h3 {{
                    color: #2c3e50;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin-bottom: 20px;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                .section {{
                    margin-bottom: 30px;
                }}
                .image-container {{
                    text-align: center;
                    margin: 20px 0;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                }}
            </style>
        </head>
        <body>
            <h1>Relatório de Análise de Histórias de Usuário e Requisitos ASVS</h1>
            
            <div class="section">
                <h2>Estatísticas Gerais</h2>
                <table>
                    <tr>
                        <th>Métrica</th>
                        <th>Valor</th>
                    </tr>
                    <tr>
                        <td>Total de Histórias Únicas</td>
                        <td>{general_stats['total_unique_stories'].values[0]}</td>
                    </tr>
                    <tr>
                        <td>Total de Analistas</td>
                        <td>{general_stats['total_analysts'].values[0]}</td>
                    </tr>
                    <tr>
                        <td>Total de Requisitos Únicos</td>
                        <td>{general_stats['total_unique_requirements'].values[0]}</td>
                    </tr>
                    <tr>
                        <td>Total de Requisitos Marcados</td>
                        <td>{general_stats['total_marked_requirements'].values[0]}</td>
                    </tr>
                    <tr>
                        <td>Média de Requisitos por História</td>
                        <td>{general_stats['avg_requirements_per_story'].values[0]:.2f}</td>
                    </tr>
                </table>
            </div>
            
            <div class="section">
                <h2>Top 10 Requisitos Mais Frequentes</h2>
                <div class="image-container">
                    <img src="top10_requisitos.png" alt="Top 10 Requisitos">
                </div>
                <table>
                    <tr>
                        <th>ID do Requisito</th>
                        <th>Frequência</th>
                        <th>Descrição</th>
                    </tr>
                    {self._generate_table_rows(req_freq_df.head(10), ['requisito_id', 'frequencia', 'descricao'])}
                </table>
            </div>
            
            <div class="section">
                <h2>Concordância Entre Analistas</h2>
                
                {"<div class='image-container'><img src='histograma_concordancia.png' alt='Histograma de Concordância'></div>" if not agreement_df.empty else ""}
                
                <h3>Histórias com Maior Concordância</h3>
                {"<table><tr><th>História</th><th>Analistas</th><th>Requisitos Únicos</th><th>Requisitos Comuns</th><th>Concordância</th></tr>" + 
                self._generate_table_rows(agreement_df.sort_values('agreement_ratio', ascending=False).head(5), 
                                         ['story_number', 'analysts_count', 'total_unique_requirements', 'common_requirements', 'agreement_ratio']) + 
                "</table>" if not agreement_df.empty else "<p>Não há dados suficientes para calcular concordância.</p>"}
                
                <h3>Histórias com Menor Concordância</h3>
                {"<table><tr><th>História</th><th>Analistas</th><th>Requisitos Únicos</th><th>Requisitos Comuns</th><th>Concordância</th></tr>" + 
                self._generate_table_rows(agreement_df.sort_values('agreement_ratio').head(5), 
                                         ['story_number', 'analysts_count', 'total_unique_requirements', 'common_requirements', 'agreement_ratio']) + 
                "</table>" if not agreement_df.empty else "<p>Não há dados suficientes para calcular concordância.</p>"}
            </div>
            
            <div class="section">
                <h2>Conclusões</h2>
                <p>A análise das {general_stats['total_unique_stories'].values[0]} histórias de usuário revelou que os requisitos de segurança 
                do ASVS são aplicados de forma variada pelos {general_stats['total_analysts'].values[0]} analistas. Em média, cada história 
                teve {general_stats['avg_requirements_per_story'].values[0]:.2f} requisitos associados a ela.</p>
                
                <p>Os requisitos mais frequentemente marcados estão relacionados a:
                {"<ul>" + "".join(f"<li><strong>{row['requisito_id']}</strong>: {row['descricao'][:100]}...</li>" 
                         for _, row in req_freq_df.head(3).iterrows()) + "</ul>"}
                </p>
                
                {"<p>A concordância entre analistas varia consideravelmente, com uma média de concordância de " + 
                f"{agreement_df['agreement_ratio'].mean():.2f} (onde 1.0 representa concordância total).</p>" 
                if not agreement_df.empty else "<p>Não há dados suficientes para determinar o nível médio de concordância entre analistas.</p>"}
                
                <p>Recomenda-se uma revisão das histórias com baixa concordância para estabelecer um entendimento 
                comum dos requisitos de segurança aplicáveis.</p>
            </div>
            
            <div class="section">
                <h2>Referências</h2>
                <p>Este relatório foi gerado automaticamente a partir da análise de histórias de usuário 
                e requisitos ASVS. Os dados completos estão disponíveis nos arquivos CSV gerados junto com este relatório.</p>
                <ul>
                    <li>estatisticas_gerais.csv - Estatísticas gerais da análise</li>
                    <li>frequencia_requisitos.csv - Frequência de cada requisito nas histórias</li>
                    <li>matriz_historias_requisitos.csv - Matriz completa de histórias e requisitos</li>
                    <li>concordancia_analistas.csv - Análise de concordância entre analistas</li>
                </ul>
            </div>
            
            <footer>
                <p>Gerado em: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            </footer>
        </body>
        </html>
        """
        
        with open(os.path.join(output_dir, "relatorio.html"), 'w', encoding='utf-8') as file:
            file.write(html_content)
    
    def _generate_table_rows(self, df: pd.DataFrame, columns: List[str]) -> str:
        """Gera linhas HTML para uma tabela a partir de um DataFrame."""
        rows = ""
        for _, row in df.iterrows():
            rows += "<tr>"
            for col in columns:
                value = row[col]
                if isinstance(value, float) and col == 'agreement_ratio':
                    value = f"{value:.2f}"
                rows += f"<td>{value}</td>"
            rows += "</tr>"
        return rows


def main():
    """Função principal para executar a análise."""
    import argparse
    
    # Configurar o parser de argumentos
    parser = argparse.ArgumentParser(description='Analisador de Histórias de Usuário e Requisitos ASVS')
    parser.add_argument('--input', '-i', type=str, default='user_stories',
                        help='Diretório que contém os arquivos JSON ou pastas dos analistas (padrão: user_stories)')
    parser.add_argument('--output', '-o', type=str, default='output',
                        help='Diretório onde os resultados serão salvos (padrão: output)')
    
    args = parser.parse_args()
    
    data_dir = args.input
    output_dir = args.output
    
    # Verificar se o diretório de entrada existe
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Diretório {data_dir} criado. Por favor, coloque os arquivos JSON nesse diretório.")
        return
    
    # Criar e executar o analisador
    analyzer = UserStoryAnalyzer(data_dir)
    analyzer.load_stories()
    analyzer.generate_report(output_dir=output_dir)
    
    print(f"Análise concluída. Os resultados estão no diretório '{output_dir}'.")


if __name__ == "__main__":
    main()
