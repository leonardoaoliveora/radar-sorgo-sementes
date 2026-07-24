import pandas as pd
import feedparser
import urllib.parse
from datetime import datetime
import os
from google import genai
from pydantic import BaseModel
from typing import List

# ==========================================
# 1. MATRIZ BLINDADA (PALAVRA SORGO É OBRIGATÓRIA EM TODAS)
# ==========================================
regras = [
    {"id": 1, "fonte": "MAPA", "cat": "Regulatório", "prio": 5, "resp": "Comercial", "query": '("MAPA" OR "Ministério da Agricultura") AND (sorgo OR "sementes de sorgo" OR "cultivares de sorgo")'},
    {"id": 2, "fonte": "MAPA RNC", "cat": "Regulatório", "prio": 5, "resp": "Comercial", "query": '("RNC" OR "CultivarWeb" OR "Registro Nacional") AND (sorgo)'},
    {"id": 3, "fonte": "ABRASEM", "cat": "Mercado Sementes", "prio": 4, "resp": "Comercial", "query": '("ABRASEM" OR "Associação Brasileira de Sementes") AND (sorgo OR sementes)'},
    {"id": 4, "fonte": "ZARC", "cat": "Clima/Regulatório", "prio": 4, "resp": "Comercial", "query": '("ZARC" OR "Zoneamento Agrícola") AND (sorgo)'},
    {"id": 5, "fonte": "EMBRAPA", "cat": "Pesquisa/Tecnologia", "prio": 5, "resp": "P&D/Comercial", "query": '("Embrapa") AND (sorgo OR "pulgão-da-cana" OR "Melanaphis")'},
    {"id": 6, "fonte": "CONAB", "cat": "Mercado Agrícola", "prio": 5, "resp": "Comercial", "query": '("CONAB" OR "Companhia Nacional de Abastecimento") AND (sorgo)'},
    {"id": 7, "fonte": "USDA", "cat": "Mercado Global", "prio": 5, "resp": "Comercial", "query": '("USDA" OR "WASDE") AND (Sorghum OR sorgo)'},
    {"id": 8, "fonte": "Celeres", "cat": "Inteligência Mercado", "prio": 3, "resp": "Comercial", "query": '("Celeres") AND (sorgo OR sementes OR safrinha)'},
    {"id": 9, "fonte": "Kynetec", "cat": "Market Share", "prio": 5, "resp": "Comercial", "query": '("Kynetec" OR "Spark") AND (sorgo OR "market share" OR sementes)'},
    {"id": 10, "fonte": "Agroconsult", "cat": "Mercado Agrícola", "prio": 3, "resp": "Comercial", "query": '("Agroconsult" OR "Rally da Safra") AND (sorgo OR safrinha)'},
    {"id": 11, "fonte": "Notícias Agrícolas", "cat": "Notícias", "prio": 4, "resp": "Comercial", "query": 'site:noticiasagricolas.com.br AND (sorgo)'},
    {"id": 12, "fonte": "Canal Rural", "cat": "Notícias", "prio": 3, "resp": "Comercial", "query": 'site:canalrural.com.br AND (sorgo)'},
    {"id": 13, "fonte": "Agrolink", "cat": "Notícias Técnicas", "prio": 3, "resp": "P&D/Comercial", "query": 'site:agrolink.com.br AND (sorgo)'},
    {"id": 14, "fonte": "Globo Rural", "cat": "Mercado Geral", "prio": 2, "resp": "Comercial", "query": 'site:globorural.globo.com AND (sorgo)'},
    # Na regra de marcas, exigimos que a palavra "sorgo" ou "sorghum" esteja obrigatoriamente vinculada à matéria:
    {"id": 15, "fonte": "Empresas de Sementes", "cat": "Empresas de Sementes", "prio": 5, "resp": "Comercial / P&D", "query": '("Advanta" OR "Classe A" OR "Shull" OR "Nortox" OR "Supra Sementes" OR "Latina Seeds" OR "Cereal Ouro" OR "Biomatrix" OR "Nuseed" OR "Priorizi" OR "Agromen" OR "Forseed" OR "Morgan" OR "Helix" OR "Corteva" OR "Bayer" OR "KWS" OR "Brevant" OR "Syngenta" OR "Agroceres") AND (sorgo OR sorghum)'}
]

print(f"[{datetime.now()}] Iniciando varredura RSS blindada (últimos 60 dias)...")

noticias = []
for r in regras:
    query_tempo = f"{r['query']} when:60d"
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query_tempo)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    
    feed = feedparser.parse(url)
    for item in feed.entries:
        try:
            data_pub = pd.to_datetime(item.published).strftime('%d/%m/%Y %H:%M')
        except:
            data_pub = datetime.now().strftime('%d/%m/%Y %H:%M')
            
        noticias.append({
            "Prioridade": r['prio'],
            "Fonte / Alvo": r['fonte'],
            "Categoria": r['cat'],
            "Título da Matéria": item.title,
            "Link Web": item.link,
            "Data Publicação": data_pub,
            "Responsável": r['resp']
        })

df = pd.DataFrame(noticias)

# ==========================================
# 2. CAMADA DE DEFESA MECÂNICA (LISTA NEGRA PYTHON)
# ==========================================
if not df.empty:
    df = df.drop_duplicates(subset=["Título da Matéria"]).copy()
    
    # Palavras e domínios proibidos que jogam a matéria no lixo na hora
    dominios_proibidos = ["games.gg", "techtudo", "ign.com", "gamevicio", "ovicio", "tecmundo", "promobit"]
    termos_proibidos = ["disney", "dreamlight", "nintendo", "playstation", "xbox", "steam", "auctioneer", "grow a garden", "trilha sonora", "filme", "novela"]
    
    def passou_no_filtro_mecânico(row):
        titulo_min = str(row["Título da Matéria"]).lower()
        link_min = str(row["Link Web"]).lower()
        
        # 1. Block de Domínios e Palavras de Games
        for dom in dominios_proibidos:
            if dom in link_min or dom in titulo_min:
                return False
        for termo in termos_proibidos:
            if termo in titulo_min:
                return False
                
        # 2. Block de outras culturas se não citar sorgo ou sementes/safra em geral
        culturas_exclusivas = ["trigo", "arroz", "café", "cacau", "maçã", "citros", "algodão", "feijão", "cana-de-açúcar", "suínos", "aves", "pecuária de leite"]
        tem_outra_cultura = any(c in titulo_min for c in culturas_exclusivas)
        tem_sorgo = "sorgo" in titulo_min or "sorghum" in titulo_min
        
        # Se fala de trigo/café e NÃO fala de sorgo, descarta!
        if tem_outra_cultura and not tem_sorgo:
            return False
            
        return True

    df = df[df.apply(passou_no_filtro_mecânico, axis=1)].copy()
    print(f"Pós-filtro mecânico: {len(df)} matérias restantes.")

# ==========================================
# 3. CAMADA DE CURADORIA COM GEMINI (COM FALLBACK SEGURO)
# ==========================================
if not df.empty:
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if api_key and len(df) > 0:
        print("Aplicando curadoria rigorosa com Gemini 2.5 Flash...")
        try:
            cliente_ia = genai.Client(api_key=api_key)
            
            class AvaliacaoNoticia(BaseModel):
                titulo: str
                relevante: bool
                tipo_movimento: str

            class ResultadoCuradoria(BaseModel):
                avaliacoes: List[AvaliacaoNoticia]
                
            titulos = df["Título da Matéria"].tolist()
            
            prompt_implacavel = f"""Você é o Diretor Técnico de uma empresa de MELHORAMENTO GENÉTICO DE SORGO.
            Sua missão é EXCLUIR sem piedade qualquer notícia que não tenha impacto real para o setor de SORGO e SEMENTES DE GRÃOS.
            
            DESCARTE IMEDIATO (relevante = false):
            1. QUALQUER notícia sobre jogos de videogame, filmes, entretenimento ou guias de games (mesmo que tenham a palavra 'sementes' ou 'jardim').
            2. Notícias focadas em trigo, milho, arroz, soja, cana ou café onde o SORGO NÃO É O TEMA ou não compete diretamente na safrinha.
            3. Citações irrelevantes de marcas concorrentes (Corteva, Bayer, KWS, etc.) se a matéria for sobre fungicida para café, herbicida para pastagem ou sementes de hortaliças.
            
            APROVE APENAS (relevante = true):
            - Matérias que falem de sorgo granífero, biomassa, forrageiro, pulgão-da-cana, ZARC de sorgo, safrinha no Centro-Oeste ou movimentações e dias de campo de empresas de sementes (Advanta, Shull, Biomatrix, Nortox, Supra Sementes, Latina Seeds, etc.).

            Classifique também o 'tipo_movimento': "Lançamento / Novo Híbrido", "Dia de Campo / Evento", "Movimentação Comercial", "Regulatório / MAPA", "Manejo / Fitossanidade" ou "Mercado / Safra".
            
            Títulos para avaliar: {titulos}"""
            
            resposta = cliente_ia.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_implacavel,
                config={"response_mime_type": "application/json", "response_schema": ResultadoCuradoria, "temperature": 0.1}
            )
            
            relevantes = {item.titulo: (item.relevante, item.tipo_movimento) for item in resposta.parsed.avaliacoes}
            
            df["Relevante"] = df["Título da Matéria"].map(lambda x: relevantes.get(x, (False, "Geral"))[0])
            df["tipo_movimento"] = df["Título da Matéria"].map(lambda x: relevantes.get(x, (False, "Geral"))[1])
            
            df = df[df["Relevante"] == True].drop(columns=["Relevante"])
            print(f"Curadoria com IA finalizada! Matérias aprovadas: {len(df)}")
            
        except Exception as e:
            # FALLBACK SEGURO: Se a IA falhar, não deixa passar tudo! Só aceita se tiver 'sorgo' ou 'sementes' no título
            print(f"Aviso: Falha temporária na IA ({e}). Ativando trava de segurança de títulos.")
            df = df[df["Título da Matéria"].str.contains("sorgo|sorghum|sementes|safrinha|pulgão|zarc", case=False, na=False)].copy()
            if "tipo_movimento" not in df.columns:
                df["tipo_movimento"] = "Movimentação Comercial"

    df = df.sort_values(by=["Prioridade", "Data Publicação"], ascending=[False, False])

df.to_csv("noticias_sorgo.csv", index=False, encoding="utf-8-sig")
print(f"[{datetime.now()}] Base blindada salva com sucesso! Total de matérias finais: {len(df)}")
