import streamlit as st
import pandas as pd
import sqlite3
from PIL import Image
import os

DB_PATH = "frota.db"
FOTOS_PATH = "fotos_frota"

@st.cache_resource
def get_conn(path=DB_PATH):
    return sqlite3.connect(path, check_same_thread=False)

conn = get_conn()

os.makedirs(FOTOS_PATH, exist_ok=True)

def show(com_expansor=False):
    st.markdown("""
        <style>
        .stApp {
            background-color: #004d00 !important; /* verde escuro */
            color: white !important;
        }
        header[data-testid="stHeader"] {
            background-color: #004d00 !important; /* topo com mesmo verde do corpo */
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #006400 !important; /* verde */
            color: white !important;
            font-weight: bold;
            font-size: 16px;
        }
        .stTextInput input,
        .stNumberInput input,
        .stSelectbox div[data-baseweb="select"] {
            background-color: white !important;
            color: black !important;
        }
        .stButton>button {
            background-color: #ffffff !important;
            color: #004d00 !important;
            font-weight: bold;
        }
        .stDataFrame thead tr th {
            background-color: #d9f2d9 !important;
            color: black !important;
        }
        .stDataFrame tbody tr td {
            background-color: #eaf8ea !important;
            color: black !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.subheader("🚛 Cadastro de Frota")

    aba1, aba2 = st.tabs(["➕ Nova Frota", "🔍 Frotas Cadastradas"])

    with aba1:
        with st.form("form_frota"):
            col1, col2 = st.columns(2)
            with col1:
                num_frota = st.text_input("Nº Frota", placeholder="Ex: FR-06", key="num_frota")
                classe_mec = st.text_input("Classe Mecânica", placeholder="Ex: CAMINHÃO TRATOR", key="classe_mec")
                classe_op = st.text_input("Classe Operacional", placeholder="Ex: CAVALO MECÂNICO", key="classe_op")
                placa = st.text_input("Placa", placeholder="Ex: RNE8A74", key="placa").upper()
            with col2:
                modelo = st.text_input("Modelo", placeholder="Ex: FH540 6X4T_ CE", key="modelo")
                marca = st.text_input("Marca", placeholder="Ex: VOLVO", key="marca")
                ano = st.number_input("Ano de Fabricação", min_value=1990, max_value=2050, step=1, key="ano")
                chassi = st.text_input("Chassi", placeholder="Ex: 9BVRG40D5ME899353", key="chassi")
            foto = st.file_uploader("Foto do Veículo", type=["jpg", "jpeg", "png"], key="foto")

            submitted = st.form_submit_button("Salvar")

        if submitted:
            conn.execute("""
                INSERT OR REPLACE INTO frota (
                    num_frota, classe_mecanica, classe_operacional, placa,
                    modelo, marca, ano_fabricacao, chassi
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (num_frota, classe_mec, classe_op, placa, modelo, marca, ano, chassi))
            conn.commit()

            if foto:
                with open(os.path.join(FOTOS_PATH, f"{placa}.jpg"), "wb") as f:
                    f.write(foto.read())

            st.success("Frota salva com sucesso!")

    with aba2:
        df = pd.read_sql("SELECT * FROM frota", conn)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filtro_frota = st.text_input("Nº Frota", key="filtro_frota")
        with col2:
            filtro_mec = st.text_input("Classe Mecânica", key="filtro_mec")
        with col3:
            filtro_op = st.text_input("Classe Operacional", key="filtro_op")
        with col4:
            filtro_marca = st.text_input("Marca", key="filtro_marca")

        if filtro_frota:
            df = df[df['num_frota'].str.contains(filtro_frota, case=False, na=False)]
        if filtro_mec:
            df = df[df['classe_mecanica'].str.contains(filtro_mec, case=False, na=False)]
        if filtro_op:
            df = df[df['classe_operacional'].str.contains(filtro_op, case=False, na=False)]
        if filtro_marca:
            df = df[df['marca'].str.contains(filtro_marca, case=False, na=False)]

        df = df.drop(columns=['id'])  # Oculta a coluna id

        # Renomeia as colunas para títulos mais amigáveis
        df = df.rename(columns={
            'num_frota': 'Nº Frota',
            'classe_mecanica': 'Classe Mecânica',
            'classe_operacional': 'Classe Operacional',
            'placa': 'Placa',
            'modelo': 'Modelo',
            'marca': 'Marca',
            'ano_fabricacao': 'Ano de Fabricação',
            'chassi': 'Chassi'
        })

        if com_expansor:
            with st.expander("📋 Ver Frotas Cadastradas"):
                st.dataframe(df, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)

