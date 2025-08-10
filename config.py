# config.py
import streamlit as st

def apply_config():
    """
    Aplica configurações globais de tema e layout
    """
    # Configura layout e tema
    st.set_page_config(
        page_title="Controle de Frota - OXE",
        page_icon="🚚",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Estilos globais para harmonizar com o painel verde
    st.markdown("""
    <style>
      /* Remove padding lateral padrão */
      .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
      }
      /* Links */
      a { color: #90ee90 !important; text-decoration: none; }
      a:hover { text-decoration: underline; }
      /* Tabelas */
      table { color: #ffffff !important; }
      thead th { background-color: #006400 !important; color: #ffffff !important; }
      tbody tr:nth-child(even) { background-color: rgba(255, 255, 255, 0.05); }
      /* Botões */
      .stButton>button {
        background-color: #2e7d32 !important;
        color: #ffffff !important;
        font-weight: 600;
        border: none;
        border-radius: 8px;
      }
      .stButton>button:hover {
        filter: brightness(1.05);
      }
    </style>
    """, unsafe_allow_html=True)
