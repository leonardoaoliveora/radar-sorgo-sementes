import pandas as pd
import feedparser
import urllib.parse
from datetime import datetime
import os
from google import genai
from pydantic import BaseModel
from typing import List

# ==========================================
# 1. MATRIZ DE BUSCA BILINGUE (PT-BR e EN-US) - ÚLTIMOS 60 DIAS
# ==========================================
regras = [
    {"id": 1, "fonte": "MAPA / Governo", "cat": "Regulatório", "prio": 5, "resp": "Comercial", "query": '("MAPA" OR "Ministério da Agricultura") AND (sorgo OR "sementes de sorgo" OR "cultivares de sorgo")'},
    {"id": 2, "fonte": "MAPA RNC", "cat": "Regulatório", "prio": 5, "resp": "Comercial", "query": '("RNC" OR "CultivarWeb" OR "Registro Nacional") AND (sorgo)'},
    {"id": 3, "fonte": "ABRASEM / Sementes", "cat": "Mercado Sementes", "prio": 4, "resp": "Comercial", "query": '("ABRASEM" OR "Associação Brasileira de Sementes" OR "Seed Federation") AND (sorgo OR sorghum OR sementes OR seeds)'},
    {"id": 4, "fonte": "ZARC / Clima", "cat": "Clima/Regulatório", "prio": 4, "resp": "Comercial", "query": '("ZARC" OR "Zoneamento Agrícola" OR "drought tolerance") AND (sorgo OR sorghum)'},
    {"id": 5, "fonte": "Pesquisa & Embrapa", "cat": "Pesquisa/Tecnologia", "prio": 5, "resp": "P&D/Comercial", "query": '("Embrapa" OR "ICRISAT" OR "Texas A&M" OR "Kansas State" OR "Sorghum Checkoff") AND (sorgo OR sorghum OR "pulgão-da-cana" OR "sugarcane aphid" OR Melanaphis OR genética)'},
    {"id": 6, "fonte": "CONAB", "cat": "Mercado Agrícola", "prio": 5, "resp": "Comercial", "query": '("CONAB" OR "Companhia Nacional de Abastecimento") AND (sorgo)'},
    {"id": 7, "fonte": "USDA / Global", "cat": "Mercado Global", "prio": 5, "resp": "Comercial", "query": '("USDA" OR "WASDE" OR "National Sorghum Producers" OR "Sorghum Checkoff") AND (Sorghum OR sorgo)'},
    {"id": 8, "fonte": "Celeres / Consultorias", "cat": "Inteligência Mercado", "prio": 3, "resp": "Comercial", "query": '("Celeres" OR "Safras & Mercado") AND (sorgo OR sementes OR safrinha)'},
    {"id": 9, "fonte": "Market Share / Spark", "cat": "Market Share", "prio": 5, "resp": "Comercial", "query": '("Kynetec" OR "Spark" OR "market share") AND (sorgo OR sorghum OR sementes OR seeds OR híbridos OR hybrids)'},
    {"id": 10, "fonte": "Agroconsult / Rally", "cat": "Mercado Agrícola", "prio": 3, "resp": "Comercial", "query": '("Agroconsult" OR "Rally da Safra") AND (sorgo OR safrinha)'},
    {"id": 11, "fonte": "Notícias Agrícolas", "cat": "Notícias", "prio": 4, "resp": "Comercial", "query": 'site:noticiasagricolas.com.br AND (sorgo)'},
    {"id": 12, "fonte": "Canal Rural", "cat": "Notícias", "prio": 3, "resp": "Comercial", "query": 'site:canalrural.com.br AND (sorgo)'},
    {"id": 13, "fonte": "Agrolink", "cat": "Notícias Técnicas", "prio": 3, "resp": "P&D/Comercial", "query": 'site:agrolink.com.br AND (sorgo)'},
    {"id": 14, "fonte": "Globo Rural", "cat": "Mercado Geral", "prio": 2, "resp": "Comercial", "query": 'site:globorural.globo.com AND (sorgo)'},
    # Empresas globais e regionais com termos em inglês e português:
    {"id": 15, "fonte": "Empresas de Sementes", "cat": "Empresas de Sementes", "prio": 5, "resp": "Comercial / P&D", "query": '("Advanta" OR "Classe A" OR "Shull" OR "Nortox" OR "Supra Sementes" OR "Latina Seeds" OR "Cereal Ouro" OR "Biomatrix" OR "Nuseed" OR "Priorizi" OR "Agromen" OR "Forseed" OR "Morgan" OR "Helix" OR "Corteva" OR "Bayer" OR "KWS" OR "Brevant" OR "Syngenta" OR "Agroceres" OR "Sorghum Partners" OR "Alta Seeds" OR "S&W Seed" OR "DEKALB" OR "Pioneer") AND (sorgo OR sorghum OR sementes OR seeds OR híbrido OR hybrid)'}
]

# Configuração para buscar nos servidores de notícias do Brasil e dos EUA
regioes_busca = [
    {"hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"},
    {"hl": "en-US", "gl": "US", "ceid": "US:en"}
]

print(f"[{datetime.now()}] Iniciando varredura RSS Bilingue (últimos 60 dias)...")

noticias = []
for r in regras:
    for reg in regioes_busca:
        try:
            # Garante a janela estrita dos últimos 60 dias (when:60d)
            query_tempo = f"{r['query']} when:60d"
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query_tempo)}&hl={reg['hl']}&gl={reg['gl']}&ceid={reg['ceid']}"
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
        except Exception as e_feed:
            print(f"Aviso: Falha ao ler feed ({reg['gl']}) da fonte {r['fonte']}: {e_feed}")

df = pd.DataFrame(noticias)

# ==========================================
# 2. FILTRO MECÂNICO DE LISTA NEGRA (PT e EN)
# ==========================================
if not df.empty and "Título da Matéria" in df.columns:
    df = df.drop_duplicates(subset=["Título da Matéria"]).copy()
    
    dominios_proibidos = ["games.gg", "techtudo", "ign.com", "gamevicio", "ovicio", "tecmundo", "promobit", "polygon.com", "kotaku.com", "gamerant.com"]
    termos_proibidos = ["disney", "dreamlight", "nintendo", "playstation", "xbox", "steam", "auctioneer", "grow a garden", "trilha sonora", "filme", "novela", "movie", "soundtrack", "gameplay"]
    
    def passou_no_filtro_mecanico(row):
        titulo_min = str(row["Título da Matéria"]).lower()
        link_min = str(row["Link Web"]).lower()
        
        for dom in dominios_proibidos:
            if dom in link_min or dom in titulo_min:
                return False
        for termo in termos_proibidos:
            if termo in titulo_min:
                return False
                
        # Culturas exclusivas em português e inglês
        culturas_exclusivas = ["trigo", "wheat", "arroz", "rice", "café", "coffee", "cacau", "maçã", "citros", "algodão", "cotton", "feijão", "cana-de-açúcar", "sugarcane", "suínos", "aves", "milho", "corn", "soybean", "soja"]
        tem_outra_cultura = any(c in titulo_min for c in culturas_exclusivas)
        tem_sorgo = "sorgo" in titulo_min or "sorghum" in titulo_min or "milo" in titulo_min
        
        # Se fala apenas de outras culturas e NÃO cita sorgo, descarta na hora
        if tem_outra_cultura and not tem_sorgo:
            return False
        return True

    df = df[df.apply(passou_no_filtro_mecanico, axis=1)].copy()
    print(f"Pós-filtro mecânico bilingue: {len(df)} matérias restantes.")

# ==========================================
# 3. CURADORIA COM GEMINI (MANTER IDIOMA ORIGINAL + TAG EM PT)
# ==========================================
if not df.empty and "Título da Matéria" in df.columns:
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if api_key and len(df) > 0:
        print("Aplicando curadoria com Gemini 2.5 Flash...")
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
            EXCLUA sem piedade qualquer notícia que não tenha impacto real para o setor de SORGO e SEMENTES DE GRÃOS no Brasil ou no mundo.
            DESCARTE: videogames, entretenimento, e notícias focadas em trigo/milho/soja onde sorgo não é o tema principal.
            APROVE APENAS: sorgo granífero, biomassa, forrageiro, pulgão-da-cana (sugarcane aphid), ZARC, safrinha, relatórios USDA/WASDE, ou movimentações de empresas de sementes globais e nacionais (Advanta, Shull, Biomatrix, Nortox, Supra Sementes, Latina Seeds, Corteva, Bayer, KWS, Alta Seeds, S&W Seed, etc.).
            
            REGRA DE IDIOMA: MANTENHA O TÍTULO EXATAMENTE COMO ESTÁ NO IDIOMA ORIGINAL (seja em português, inglês ou espanhol). NÃO TRADUZA OS TÍTULOS.
            
            Classifique em 'tipo_movimento' (use sempre estas etiquetas em português para padronizar os filtros do painel): "Lançamento / Novo Híbrido", "Dia de Campo / Evento", "Movimentação Comercial", "Regulatório / MAPA", "Manejo / Fitossanidade" ou "Mercado / Safra".
            
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
            print("Curadoria IA finalizada com sucesso!")
            
        except Exception as e:
            print(f"Aviso: Falha na API da IA ({e}). Ativando fallback de segurança por palavras-chave.")
            df = df[df["Título da Matéria"].str.contains("sorgo|sorghum|sementes|seeds|safrinha|pulgão|aphid|zarc|wasde", case=False, na=False)].copy()
            if "tipo_movimento" not in df.columns:
                df["tipo_movimento"] = "Movimentação Comercial"

    df = df.sort_values(by=["Prioridade", "Data Publicação"], ascending=[False, False])

# ==========================================
# 4. SALVAMENTO DA BASE
# ==========================================
if not df.empty:
    df.to_csv("noticias_sorgo.csv", index=False, encoding="utf-8-sig")
    print(f"[{datetime.now()}] Base bilingue salva com sucesso! Matérias finais: {len(df)}")
else:
    print("Nenhuma matéria relevante encontrada ou a internet oscilou. O arquivo CSV anterior foi mantido intacto por segurança.")
