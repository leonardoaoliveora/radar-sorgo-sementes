import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os
from google import genai

if not os.path.exists("noticias_sorgo.csv"):
    exit(0)

df = pd.read_csv("noticias_sorgo.csv")
df["Data_Obj"] = pd.to_datetime(df["Data Publicação"], format="%d/%m/%Y %H:%M", errors="coerce")
data_limite = datetime.now() - timedelta(days=7)
df_semana = df[df["Data_Obj"] >= data_limite].copy()

if len(df_semana) == 0:
    exit(0)

api_key = os.environ.get("GEMINI_API_KEY")
resumo_ia_html = "<p><i>Resumo indisponível.</i></p>"

if api_key:
    try:
        cliente_ia = genai.Client(api_key=api_key)
        lista_itens = ""
        for idx, linha in df_semana.head(20).iterrows():
            tag = linha.get("tipo_movimento", "Geral")
            lista_itens += f"- [{tag}] {linha['Fonte / Alvo']}: {linha['Título da Matéria']} (Link: {linha['Link Web']})\n"
            
        prompt = f"""Redija um BOLETIM EXECUTIVO SEMANAL em português com base nesta lista de notícias dos últimos 7 dias no setor de sorgo.
        RESPOSTA APENAS EM HTML LIMPO. Crie 2 linhas de introdução e divida em 3 seções com <h4> verde escuro (<h4 style="color: #1b5e20;">):
        1. 🏢 Movimentações de Marcas e Lançamentos de Híbridos
        2. 🚨 Regulatório, RNC e ZARC
        3. 🌱 Mercado, Safra e Fitossanidade
        Use bullet points com 1 frase de resumo e o link <a href="..."> Original para leitura. Lista: {lista_itens}"""
        
        resposta = cliente_ia.models.generate_content(model="gemini-2.5-flash", contents=prompt, config={"temperature": 0.2})
        resumo_ia_html = resposta.text
    except Exception as e:
        print(f"Erro IA: {e}")

html_email = f"""<!DOCTYPE html><html><body style="font-family: Arial; color: #212529; line-height: 1.6; max-width: 650px; margin: 0 auto; padding: 20px;">
<div style="background-color: #1b5e20; color: #ffffff; padding: 15px 20px; border-radius: 8px 8px 0 0;"><h2 style="margin: 0;">🌱 Radar Semanal: Sorgo & Sementes</h2></div>
<div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 0 0 8px 8px;"><p>Olá, Equipe,</p><p>Confira o briefing das movimentações dos últimos 7 dias:</p>
<hr style="border: none; border-top: 1px solid #eeeeee; margin: 20px 0;">{resumo_ia_html}<hr style="border: none; border-top: 1px solid #eeeeee; margin: 20px 0;">
<p style="font-size: 12px; color: #6c757d; text-align: center;">Relatório gerado automaticamente por IA via GitHub Actions.</p></div></body></html>"""

remetente = os.environ.get("EMAIL_REMETENTE")
senha = os.environ.get("EMAIL_SENHA")
destinatarios = [e.strip() for e in os.environ.get("EMAIL_DESTINATARIOS", "").split(",") if e.strip()]

if remetente and senha and destinatarios:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🌱 Briefing Semanal de Sorgo - {datetime.now().strftime('%d/%m/%Y')}"
        msg["From"], msg["To"] = f"Radar Sementes <{remetente}>", ", ".join(destinatarios)
        msg.attach(MIMEText(html_email, "html", "utf-8"))
        
        servidor = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        servidor.login(remetente, senha)
        servidor.sendmail(remetente, destinatarios, msg.as_string())
        servidor.quit()
        print("E-mail semanal enviado!")
    except Exception as e:
        print(f"Falha ao enviar: {e}")