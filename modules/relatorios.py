# modules/relatorios.py
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

DB_PATH = "frota.db"

@st.cache_resource
def get_conn(path=DB_PATH):
    return sqlite3.connect(path, check_same_thread=False)

conn = get_conn()

def show(estilo_visual=False):
    if estilo_visual:
        st.markdown("""
            <style>
            .main, .block-container {
                background-color: #003300 !important;
                color: white !important;
            }
            h1, h2, h3, h4, h5, h6, label, .stTextInput label, .stDateInput label, .stSelectbox label {
                color: white !important;
            }
            .stPlotlyChart .xtick text, .stPlotlyChart .ytick text {
                fill: white !important;
            }
            </style>
        """, unsafe_allow_html=True)

    st.subheader("📊 Relatórios e Análises")

    tab1, tab2 = st.tabs(["Custos de Manutenção", "Ordens de Serviço"])

    with tab1:
        df_manut = pd.read_sql("SELECT * FROM manutencao", conn)

        if df_manut.empty:
            st.warning("Nenhum dado de manutenção encontrado.")
        else:
            df_manut['data'] = pd.to_datetime(df_manut['data'], errors='coerce')
            df_manut['mes'] = df_manut['data'].dt.strftime('%Y-%m')

            placas = df_manut['placa'].dropna().unique().tolist()
            placa_selecionada = st.selectbox("Filtrar por Placa", options=["Todas"] + placas)
            datas = df_manut['data'].dropna()
            data_inicio = st.date_input("Início", value=datas.min().date()) if not datas.empty else None
            data_fim = st.date_input("Fim", value=datas.max().date()) if not datas.empty else None

            if placa_selecionada != "Todas":
                df_manut = df_manut[df_manut['placa'] == placa_selecionada]

            if data_inicio and data_fim:
                df_manut = df_manut[(df_manut['data'] >= pd.to_datetime(data_inicio)) & (df_manut['data'] <= pd.to_datetime(data_fim))]

            custo_por_mes = df_manut.groupby('mes')['vlr_peca'].sum().reset_index()
            fig = px.bar(custo_por_mes, x='mes', y='vlr_peca', title="Custo Total por Mês", labels={"mes": "Mês", "vlr_peca": "Custo (R$)"})
            st.plotly_chart(fig, use_container_width=True)

            custo_por_frota = df_manut.groupby('placa')['vlr_peca'].sum().reset_index()
            fig2 = px.bar(custo_por_frota, x='placa', y='vlr_peca', title="Custo Total por Veículo", labels={"placa": "Placa", "vlr_peca": "Custo (R$)"})
            st.plotly_chart(fig2, use_container_width=True)

            fornecedor_freq = df_manut['fornecedor'].value_counts().reset_index()
            fornecedor_freq.columns = ['Fornecedor', 'Quantidade']
            fig3 = px.bar(fornecedor_freq, x='Fornecedor', y='Quantidade', title="Fornecedores Mais Utilizados")
            st.plotly_chart(fig3, use_container_width=True)

            tipo_freq = df_manut['tipo'].value_counts().reset_index()
            tipo_freq.columns = ['Tipo de Manutenção', 'Quantidade']
            fig4 = px.pie(tipo_freq, names='Tipo de Manutenção', values='Quantidade', title="Distribuição por Tipo de Manutenção")
            st.plotly_chart(fig4, use_container_width=True)

    with tab2:
        df_os = pd.read_sql("SELECT * FROM ordens_servico", conn)

        if df_os.empty:
            st.warning("Nenhuma OS encontrada.")
        else:
            df_os['data_abertura'] = pd.to_datetime(df_os['data_abertura'], errors='coerce')
            df_os['mes'] = df_os['data_abertura'].dt.strftime('%Y-%m')

            placas_os = df_os['placa'].dropna().unique().tolist()
            placa_os = st.selectbox("Filtrar OS por Placa", options=["Todas"] + placas_os)
            datas_os = df_os['data_abertura'].dropna()
            inicio_os = st.date_input("Início (OS)", value=datas_os.min().date()) if not datas_os.empty else None
            fim_os = st.date_input("Fim (OS)", value=datas_os.max().date()) if not datas_os.empty else None

            if placa_os != "Todas":
                df_os = df_os[df_os['placa'] == placa_os]

            if inicio_os and fim_os:
                df_os = df_os[(df_os['data_abertura'] >= pd.to_datetime(inicio_os)) & (df_os['data_abertura'] <= pd.to_datetime(fim_os))]

            qtde_por_mes = df_os.groupby('mes')['num_os'].count().reset_index(name='quantidade')
            fig = px.line(qtde_por_mes, x='mes', y='quantidade', markers=True, title="Quantidade de OS por Mês")
            st.plotly_chart(fig, use_container_width=True)

            df_os_filtrado = df_os[df_os['data_liberacao'].isnull()][['data_abertura', 'num_os', 'placa', 'descritivo_servico', 'orcamento', 'responsavel']]
            st.dataframe(df_os_filtrado, use_container_width=True)
