import pandas as pd
import feedparser
import urllib.parse
from datetime import datetime
import os
from google import genai
from pydantic import BaseModel
from typing import List

# 1. MATRIZ COM OS 15 CRITÉRIOS DE MONITORAMENTO (FOCO EM SEMENTES)
regras = [
    {"id": 1, "fonte": "MAPA", "cat": "Regulatório", "prio": 5, "resp": "Comercial", "query": '("MAPA" OR "Ministério da Agricultura") AND (sorgo OR RNC OR sementes)'},
    {"id": 2, "fonte": "MAPA RNC", "cat": "Regulatório", "prio": 5, "resp": "Comercial", "query": '("RNC" OR "CultivarWeb") AND (sorgo OR híbrido)'},
    {"id": 3, "fonte": "ABRASEM", "cat": "Mercado Sementes", "prio": 4, "resp": "Comercial", "query": '("ABRASEM") AND (sorgo OR sementes OR legislação)'},
    {"id": 4, "fonte": "ZARC", "cat": "Clima/Regulatório", "prio": 4, "resp": "Comercial", "query": '("ZARC" OR "Zoneamento Agrícola") AND (sorgo OR "risco climático")'},
    {"id": 5, "fonte": "EMBRAPA", "cat": "Pesquisa/Tecnologia", "prio": 5, "resp": "P&D/Comercial", "query": '("Embrapa") AND (sorgo OR seca OR pragas OR doenças OR genética)'},
    {"id": 6, "fonte": "CONAB", "cat": "Mercado Agrícola", "prio": 5, "resp": "Comercial", "query": '("CONAB") AND (sorgo OR "safra de sorgo")'},
    {"id": 7, "fonte": "USDA", "cat": "Mercado Global", "prio": 5, "resp": "Comercial", "query": '("USDA" OR "WASDE") AND (Sorghum OR sorgo)'},
    {"id": 8, "fonte": "Celeres", "cat": "Inteligência Mercado", "prio": 3, "resp": "Comercial", "query": '("Celeres") AND (sorgo OR sementes OR grãos)'},
    {"id": 9, "fonte": "Kynetec", "cat": "Market Share", "prio": 5, "resp": "Comercial", "query": '("Kynetec" OR "Spark") AND (sorgo OR "market share" OR híbridos)'},
    {"id": 10, "fonte": "Agroconsult", "cat": "Mercado Agrícola", "prio": 3, "resp": "Comercial", "query": '("Agroconsult") AND (sorgo OR safrinha OR produção)'},
    {"id": 11, "fonte": "Notícias Agrícolas", "cat": "Notícias", "prio": 4, "resp": "Comercial", "query": 'site:noticiasagricolas.com.br AND (sorgo OR "segunda safra")'},
    {"id": 12, "fonte": "Canal Rural", "cat": "Notícias", "prio": 3, "resp": "Comercial", "query": 'site:canalrural.com.br AND (sorgo OR pecuária)'},
    {"id": 13, "fonte": "Agrolink", "cat": "Notícias Técnicas", "prio": 3, "resp": "P&D/Comercial", "query": 'site:agrolink.com.br AND (sorgo OR pragas OR doenças)'},
    {"id": 14, "fonte": "Globo Rural", "cat": "Mercado Geral", "prio": 2, "resp": "Comercial", "query": 'site:globorural.globo.com AND (sorgo)'},
    {"id": 15, "fonte": "Empresas de Sementes", "cat": "Empresas de Sementes", "prio": 5, "resp": "Comercial / P&D", "query": '("Advanta" OR "Classe A" OR "Shull" OR "Nortox" OR "Supra Sementes" OR "Latina Seeds" OR "Cereal Ouro" OR "Biomatrix" OR "Nuseed" OR "Priorizi" OR "Agromen" OR "Forseed" OR "Morgan" OR "Helix" OR "Corteva" OR "Bayer" OR "KWS" OR "Brevant" OR "Syngenta" OR "Agroceres") AND (sorgo OR híbrido OR sementes)'}
]

print(f"[{datetime.now()}] Iniciando varredura RSS (últimos 60 dias)...")

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

# 2. CURADORIA COM GEMINI (FILTRO E CLASSIFICAÇÃO COMERCIAL)
if not df.empty:
    df = df.drop_duplicates(subset=["Título da Matéria"])
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key and len(df) > 0:
        print("Aplicando curadoria qualitativa com Gemini...")
        try:
            cliente_ia = genai.Client(api_key=api_key)
            
            class AvaliacaoNoticia(BaseModel):
                titulo: str
                relevante: bool
                tipo_movimento: str

            class ResultadoCuradoria(BaseModel):
                avaliacoes: List[AvaliacaoNoticia]
                
            titulos = df["Título da Matéria"].tolist()
            prompt = f"""Você é analista de agronegócio focado em SEMENTES DE SORGO.
            Avalie se o título é relevante (true/false) para o mercado de sorgo/sementes. Descarte notícias 100% focadas em cana, café, gado ou algodão sem relação com sorgo.
            Classifique em 'tipo_movimento': "Lançamento / Novo Híbrido", "Dia de Campo / Evento", "Movimentação Comercial", "Regulatório / MAPA", "Manejo / Fitossanidade" ou "Mercado / Safra".
            Títulos: {titulos}"""
            
            resposta = cliente_ia.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"response_mime_type": "application/json", "response_schema": ResultadoCuradoria, "temperature": 0.1}
            )
            
            relevantes = {item.titulo: (item.relevante, item.tipo_movimento) for item in resposta.parsed.avaliacoes}
            
            df["Relevante"] = df["Título da Matéria"].map(lambda x: relevantes.get(x, (True, "Geral"))[0])
            df["tipo_movimento"] = df["Título da Matéria"].map(lambda x: relevantes.get(x, (True, "Geral"))[1])
            
            df = df[df["Relevante"] == True].drop(columns=["Relevante"])
            print("Curadoria finalizada!")
        except Exception as e:
            print(f"Aviso: Falha na curadoria IA ({e}). Mantendo base sem filtros.")
            if "tipo_movimento" not in df.columns:
                df["tipo_movimento"] = "Movimentação Comercial"

    df = df.sort_values(by=["Prioridade", "Data Publicação"], ascending=[False, False])

df.to_csv("noticias_sorgo.csv", index=False, encoding="utf-8-sig")
print(f"Base salva! Total de matérias: {len(df)}")