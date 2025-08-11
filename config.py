# config.py
import streamlit as st
from pathlib import Path

# data.db na raiz do projeto
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data.db"

def apply_config() -> None:
    """
    Só configura a página. Nada de CSS, nada de st.sidebar, nada de markdown aqui.
    Deixe todo o CSS no app.py.
    """
    st.set_page_config(
        page_title="Controle de Frota",
        page_icon="🚚",
        layout="wide",                  # dá espaço máximo pro conteúdo da direita
        initial_sidebar_state="expanded"
    )

    # Estilos globais para harmonizar com o painel verde
    st.markdown("""
    <style>
      /* ===== Tema base ===== */
      .stApp, .block-container { background-color:#004d00 !important; color:#ffffff !important; }

      /* ===== Conteúdo central, confortável p/ 15" ===== */
      main .block-container{
        max-width: 1180px;         /* ajuste fino: 1100–1240 conforme seu gosto */
        margin: 0 auto;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: .6rem !important;
        padding-bottom: .6rem !important;
      }
      main .element-container{ margin-bottom:.6rem !important; }
      h1,h2,h3,h4{ margin:.25rem 0 .5rem !important; }

      /* ===== Sidebar mais estreita e compacta ===== */
      section[data-testid="stSidebar"]{
        background-color:#003300 !important; z-index:1000 !important;
        width: 250px !important; min-width: 250px !important;
      }
      section[data-testid="stSidebar"] .block-container{
        padding-top:.6rem !important; padding-bottom:.6rem !important;
      }
      section[data-testid="stSidebar"] *{ color:#ffffff !important; }
      section[data-testid="stSidebar"] .element-container{ margin-bottom:.45rem !important; }

      /* ===== Menu lateral enxuto ===== */
      .stRadio > div{ display:flex; flex-direction:column; gap:.25rem; }
      .stRadio [role="radiogroup"] label{
        background-color:#006400; color:#ffffff; padding:.55rem .8rem;
        border-radius:10px; cursor:pointer; transition:filter .15s ease; font-weight:600; font-size:.95rem;
      }
      .stRadio [role="radiogroup"] label:hover{ filter:brightness(1.08); }
      .stRadio [role="radio"][aria-checked="true"]+div label{ background-color:#2e7d32 !important; }

      /* ===== Entradas/tabs um pouco menores ===== */
      .stTabs [data-baseweb="tab"]{ padding:.25rem .6rem !important; font-size:.95rem !important; }
      .stTextInput>div>div>input, .stNumberInput input{ min-height: 38px !important; }
      div[data-baseweb="select"] > div{ min-height: 38px !important; }

      /* ===== Tabelas ===== */
      thead tr th{ background:#d9f2d9 !important; color:#000 !important; }
      tbody tr td{ background:#eaf8ea !important; color:#000 !important; }

      /* ===== Botões padrão ===== */
      .stButton>button{ background:#ffffff !important; color:#004d00 !important; font-weight:700; border:0; border-radius:10px; }

      /* ===== Footer menor ===== */
      .app-footer{
        position:fixed; right:18px; bottom:12px; z-index:500; pointer-events:none;
        background:rgba(234,248,234,.95); color:#0a2e0a; border:1px solid #bfe8bf;
        border-radius:10px; padding:4px 8px; font-size:11px; box-shadow:0 4px 14px rgba(0,0,0,.15);
      }
      .app-footer b{ color:#0a2e0a; }

      /* ===== Card usuário + botão sair ===== */
      .fixed-user-card{ position:sticky; top:0; z-index:200; background:#003300; padding-bottom:6px; margin-bottom:6px; }
      .user-row{ display:flex; justify-content:space-between; align-items:center; background:#0b3d0b; padding:6px 10px; border-radius:10px; }
      .user-info{ display:flex; flex-direction:column; }
      .user-info .name{ font-weight:700; }
      .user-info .meta{ color:#cfd8dc; font-size:12px; }
      div[data-testid="stSidebar"] .logout-btn-small button{
        background-color:#ff4d4d !important; color:#000000 !important; font-weight:700 !important;
        border:none !important; border-radius:6px !important; padding:.25rem .5rem !important;
        font-size:.8rem !important; width:auto !important; display:inline-block !important; box-shadow:0 2px 6px rgba(0,0,0,.15);
      }
      div[data-testid="stSidebar"] .logout-btn-small button:hover{ background-color:#e63939 !important; color:#000000 !important; }

      /* ===== Logo clicável sem “barra branca” ===== */
      .logo-wrap{ position:relative; display:inline-block; margin-bottom:.4rem; }
      .logo-wrap img{ display:block; border-radius:8px; }
      .logo-wrap .hit-area{ position:absolute; inset:0; }
      .logo-wrap .hit-area .stButton>button{
        width:100% !important; height:100% !important;
        background:transparent !important; border:none !important;
        padding:0 !important; box-shadow:none !important; outline:none !important;
        color:transparent !important; cursor:pointer;
      }
      .logo-wrap .hit-area .stButton>button:hover,
      .logo-wrap .hit-area .stButton>button:focus{
        background:transparent !important; box-shadow:none !important; outline:none !important;
      }

      /* ===== Separador discreto ===== */
      .sidebar-hr{ border:0; border-top:1px solid rgba(255,255,255,.08); margin:.35rem 0; }
    </style>
    """, unsafe_allow_html=True)