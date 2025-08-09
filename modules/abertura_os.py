# modules/abertura_os.py
import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

DB_PATH = "frota.db"

@st.cache_resource
def get_conn(path=DB_PATH):
    return sqlite3.connect(path, check_same_thread=False)

conn = get_conn()

def show(com_expansor=False):
    st.subheader("📄 Abertura de Ordem de Serviço")

    with st.form("form_os"):
        col1, col2 = st.columns(2)
        with col1:
            data_abertura = st.date_input("Data de Abertura", value=date.today())
            num_os = st.text_input("Número da OS")
            num_frota = st.text_input("Número da Frota")
            placa = st.text_input("Placa")
            modelo = st.text_input("Modelo")
        with col2:
            marca = st.text_input("Marca")
            ano = st.number_input("Ano de Fabricação", min_value=1990, max_value=2050, step=1)
            chassi = st.text_input("Chassi")
            descritivo_servico = st.text_area("Descritivo do Serviço")
            sc = st.text_input("SC")
            orcamento = st.number_input("Orçamento (R$)", min_value=0.0, format="%.2f")

        col3, col4 = st.columns(2)
        with col3:
            previsao_saida = st.date_input("Previsão de Saída")
        with col4:
            data_liberacao = st.date_input("Data de Liberação")

        responsavel = st.text_input("Responsável")

        submitted = st.form_submit_button("Salvar")

    if submitted:
        conn.execute("""
        INSERT INTO ordens_servico (
            data_abertura, num_os, id_frota, placa,
            descritivo_servico, sc, orcamento,
            previsao_saida, data_liberacao, responsavel
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data_abertura.strftime('%Y-%m-%d'), num_os, None, placa,
            descritivo_servico, sc, orcamento,
            previsao_saida.strftime('%Y-%m-%d'), data_liberacao.strftime('%Y-%m-%d'), responsavel
        ))
        conn.commit()
        st.success("Ordem de Serviço registrada com sucesso!")

    st.markdown("---")
    if com_expansor:
        with st.expander("📋 Visualizar Ordens de Serviço"):
            df = pd.read_sql("SELECT * FROM ordens_servico", conn)
            st.dataframe(df)
    else:
        pass
