import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Radar de Mercado - Sorgo", page_icon="🌱", layout="wide")

st.title("🌱 Radar de Inteligência de Mercado - Sorgo & Sementes")
st.markdown("Dossiê qualitativo de **Legislação, Marcas de Sementes, Concorrência e P&D**.")
st.divider()

if os.path.exists("noticias_sorgo.csv"):
    df_filtrado = pd.read_csv("noticias_sorgo.csv")
    
    # 1. TOPO SIMPLIFICADO: Apenas 2 cartões (sem o Alertas Críticos Prio 5)
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.metric("📰 Matérias Monitoradas (60 dias)", f"{len(df_filtrado)}")
    with col2:
        with st.container(border=True):
            data_mod = datetime.fromtimestamp(os.path.getmtime("noticias_sorgo.csv")).strftime('%d/%m/%Y %H:%M')
            st.metric("🕒 Última Varredura Automática", data_mod)
            
    st.divider()
    
    # Lista de colunas que serão ocultadas das tabelas visuais
    colunas_ocultar = ["Prioridade", "Responsável", "tipo_movimento"]
    
    aba_urgentes, aba_empresas, aba_mercado = st.tabs([
        "🚨 Regulatório & Registros (MAPA/RNC/ZARC)",
        "🏢 Radar de Empresas & Comercialização de Sementes",
        "🌱 Safra, P&D e Mercado Geral"
    ])

    with aba_urgentes:
        st.markdown("**Portarias, Legislação e Janelas de Plantio**")
        df_reg = df_filtrado[df_filtrado["Categoria"].isin(["Regulatório", "Clima/Regulatório"])]
        if not df_reg.empty:
            # 2. REMOVENDO AS COLUNAS INTERNAS DA TABELA
            df_exibir_reg = df_reg.drop(columns=colunas_ocultar, errors="ignore")
            st.dataframe(
                df_exibir_reg, 
                column_config={
                    "Link Web": st.column_config.LinkColumn("Link", display_text="🔗 Abrir"), 
                    "Título da Matéria": st.column_config.TextColumn("Descrição", width="large")
                }, 
                hide_index=True, 
                use_container_width=True
            )
        else:
            st.info("Nenhuma atualização regulatória recente no período.")

    with aba_empresas:
        st.markdown("**Acompanhamento de Lançamentos, Vitrines e Posicionamento de Marcas no Campo**")
        df_empresas = df_filtrado[df_filtrado["Categoria"] == "Empresas de Sementes"].copy()
        if not df_empresas.empty:
            if "tipo_movimento" not in df_empresas.columns:
                df_empresas["tipo_movimento"] = "Movimentação Comercial"
            df_empresas["tipo_movimento"] = df_empresas["tipo_movimento"].fillna("Movimentação Comercial")
            
            opcoes = df_empresas["tipo_movimento"].unique().tolist()
            tags_sel = st.multiselect("🎯 Filtrar por Tipo de Movimento:", options=opcoes, default=opcoes)
            
            df_exibir = df_empresas[df_empresas["tipo_movimento"].isin(tags_sel)]
            st.divider()
            
            for index, linha in df_exibir.iterrows():
                tag = f" [{linha['tipo_movimento']}]"
                with st.expander(f"📌{tag} [{linha['Data Publicação']}] {linha['Fonte / Alvo']} — {linha['Título da Matéria']}"):
                    col_t, col_b = st.columns([4, 1])
                    with col_t:
                        # Removida a informação visual de Responsável de dentro do cartão
                        st.markdown(f"**Empresa Monitorada:** `{linha['Fonte / Alvo']}`")
                        st.markdown(f"**Classificação IA:** `{linha['tipo_movimento']}`")
                    with col_b:
                        st.link_button("🔗 Abrir Matéria", linha["Link Web"], use_container_width=True)
        else:
            st.info("Nenhuma movimentação comercial de marcas capturada no período.")

    with aba_mercado:
        st.markdown("**Estudos de Safra, Preços e Tecnologias da Embrapa**")
        df_geral = df_filtrado[~df_filtrado["Categoria"].isin(["Regulatório", "Clima/Regulatório", "Empresas de Sementes"])]
        if not df_geral.empty:
            # 3. REMOVENDO AS COLUNAS INTERNAS DA TABELA
            df_exibir_geral = df_geral.drop(columns=colunas_ocultar, errors="ignore")
            st.dataframe(
                df_exibir_geral, 
                column_config={
                    "Link Web": st.column_config.LinkColumn("Link", display_text="🔗 Abrir"), 
                    "Título da Matéria": st.column_config.TextColumn("Descrição", width="large")
                }, 
                hide_index=True, 
                use_container_width=True
            )
else:
    st.warning("A base de dados ainda não foi gerada pelo robô do GitHub Actions. Aguarde a execução agendada ou rode manualmente no GitHub.")
