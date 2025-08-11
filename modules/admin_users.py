import streamlit as st
from modules import auth
import pandas as pd

def _inject_css():
    st.markdown("""
    <style>
      .stApp { background-color:#004d00 !important; color:#fff !important; }
      header[data-testid="stHeader"] { background-color:#004d00 !important; }
      .stTabs [data-baseweb="tab"] {
        background-color:#006400 !important; color:#ffffff !important;
        font-weight:700; font-size:16px;
      }
      .card { background:#eaf8ea; color:#0a2e0a; border:1px solid #bfe8bf; border-radius:12px; padding:16px; }
      .stButton>button {
        background:#ffffff !important; color:#004d00 !important; font-weight:700;
        border:0; border-radius:8px;
      }
      .stDataFrame thead tr th { background:#d9f2d9 !important; color:#000 !important; }
      .stDataFrame tbody tr td { background:#eaf8ea !important; color:#000 !important; }
    </style>
    """, unsafe_allow_html=True)

def show():
    user = auth.require_login()
    if user.get("role") != "admin":
        st.error("Acesso restrito aos administradores.")
        st.stop()

    _inject_css()
    st.subheader("👤 Administração de Usuários")

    tab_list, tab_create, tab_update = st.tabs(["📋 Lista", "➕ Criar usuário", "🛠️ Alterar / (Des)ativar"])

    # ===== Lista
    with tab_list:
        df = auth.list_users()
        # Deixa mais amigável
        if not df.empty:
            df = df.rename(columns={"username":"Usuário","name":"Nome","role":"Papel","active":"Ativo","created_at":"Criado em"})
            df["Ativo"] = df["Ativo"].map({1:"Sim", 0:"Não"})
        st.dataframe(df, use_container_width=True)

    # ===== Criar
    with tab_create:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            username = st.text_input("Usuário (login)", placeholder="ex: joao.silva").lower().strip()
            name     = st.text_input("Nome completo", placeholder="João da Silva").strip()
            role     = st.selectbox("Papel", ["user", "admin"], index=0)
        with c2:
            pwd  = st.text_input("Senha", type="password")
            pwd2 = st.text_input("Confirmar senha", type="password")
            active = st.checkbox("Ativo", value=True)
        if st.button("Criar usuário", use_container_width=True):
            if not username or not name or not pwd:
                st.error("Preencha usuário, nome e senha.")
            elif pwd != pwd2:
                st.error("As senhas não coincidem.")
            else:
                try:
                    auth.create_user(username, name, pwd, role, active)
                except Exception as e:
                    st.error(f"Erro ao criar usuário: {e}")
                else:
                    st.success("Usuário criado com sucesso!")

        st.markdown('</div>', unsafe_allow_html=True)

    # ===== Alterar / (Des)ativar
    with tab_update:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        df_users = auth.list_users()
        users = df_users["username"].tolist() if not df_users.empty else []
        if not users:
            st.info("Nenhum usuário cadastrado ainda.")
        else:
            sel = st.selectbox("Selecione o usuário", users)
            urow = df_users[df_users["username"] == sel].iloc[0] if not df_users.empty else None

            st.markdown(f"**Nome:** {urow['name']}  \n**Papel atual:** `{urow['role']}`  \n**Ativo:** {'Sim' if urow['active']==1 else 'Não'}")

            st.markdown("---")
            st.markdown("### 🔑 Alterar senha")
            new_pwd  = st.text_input("Nova senha", type="password")
            new_pwd2 = st.text_input("Confirmar nova senha", type="password")
            if st.button("Salvar nova senha"):
                if not new_pwd:
                    st.error("Digite a nova senha.")
                elif new_pwd != new_pwd2:
                    st.error("As senhas não coincidem.")
                else:
                    auth.set_password(sel, new_pwd)
                    st.success("Senha alterada com sucesso.")

            st.markdown("---")
            st.markdown("### 🔁 (Des)ativar usuário")
            new_active = st.selectbox("Status", ["Ativo", "Inativo"], index=0 if urow["active"]==1 else 1)
            if st.button("Aplicar status"):
                auth.set_active(sel, new_active == "Ativo")
                st.success("Status atualizado.")

            st.markdown("---")
            st.markdown("### 🧭 Mudar papel (role)")
            new_role = st.selectbox("Papel", ["user", "admin"], index=0 if urow["role"]=="user" else 1)
            if st.button("Aplicar papel"):
                auth.set_role(sel, new_role)
                st.success("Papel atualizado.")

        st.markdown('</div>', unsafe_allow_html=True)
