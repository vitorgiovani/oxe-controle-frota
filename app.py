import os
import subprocess
from datetime import datetime
import streamlit as st
from config import apply_config
from modules import auth, cadastro_frota, abertura_os, manutencao, relatorios

APP_VERSION = "1.0.0"

# ===================== Função para obter hash curto do commit =====================
def get_git_commit_hash():
    try:
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        return commit_hash
    except Exception:
        return "no-git"

# ===================== Config & Tema =====================
apply_config()

# ===================== Gate de Login =====================
user = auth.require_login()

# ===================== Reset layout pós-login =====================
st.markdown("""
<style>
  header[data-testid="stHeader"]   { display:block !important; }
  section[data-testid="stSidebar"] { display:block !important; }
  .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }
</style>
""", unsafe_allow_html=True)

# ===================== Estilos globais =====================
st.markdown("""
<style>
  .stApp, .block-container { background-color:#004d00 !important; color:#ffffff !important; }
  section[data-testid="stSidebar"] { background-color:#003300 !important; z-index: 1000 !important; }
  section[data-testid="stSidebar"] * { color:#ffffff !important; }

  .stRadio > div { display:flex; flex-direction:column; gap:0.5rem; }
  .stRadio [role="radiogroup"] label {
    background-color:#006400; color:#ffffff; padding:0.75rem 1.1rem;
    border-radius:10px; cursor:pointer; transition:filter .15s ease; font-weight:600;
  }
  .stRadio [role="radiogroup"] label:hover { filter:brightness(1.08); }
  .stRadio [role="radio"][aria-checked="true"]+div label { background-color:#2e7d32 !important; }

  thead tr th { background:#d9f2d9 !important; color:#000 !important; }
  tbody tr td { background:#eaf8ea !important; color:#000 !important; }

  /* estilo padrão dos botões do app */
  .stButton>button {
    background:#ffffff !important; color:#004d00 !important; font-weight:700;
    border:0; border-radius:10px;
  }

  .app-footer {
    position: fixed; right: 18px; bottom: 12px; z-index: 500; pointer-events: none;
    background: rgba(234, 248, 234, 0.95); color:#0a2e0a; border: 1px solid #bfe8bf;
    border-radius: 10px; padding: 6px 10px; font-size: 12px; box-shadow: 0 4px 14px rgba(0,0,0,.15);
  }
  .app-footer b { color:#0a2e0a; }
</style>
""", unsafe_allow_html=True)

# ===================== Estilo do card de usuário fixo + botão SAIR =====================
st.markdown("""
<style>
  /* Card fixo no topo */
  .fixed-user-card {
    position: sticky;
    top: 0;
    z-index: 200;
    background-color: #003300;
    padding-bottom: 10px;
    margin-bottom: 10px;
  }
  .user-row {
    display:flex; justify-content:space-between; align-items:center;
    background:#0b3d0b; padding:8px 12px; border-radius:10px;
  }
  .user-info { display:flex; flex-direction:column; }
  .user-info .name { font-weight:700; }
  .user-info .meta { color:#cfd8dc; font-size:12px; }

  /* Botão SAIR */
  div[data-testid="stSidebar"] .logout-btn-small button {
    background-color:#ff4d4d !important;
    color:#000000 !important;
    font-weight:700 !important;
    border:none !important;
    border-radius:6px !important;
    padding:0.3rem 0.6rem !important;
    font-size:0.8rem !important;
    width:auto !important;
    display:inline-block !important;
    box-shadow:0 2px 6px rgba(0,0,0,.15);
  }
  div[data-testid="stSidebar"] .logout-btn-small button:hover {
    background-color:#e63939 !important;
    color:#000000 !important;
  }
</style>
""", unsafe_allow_html=True)

# ===================== Sidebar =====================
with st.sidebar:
    logo_path = "assets/oxe.logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=200)
    else:
        st.warning("⚠️ Logo da OXE não encontrado em 'assets/oxe.logo.png'")

    st.markdown("---")

    # Card fixo com saudação + botão sair
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
    if st.button("🚪", key="logout-small", help="Sair"):  # só ícone, com tooltip
        auth.logout()
        st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    options = ["Frota", "Ordens de Serviço", "Manutenção", "Relatórios"]
    if user.get("role") == "admin":
        options.append("Admin (Usuários)")
    menu = st.radio(label="", options=options, index=0)

# ===================== Roteamento =====================
if menu == "Frota":
    cadastro_frota.show()
elif menu == "Ordens de Serviço":
    abertura_os.show()
elif menu == "Manutenção":
    manutencao.show(com_expansor=True)
elif menu == "Relatórios":
    relatorios.show()
elif menu == "Admin (Usuários)":
    from modules import admin_users
    admin_users.show()

# ===================== Rodapé =====================
_now_br = datetime.now().strftime("%d/%m/%Y %H:%M")
_commit = get_git_commit_hash()
st.markdown(
    f'<div class="app-footer">Versão <b>{APP_VERSION}</b> · {_now_br} · commit <b>{_commit}</b> · Desenvolvido por <b>NeuralSys</b></div>',
    unsafe_allow_html=True
)
