import pandas as pd
import feedparser
import urllib.parse
from datetime import datetime
import os
from google import genai
from pydantic import BaseModel
from typing import List

# 1. MATRIZ BILINGUE OTIMIZADA
regras = [
    {"id": 1, "fonte": "MAPA / Governo", "cat": "Regulatório", "prio": 5, "resp": "Comercial", "query": '("MAPA" OR "Ministério da Agricultura") AND (sorgo OR "sementes de sorgo")'},
    {"id": 2, "fonte": "MAPA RNC", "cat": "Regulatório", "prio": 5, "resp": "Comercial", "query": '("RNC" OR "CultivarWeb") AND (sorgo)'},
    {"id": 3, "fonte": "ABRASEM / Sementes", "cat": "Mercado Sementes", "prio": 4, "resp": "Comercial", "query": '("ABRASEM" OR "Seed Federation") AND (sorgo OR sorghum OR sementes OR seeds)'},
    {"id": 4, "fonte": "ZARC / Clima", "cat": "Clima/Regulatório", "prio": 4, "resp": "Comercial", "query": '("ZARC" OR "Zoneamento Agrícola") AND (sorgo OR sorghum)'},
    {"id": 5, "fonte": "Pesquisa & Embrapa", "cat": "Pesquisa/Tecnologia", "prio": 5, "resp": "P&D/Comercial", "query": '("Embrapa" OR "ICRISAT" OR "Texas A&M" OR "Kansas State") AND (sorgo OR sorghum OR "pulgão-da-cana" OR "sugarcane aphid")'},
    {"id": 6, "fonte": "CONAB", "cat": "Mercado Agrícola", "prio": 5, "resp": "Comercial", "query": '("CONAB") AND (sorgo)'},
    {"id": 7, "fonte": "USDA / Global", "cat": "Mercado Global", "prio": 5, "resp": "Comercial", "query": '("USDA" OR "WASDE" OR "National Sorghum Producers") AND (Sorghum OR sorgo)'},
    {"id": 8, "fonte": "Celeres / Consultorias", "cat": "Inteligência Mercado", "prio": 3, "resp": "Comercial", "query": '("Celeres" OR "Safras & Mercado") AND (sorgo OR sementes)'},
    {"id": 9, "fonte": "Market Share / Spark", "cat": "Market Share", "prio": 5, "resp": "Comercial", "query": '("Kynetec" OR "Spark") AND (sorgo OR sorghum OR sementes OR seeds)'},
    {"id": 10, "fonte": "Agroconsult / Rally", "cat": "Mercado Agrícola", "prio": 3, "resp": "Comercial", "query": '("Agroconsult") AND (sorgo OR safrinha)'},
    {"id": 11, "fonte": "Notícias Agrícolas", "cat": "Notícias", "prio": 4, "resp": "Comercial", "query": 'site:noticiasagricolas.com.br AND (sorgo)'},
    {"id": 12, "fonte": "Canal Rural", "cat": "Notícias", "prio": 3, "resp": "Comercial", "query": 'site:canalrural.com.br AND (sorgo)'},
    {"id": 13, "fonte": "Agrolink", "cat": "Notícias Técnicas", "prio": 3, "resp": "P&D/Comercial", "query": 'site:agrolink.com.br AND (sorgo)'},
    {"id": 14, "fonte": "Globo Rural", "cat": "Mercado Geral", "prio": 2, "resp": "Comercial", "query": 'site:globorural.globo.com AND (sorgo)'},
    {"id": 15, "fonte": "Empresas de Sementes", "cat": "Empresas de Sementes", "prio": 5, "resp": "Comercial / P&D", "query": '("Advanta" OR "Shull" OR "Biomatrix" OR "Nuseed" OR "Corteva" OR "Bayer" OR "KWS" OR "Syngenta" OR "Pioneer" OR "DEKALB") AND (sorgo OR sorghum OR sementes OR seeds)'}
]

regioes_busca = [
    {"hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"},
    {"hl": "en-US", "gl": "US", "ceid": "US:en"}
]

print(f"[{datetime.now()}] Iniciando varredura RSS com limite de tempo...")

noticias = []
for r in regras:
    for reg in regioes_busca:
        try:
            query_tempo = f"{r['query']} when:30d"  # Reduzido para 30 dias para puxar menos volume obsoleto
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query_tempo)}&hl={reg['hl']}&gl={reg['gl']}&ceid={reg['ceid']}"
            feed = feedparser.parse(url)
            
            # Limita a 10 notícias por feed para garantir velocidade máxima
            for item in feed.entries[:10]:
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
        except Exception:
            pass

df = pd.DataFrame(noticias)

# 2. FILTRO MECÂNICO DE LIMPEZA
if not df.empty and "Título da Matéria" in df.columns:
    df = df.drop_duplicates(subset=["Título da Matéria"]).copy()
    
    dominios_proibidos = ["games.gg", "techtudo", "ign.com", "gamevicio", "ovicio", "tecmundo", "promobit", "polygon.com", "kotaku.com"]
    termos_proibidos = ["disney", "dreamlight", "nintendo", "playstation", "xbox", "steam", "auctioneer", "grow a garden", "filme", "novela"]
    
    def passou_no_filtro_mecanico(row):
        titulo_min = str(row["Título da Matéria"]).lower()
        link_min = str(row["Link Web"]).lower()
        
        for dom in dominios_proibidos:
            if dom in link_min or dom in titulo_min:
                return False
        for termo in termos_proibidos:
            if termo in titulo_min:
                return False
                
        culturas_exclusivas = ["trigo", "wheat", "arroz", "rice", "café", "coffee", "cacau", "algodão", "cotton", "cana-de-açúcar", "sugarcane", "milho", "corn", "soybean", "soja"]
        tem_outra_cultura = any(c in titulo_min for c in culturas_exclusivas)
        tem_sorgo = "sorgo" in titulo_min or "sorghum" in titulo_min or "milo" in titulo_min
        
        if tem_outra_cultura and not tem_sorgo:
            return False
        return True

    df = df[df.apply(passou_no_filtro_mecanico, axis=1)].copy()

# 3. CURADORIA COM GEMINI (COM AMOSTRA SEGURA DE MÁXIMO 80 ITENS)
if not df.empty and "Título da Matéria" in df.columns:
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # Restringe a um lote máximo de 80 títulos para a IA processar em menos de 3 segundos
    df_para_ia = df.head(80).copy()
    
    if api_key and len(df_para_ia) > 0:
        print("Aplicando curadoria rápida com Gemini...")
        try:
            cliente_ia = genai.Client(api_key=api_key)
            
            class AvaliacaoNoticia(BaseModel):
                titulo: str
                relevante: bool
                tipo_movimento: str

            class ResultadoCuradoria(BaseModel):
                avaliacoes: List[AvaliacaoNoticia]
                
            titulos = df_para_ia["Título da Matéria"].tolist()
            
            prompt_rapido = f"""Você é agrônomo especialista em SORGO.
            Avalie rapidamente os títulos e aponte quais são relevantes (true/false) para o setor de sorgo e sementes.
            Descarte jogos, entretenimento e culturas sem relação com sorgo.
            Classifique em 'tipo_movimento': "Lançamento / Novo Híbrido", "Dia de Campo / Evento", "Movimentação Comercial", "Regulatório / MAPA", "Manejo / Fitossanidade" ou "Mercado / Safra".
            Títulos: {titulos}"""
            
            resposta = cliente_ia.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_rapido,
                config={"response_mime_type": "application/json", "response_schema": ResultadoCuradoria, "temperature": 0.1}
            )
            
            relevantes = {item.titulo: (item.relevante, item.tipo_movimento) for item in resposta.parsed.avaliacoes}
            
            df_para_ia["Relevante"] = df_para_ia["Título da Matéria"].map(lambda x: relevantes.get(x, (False, "Geral"))[0])
            df_para_ia["tipo_movimento"] = df_para_ia["Título da Matéria"].map(lambda x: relevantes.get(x, (False, "Geral"))[1])
            
            df = df_para_ia[df_para_ia["Relevante"] == True].drop(columns=["Relevante"]).copy()
            print("Curadoria IA concluída com sucesso!")
            
        except Exception as e:
            print(f"Aviso na IA ({e}). Usando filtro de segurança por palavras-chave.")
            df = df[df["Título da Matéria"].str.contains("sorgo|sorghum|sementes|seeds|safrinha|pulgão|aphid|zarc|wasde", case=False, na=False)].copy()
            if "tipo_movimento" not in df.columns:
                df["tipo_movimento"] = "Movimentação Comercial"

    df = df.sort_values(by=["Prioridade", "Data Publicação"], ascending=[False, False])

# 4. SALVAMENTO
if not df.empty:
    df.to_csv("noticias_sorgo.csv", index=False, encoding="utf-8-sig")
    print(f"[{datetime.now()}] Base salva com sucesso! Total: {len(df)} matérias.")
