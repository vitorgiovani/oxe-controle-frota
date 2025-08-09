# app.py
import streamlit as st
import os
from config import apply_config
from modules import cadastro_frota, abertura_os, manutencao, relatorios

apply_config()

# Logo da OXE no topo da barra lateral
with st.sidebar:
    logo_path = "assets/oxe.logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=200)
    else:
        st.warning("⚠️ Logo da OXE não encontrado em 'assets/oxe.logo.jpg'")

# Estilo customizado com fundo verde escuro e menu sem quebra de linha
st.markdown(
    """
    <style>
    .main, .block-container {
        background-color: #004d00 !important; /* verde escuro */
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #003300 !important; /* verde ainda mais escuro */
    }

    .stSidebar label, .stSidebar span, .stSidebar div {
        color: white !important;
        font-weight: bold;
        font-size: 18px !important;
    }

    .stRadio > div {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        white-space: nowrap;
    }

    .stRadio > div > label {
        background-color: #006400;
        color: white;
        padding: 0.75rem 1.2rem;
        border-radius: 8px;
        cursor: pointer;
        transition: background-color 0.3s;
        font-size: 18px !important;
        white-space: nowrap;
    }

    .stRadio > div > label:hover {
        background-color: #228B22;
    }

    .stRadio > div > label[data-selected="true"] {
        background-color: #2e7d32 !important;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True
)

menu = st.sidebar.radio("", (
    "Frota",
    "Ordens de Serviço",
    "Manutenção",
    "Relatórios"
))

if menu == "Frota":
    cadastro_frota.show()
elif menu == "Ordens de Serviço":
    abertura_os.show()
elif menu == "Manutenção":
    manutencao.show(com_expansor=True)
elif menu == "Relatórios":
    relatorios.show(estilo_visual=True)
