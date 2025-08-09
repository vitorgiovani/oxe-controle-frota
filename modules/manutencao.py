# modules/manutencao.py
import streamlit as st
import pandas as pd
import sqlite3

DB_PATH = "frota.db"

@st.cache_resource
def get_conn(path=DB_PATH):
    return sqlite3.connect(path, check_same_thread=False)

conn = get_conn()

def show(com_expansor=False):
    st.subheader("🔧 Registro de Manutenção")

    with st.form("form_manutencao"):
        col1, col2 = st.columns(2)
        with col1:
            num_frota = st.text_input("Número da Frota")
            placa = st.text_input("Placa")
            data = st.date_input("Data")
            mes = st.text_input("Mês")
            sc = st.text_input("SC")
            tipo = st.text_input("Tipo")
        with col2:
            cod_peca = st.text_input("Código da Peça")
            desc_peca = st.text_input("Descrição da Peça")
            qtd = st.number_input("Quantidade", min_value=0)
            vlr_unitario = st.number_input("Valor Unitário", min_value=0.0, format="%.2f")
            fornecedor = st.text_input("Fornecedor")
            nf = st.text_input("Nota Fiscal")

        vlr_total = qtd * vlr_unitario

        submitted = st.form_submit_button("Salvar")

    if submitted:
        conn.execute("""
        INSERT INTO manutencao (
            id_frota, placa, data, mes, sc, tipo,
            cod_peca, desc_peca, qtd, vlr_unitario,
            fornecedor, nf, vlr_peca
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            None, placa, data.strftime('%Y-%m-%d'), mes, sc, tipo,
            cod_peca, desc_peca, qtd, vlr_unitario,
            fornecedor, nf, vlr_total
        ))
        conn.commit()
        st.success("Manutenção registrada com sucesso!")

    st.markdown("---")
    if com_expansor:
        with st.expander("📜 Visualizar Histórico de Manutenções"):
            df = pd.read_sql("SELECT * FROM manutencao", conn)
            st.dataframe(df)
    else:
        st.markdown("### 📜 Histórico de Manutenções")
        df = pd.read_sql("SELECT * FROM manutencao", conn)
        st.dataframe(df)