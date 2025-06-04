import os
import json
import pandas as pd
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
from typing import Dict, List, Set, Any, Tuple
import re

class UserStoryAnalyzer:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.stories = []
        self.requirements_by_id = {}
        self.section_names = {}
        self.user_analysis = defaultdict(list)
        self.story_pattern = re.compile(r"g\d+(\w+)_(\d+)\.json")

    def load_stories(self) -> None:
        analysts_dirs = [d for d in os.listdir(self.data_dir) 
                         if os.path.isdir(os.path.join(self.data_dir, d))]

        total_files = 0
        if not analysts_dirs:
            files = [f for f in os.listdir(self.data_dir) if f.endswith('.json')]
            total_files += len(files)
            for filename in files:
                self._process_file(filename, os.path.join(self.data_dir, filename), None)
        else:
            for analyst_dir in analysts_dirs:
                analyst_path = os.path.join(self.data_dir, analyst_dir)
                files = [f for f in os.listdir(analyst_path) if f.endswith('.json')]
                total_files += len(files)
                print(f"Processando {len(files)} arquivos do analista: {analyst_dir}")
                for filename in files:
                    self._process_file(filename, os.path.join(analyst_path, filename), analyst_dir)

        print(f"Total de {total_files} arquivos JSON processados de {len(analysts_dirs) if analysts_dirs else 1} analistas")

    def _process_file(self, filename: str, filepath: str, analyst_dir: str = None) -> None:
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                data = json.load(file)

            match = self.story_pattern.match(filename)
            if match:
                analyst_id = match.group(1)
                story_number = match.group(2)
            else:
                parts = filename.split('_')
                analyst_id = parts[0] if len(parts) > 0 else "unknown"
                story_number = parts[1].split('.')[0] if len(parts) > 1 else "unknown"

            if analyst_dir:
                analyst_id = analyst_dir

            data['_metadata'] = {
                'filename': filename,
                'analyst_id': analyst_id,
                'story_number': story_number
            }

            self.stories.append(data)
            self.user_analysis[(analyst_id, story_number)].append(data)
            self._extract_requirements_info(data)

        except json.JSONDecodeError:
            print(f"Erro ao processar o arquivo {filepath}: JSON inválido")
        except Exception as e:
            print(f"Erro ao processar o arquivo {filepath}: {str(e)}")

    def _extract_requirements_info(self, data: Dict) -> None:
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

    def get_requirement_frequency(self) -> Dict[str, int]:

        #Calcula a frequência com que cada requisito foi marcado em todas as histórias.

        req_count = Counter()
        for story in self.stories:
            marked_reqs = self.get_marked_requirements(story)
            for req in marked_reqs:
                req_count[req.get('id_externo')] += 1
        return dict(req_count)

    def get_marked_requirements(self, story_data: Dict) -> List[Dict]:
        marked_requirements = []
        for question in story_data.get('questions', []):
            for specific_question in question.get('questoesEspecificas', []):
                for requirement in specific_question.get('requirements', []):
                    if requirement.get('marked', False):
                        marked = requirement.copy()
                        marked['specific_question'] = specific_question.get('question', {}).get('descricao', '')
                        marked['general_question'] = question.get('question', {}).get('descricao', '')
                        marked_requirements.append(marked)
        return marked_requirements

    def export_detalhes_por_analista_historia(self, output_path: str = "./output/por_analista_historia.csv") -> None:
        registros = []
        for story in self.stories:
            analyst_id = story['_metadata']['analyst_id']
            story_number = int(story['_metadata']['story_number'])
            story_id = story['userStory']['id']
            marked = self.get_marked_requirements(story)
            for req in marked:
                registros.append({
                    'story_number': story_number,
                    'story_id': story_id,
                    'analyst_id': analyst_id,
                    'req_id': req.get('id_externo'),
                    'specific_question': req.get('specific_question'),
                    'general_question': req.get('general_question')
                })

        df = pd.DataFrame(registros)
        df = df.sort_values(by=["story_number", "analyst_id"])
        df.to_csv(output_path, index=False)
        print(f"Detalhamento por analista e história salvo em: {output_path}")

        # Gráfico de frequência por questão geral

        plt.figure(figsize=(12, 6))
        geral_freq = df['general_question'].value_counts().sort_values(ascending=False)
        geral_freq.plot(kind='bar')
        plt.title('Frequência de Requisitos Marcados por Questão Geral')
        plt.ylabel('Quantidade de marcações')
        plt.xlabel('Questão Geral')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(output_path.replace(".csv", "_grafico.png"))
        print(f"Gráfico salvo em: {output_path.replace('.csv', '_grafico.png')}")

    def export_convergencia_geral(self, output_path: str = "./output/convergencia_questao_geral.csv") -> None:
        
        #Gera análise de convergência por questão geral considerando múltiplas marcações para mesma questão geral
    
        convergencia = defaultdict(lambda: defaultdict(set))  # {story_number: {general_question: set(analyst_id)}}

        for (analyst_id, story_number), stories in self.user_analysis.items():
            for story in stories:
                for question in story.get("questions", []):
                    general_desc = question["question"]["descricao"]
                    for specific in question.get("questoesEspecificas", []):
                        for req in specific.get("requirements", []):
                            if req.get("marked", False):
                                convergencia[int(story_number)][general_desc].add(analyst_id)

        registros = []
        for story_number, questoes in convergencia.items():
            for general_question, analistas in questoes.items():
                registros.append({
                    "story_number": story_number,
                    "general_question": general_question,
                    "analyst_count": len(analistas),
                    "analysts": ", ".join(sorted(analistas))
                })

        df = pd.DataFrame(registros)
        df = df.sort_values(by=["story_number", "general_question"])
        df.to_csv(output_path, index=False)
        print(f"Convergência por questão geral salva em: {output_path}")

    def export_questoes_mais_marcadas(self, output_path: str = "./output/questoes_mais_marcadas.csv") -> None:
        question_counter = Counter()
        for story in self.stories:
            for question in story.get('questions', []):
                general = question['question']['descricao']
                for specific in question.get('questoesEspecificas', []):
                    for req in specific.get('requirements', []):
                        if req.get('marked'):
                            question_counter[general] += 1

        df = pd.DataFrame(question_counter.items(), columns=["general_question", "total_marcacoes"])
        df = df.sort_values(by="total_marcacoes", ascending=False)
        df.to_csv(output_path, index=False)
        print(f"Questões gerais mais marcadas salvas em: {output_path}")

    def export_coocorrencia_requisitos(self, output_path: str = "./output/coocorrencia_requisitos.csv") -> None:
        from itertools import combinations
        coocorrencias = Counter()

        for story in self.stories:
            reqs = [req['id_externo'] for req in self.get_marked_requirements(story)]
            for a, b in combinations(sorted(set(reqs)), 2):
                coocorrencias[(a, b)] += 1

        df = pd.DataFrame([{"req_1": a, "req_2": b, "coocorrencias": count} 
                           for (a, b), count in coocorrencias.items()])
        df = df.sort_values(by="coocorrencias", ascending=False)
        df.to_csv(output_path, index=False)
        print(f"Coocorrência de requisitos salva em: {output_path}")

    def export_analise_por_secao(self, output_path: str = "./output/analise_por_secao.csv") -> None:
        secao_counter = Counter()

        for story in self.stories:
            for req in self.get_marked_requirements(story):
                secao_id = self.requirements_by_id.get(req['id'], {}).get('secao_id', 'Desconhecida')
                secao_counter[secao_id] += 1

        df = pd.DataFrame(secao_counter.items(), columns=["secao_id", "total_marcacoes"])
        df = df.sort_values(by="total_marcacoes", ascending=False)
        df.to_csv(output_path, index=False)
        print(f"Análise por seção do ASVS salva em: {output_path}")

    def generate_report(self, output_dir: str = "./output") -> None:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        if not self.stories:
            self.load_stories()

        print(f"Analisando {len(self.stories)} histórias de usuário...")
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

        req_freq = self.get_requirement_frequency()
        req_freq_df = pd.DataFrame([
            {'requisito_id': req_id, 'frequencia': freq} for req_id, freq in req_freq.items()
        ]).sort_values('frequencia', ascending=False)
        req_freq_df.to_csv(os.path.join(output_dir, "frequencia_requisitos.csv"), index=False)

        matrix_df = self.get_story_requirement_matrix()
        matrix_df.to_csv(os.path.join(output_dir, "matriz_historias_requisitos.csv"), index=False)

        agreement_df = self.get_analyst_agreement()
        agreement_df.to_csv(os.path.join(output_dir, "concordancia_analistas.csv"), index=False)

        self.export_detalhes_por_historia(os.path.join(output_dir, "detalhes_por_historia.csv"))
        self.export_detalhes_por_analista_historia(os.path.join(output_dir, "por_analista_historia.csv"))
        self.export_convergencia_geral(os.path.join(output_dir, "convergencia_questao_geral.csv"))
        self.export_questoes_mais_marcadas(os.path.join(output_dir, "questoes_mais_marcadas.csv"))
        self.export_coocorrencia_requisitos(os.path.join(output_dir, "coocorrencia_requisitos.csv"))
        self.export_analise_por_secao(os.path.join(output_dir, "analise_por_secao.csv"))
        print(f"Relatório gerado com sucesso no diretório: {output_dir}")

    def get_story_requirement_matrix(self) -> pd.DataFrame:
        all_req_ids = sorted(set(req['id_externo'] for req in self.requirements_by_id.values()))
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
            marked_reqs = self.get_marked_requirements(story)
            marked_req_ids = [req.get('id_externo') for req in marked_reqs]
            for req_id in all_req_ids:
                row[f'req_{req_id}'] = 1 if req_id in marked_req_ids else 0
            data.append(row)
        return pd.DataFrame(data)

    def get_analyst_agreement(self) -> pd.DataFrame:
        agreement_data = []
        stories_by_number = defaultdict(list)
        for story in self.stories:
            story_number = story['_metadata']['story_number']
            stories_by_number[story_number].append(story)

        for story_number, story_variants in stories_by_number.items():
            if len(story_variants) <= 1:
                continue
            analyst_requirements = {}
            for story in story_variants:
                analyst_id = story['_metadata']['analyst_id']
                marked_reqs = set(req.get('id_externo') for req in self.get_marked_requirements(story))
                analyst_requirements[analyst_id] = marked_reqs
            if len(analyst_requirements) >= 2:
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
                total_requirements = len(all_marked)
                common_requirements = len(common_marked)
                agreement_ratio = common_requirements / total_requirements if total_requirements > 0 else 1.0
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

    def export_detalhes_por_historia(self, output_path: str = "./output/detalhes_por_historia.csv") -> None:
        detalhes = []
        agrupamento = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

        for (analyst_id, story_number), stories in self.user_analysis.items():
            story = stories[0]
            for q in story.get("questions", []):
                general_question_desc = q["question"]["descricao"]
                for sq in q.get("questoesEspecificas", []):
                    for req in sq.get("requirements", []):
                        if req.get("marked", False):
                            agrupamento[int(story_number)][general_question_desc][analyst_id].add(req["id_externo"])

        for story_number, questoes in agrupamento.items():
            for general_desc, analistas_reqs in questoes.items():
                todos = list(analistas_reqs.values())
                uniao = set.union(*todos) if todos else set()
                intersec = set.intersection(*todos) if len(todos) > 1 else set()
                detalhes.append({
                    "story_number": story_number,
                    "general_question": general_desc,
                    "analysts": "; ".join(f"{k}: {sorted(v)}" for k, v in analistas_reqs.items()),
                    "intersection": ", ".join(sorted(intersec)),
                    "union": ", ".join(sorted(uniao)),
                    "total_union": len(uniao),
                    "total_intersection": len(intersec)
                })

        df = pd.DataFrame(detalhes)
        df = df.sort_values(by="story_number")
        df.to_csv(output_path, index=False)
        print(f"Arquivo CSV gerado: {output_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Analisador de Histórias de Usuário e Requisitos ASVS')
    parser.add_argument('--input', '-i', type=str, default='user_stories',
                        help='Diretório com os arquivos JSON ou pastas dos analistas (padrão: user_stories)')
    parser.add_argument('--output', '-o', type=str, default='output',
                        help='Diretório onde os resultados serão salvos (padrão: output)')
    args = parser.parse_args()
    data_dir = args.input
    output_dir = args.output

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Diretório {data_dir} criado. Coloque os arquivos JSON nesse diretório.")
        return

    analyzer = UserStoryAnalyzer(data_dir)
    analyzer.load_stories()
    analyzer.generate_report(output_dir=output_dir)
    print(f"Análise concluída. Resultados em '{output_dir}'.")

if __name__ == "__main__":
    main()
