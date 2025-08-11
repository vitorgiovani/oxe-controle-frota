import os
import subprocess
from datetime import datetime
import base64
import streamlit as st
import inspect  # <- precisa para o helper

from config import apply_config
from db import bootstrap
from modules import auth, cadastro_frota, abertura_os, manutencao, relatorios
import modules.listar_editar_carros as listar_editar_carros

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")


def get_git_commit_hash():
    try:
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        return commit_hash
    except Exception:
        return "no-git"

# --- helper: chama .show() só com kwargs suportados (evita TypeError no deploy)
def call_show(fn, **kwargs):
    try:
        sig = inspect.signature(fn)
        allowed = {k: v for k, v in kwargs.items() if k in sig.parameters}
        return fn(**allowed)
    except Exception:
        # se não der pra inspecionar ou ainda assim der ruim, chama sem kwargs
        return fn()


# ===================== Config & Bootstrap =====================
apply_config()
bootstrap()

# ===================== Login =====================
user = auth.require_login()

# Aba padrão após login
if "menu" not in st.session_state:
    st.session_state["menu"] = "Início"

# --- trata clique no logo via ?home=1 (sem voltar pra tela de login)
try:
    qp = st.query_params  # Streamlit 1.31+
    if qp.get("home") in ("1", "true", "True"):
        st.session_state["menu"] = "Início"
        qp.clear()
except Exception:
    qs = st.experimental_get_query_params()
    if (qs.get("home") or [""])[0] in ("1", "true", "True"):
        st.session_state["menu"] = "Início"
        st.experimental_set_query_params()


# ===================== ESTILO GLOBAL =====================
st.markdown("""
<style>
  /* ===== Cores base ===== */
  html, body, [data-testid="stAppViewContainer"]{ background:#004d00 !important; }
  .stApp{ color:#ffffff !important; }

  /* ===== Topo (header/toolbar) verde e sem sombras ===== */
  header[data-testid="stHeader"],
  [data-testid="stToolbar"], .stAppToolbar{
    background:#004d00 !important;
    border:none !important; box-shadow:none !important;
  }
  header[data-testid="stHeader"] *{ color:#ffffff !important; }

  /* ===== Sidebar mais colada e sem “barrinhas” ===== */
  section[data-testid="stSidebar"]{
    background:#003300 !important;
    width:270px !important; min-width:270px !important;
    overflow-y:auto; border-right:none !important; box-shadow:none !important;
  }
  section[data-testid="stSidebar"] .block-container{ padding:.35rem .60rem !important; }
  section[data-testid="stSidebar"] .element-container{ margin-bottom:.28rem !important; }
  section[data-testid="stSidebar"] *{ color:#ffffff !important; }

  /* esconder qualquer botão/linha/separador da sidebar */
  [data-testid="stSidebarCollapseButton"],
  section[data-testid="stSidebar"] hr,
  section[data-testid="stSidebar"] [role="separator"]{ display:none !important; }

  /* ===== Logo clicável (sem quadrado branco) ===== */
  .logo-link{ display:block; line-height:0; margin:.15rem auto .20rem auto; text-align:center; }
  .logo-img{ display:block; width:180px; height:auto; margin:0 auto; border-radius:8px; }

  /* ===== Card de usuário/SAIR compacto ===== */
  .fixed-user-card{ position:sticky; top:0; z-index:200; background:#003300; padding-bottom:2px; }
  .user-row{ display:flex; justify-content:space-between; align-items:center; background:#0b3d0b; padding:4px 8px; border-radius:10px; }
  .user-info .name{ font-weight:700; font-size:.90rem; }
  .user-info .meta{ color:#cfe7cf; font-size:.72rem; }
  div[data-testid="stSidebar"] .logout-btn-small button{
    background:#ff4d4d !important; color:#000 !important; font-weight:700 !important;
    border:none !important; border-radius:6px !important; padding:.22rem .50rem !important; font-size:.80rem !important;
    width:auto !important; box-shadow:0 2px 6px rgba(0,0,0,.15);
  }

  /* ===== Menu da sidebar enxuto e sem quebra ===== */
  .stRadio > div{ display:flex; flex-direction:column; gap:.12rem !important; }
  .stRadio [role="radiogroup"] label{
    background:#0d5c13; color:#fff; padding:.44rem .66rem !important;
    border-radius:12px; font-weight:600; font-size:.95rem !important;
    white-space:nowrap !important; line-height:1.1;
  }
  .stRadio [role="radiogroup"] label:hover{ filter:brightness(1.08); }
  .stRadio [role="radio"][aria-checked="true"]+div label{ background:#2e7d32 !important; }

  /* ===== Conteúdo da direita: largo e lá em cima ===== */
  [data-testid="stAppViewContainer"] .main,
  [data-testid="stAppViewContainer"] .main > div,
  [data-testid="stAppViewContainer"] .main > div > div{ max-width:none !important; }
  main .block-container{
    width: calc(100vw - 290px) !important;   /* 270 da sidebar + ~20 de respiro */
    max-width:none !important;
    margin:0 !important; padding:.55rem 1.2rem !important;
  }

  /* ===== Menos espaços verticais no miolo ===== */
  main [data-testid="stVerticalBlock"]{ gap:.36rem !important; }
  main [data-testid="stHorizontalBlock"]{ gap:.36rem !important; }
  main .element-container{ margin-bottom:.36rem !important; }
  h1,h2,h3,h4{ margin:.18rem 0 .30rem !important; }

  /* Inputs baixinhos e sempre 100% de largura */
  .stTextInput>div>div, .stNumberInput>div>div, div[data-baseweb="select"]>div{ min-height:34px !important; width:100% !important; }

  /* Tabelas e gráficos ocupam tudo */
  .stDataFrame, .stTable{ width:100% !important; }

  /* ===== Footer pequeno ===== */
  .app-footer{
    position:fixed; right:18px; bottom:12px; z-index:500; pointer-events:none;
    background:rgba(234,248,234,.95); color:#0a2e0a; border:1px solid #bfe8bf;
    border-radius:10px; padding:4px 8px; font-size:11px; box-shadow:0 4px 14px rgba(0,0,0,.15);
  }
  .app-footer b{ color:#0a2e0a; }
</style>
""", unsafe_allow_html=True)

# ===================== SIDEBAR =====================
with st.sidebar:
    logo_path = "assets/oxe.logo.png"
    if os.path.exists(logo_path):
        # img como data URI, clicável, sem botão
        with open(logo_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        st.markdown(
            f'<a href="?home=1" class="logo-link">'
            f'  <img src="data:image/png;base64,{b64}" alt="Oxe Energia" class="logo-img" />'
            f'</a>',
            unsafe_allow_html=True
        )
    else:
        st.warning("⚠️ Logo da OXE não encontrado em 'assets/oxe.logo.png'")

    # Card usuário + sair
    st.markdown('<div class="fixed-user-card">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="user-row">
          <div class="user-info">
            <div class="name">👋 Olá, {user['name']}</div>
            <div class="meta">{user['username']} · <i>{user['role']}</i></div>
          </div>
          <div class="logout-btn-small">
        """,
        unsafe_allow_html=True
    )
    if st.button("🚪", key="logout-small", help="Sair"):
        auth.logout()
        st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

    # Menu
    options = ["Início", "Frota", "Ordens de Serviço", "Manutenção"]
    if user.get("role") == "admin":
        options.append("Admin (Usuários)")
    default_index = options.index(st.session_state.get("menu", "Início")) if st.session_state.get("menu", "Início") in options else 0
    selecionado = st.radio(label="", options=options, index=default_index)
    st.session_state["menu"] = selecionado

# ===================== ROTEAMENTO =====================
menu = st.session_state.get("menu", "Início")

if menu == "Início":
    # call_show evita TypeError quando a função não aceita graphs_only
    call_show(relatorios.show, graphs_only=True)

elif menu == "Frota":
    desired = st.session_state.get("frota_tab", "Listar/Editar")
    order = ["Cadastrar", "Listar/Editar"] if desired == "Cadastrar" else ["Listar/Editar", "Cadastrar"]
    tabA, tabB = st.tabs(order)

    if order[0] == "Cadastrar":
        with tabA:
            cadastro_frota.show()
        with tabB:
            st.session_state["frota_tab"] = "Listar/Editar"
            listar_editar_carros.page()
    else:
        with tabA:
            listar_editar_carros.page()
        with tabB:
            cadastro_frota.show()

elif menu == "Ordens de Serviço":
    abertura_os.show()

elif menu == "Manutenção":
    # idem para com_expansor
    call_show(manutencao.show, com_expansor=True)

elif menu == "Admin (Usuários)":
    from modules import admin_users
    admin_users.show()

# ===================== RODAPÉ =====================
_now_br = datetime.now().strftime("%d/%m/%Y %H:%M")
_commit = get_git_commit_hash()
st.markdown(
    f'<div class="app-footer">Versão <b>{APP_VERSION}</b> · {_now_br} · commit <b>{_commit}</b> · Desenvolvido por <b>NeuralSys</b></div>',
    unsafe_allow_html=True
)
