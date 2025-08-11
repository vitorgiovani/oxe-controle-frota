# modules/auth.py
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Optional, Dict
import pandas as pd
import streamlit as st
from db import get_conn

USERS_TABLE = "usuarios"

# ==================== Model ====================
@dataclass
class User:
    id: int
    username: Optional[str]
    email: Optional[str]
    name: Optional[str]
    role: Optional[str]

    def as_dict(self) -> Dict:
        return {
            "id": self.id,
            "username": (self.username or "").strip(),
            "email": (self.email or "").strip(),
            "name": (self.name or "").strip(),
            "role": (self.role or "user").lower(),
        }

# ==================== Visual (login card translúcido) ====================
def _inject_login_css():
    st.markdown("""
    <style>
      /* tirar padding e sumir header/sidebar */
      .block-container{padding-top:0 !important;padding-bottom:0 !important;max-width:100% !important;}
      header[data-testid="stHeader"]{display:none !important;}
      section[data-testid="stSidebar"]{display:none !important;}

      /* fundo e centralização vertical */
      .stApp{
        background:linear-gradient(180deg,#0b3d0b 0%, #0a330a 50%, #0b3d0b 100%) !important;
        min-height:100vh !important; display:flex; align-items:center; justify-content:center;
      }

      /* wrapper central para limitar largura */
      .login-wrap{ width:100%; max-width:900px; margin:0 auto; padding:24px; }

      /* card = o próprio form */
      form.st-form{
        width:100%; max-width:760px; margin:0 auto;
        background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.18);
        border-radius:16px; padding:24px !important; box-shadow:0 10px 28px rgba(0,0,0,.35);
        backdrop-filter: blur(4px);
      }

      /* topo (logo + textos) */
      .login-logo{ text-align:center; margin-bottom:10px; }
      .login-title{ text-align:center; font-weight:800; font-size:28px; color:#fff; margin:4px 0 2px; }
      .login-sub{ text-align:center; font-size:13px; color:#d2e7d2; margin-bottom:18px; }

      /* cores de labels */
      label, .stMarkdown p, .stCheckbox label{ color:#e9f5e9 !important; }

      /* inputs em pílula */
      .stTextInput input, .stPassword input{
        background:#fff !important; color:#0a2e0a !important;
        border:0 !important; border-radius:999px !important; padding:.9rem 1rem !important;
        box-shadow: inset 0 0 0 1px #cfe7cf;
      }

      /* botão entrar, central e largo */
      .stButton>button{
        display:block; margin:8px auto 0 auto; width:60%;
        background:linear-gradient(180deg,#2e7d32 0%, #1b5e20 100%) !important;
        color:#fff !important; font-weight:800 !important; border:0 !important; border-radius:999px !important;
        padding:.9rem 1rem !important; box-shadow:0 3px 10px rgba(0,0,0,.25);
      }
      .stButton>button:hover{ filter:brightness(1.06); }

      /* rodapé */
      .login-footer{ color:#cfe7cf; font-size:12px; margin-top:14px; text-align:center; }
      .login-footer b{ color:#fff; }

      /* responsivo */
      @media(max-width:640px){
        form.st-form{ max-width: 94vw; padding:18px !important; }
        .stButton>button{ width:100%; }
      }
    </style>
    """, unsafe_allow_html=True)

# ==================== Infra & schema ====================
def _hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()

def _ensure_schema():
    """Garante colunas/índices e adiciona campos usados pelo admin (active/created_at)."""
    with get_conn() as conn:
        conn.execute(f"CREATE TABLE IF NOT EXISTS {USERS_TABLE} (id INTEGER PRIMARY KEY AUTOINCREMENT);")

        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({USERS_TABLE})")}
        if "email" not in cols:
            conn.execute(f"ALTER TABLE {USERS_TABLE} ADD COLUMN email TEXT;")
        if "senha_hash" not in cols:
            conn.execute(f"ALTER TABLE {USERS_TABLE} ADD COLUMN senha_hash TEXT;")
        if "nome" not in cols:
            conn.execute(f"ALTER TABLE {USERS_TABLE} ADD COLUMN nome TEXT;")
        if "username" not in cols:
            conn.execute(f"ALTER TABLE {USERS_TABLE} ADD COLUMN username TEXT;")
        if "role" not in cols:
            conn.execute(f"ALTER TABLE {USERS_TABLE} ADD COLUMN role TEXT DEFAULT 'user';")
        if "active" not in cols:
            conn.execute(f"ALTER TABLE {USERS_TABLE} ADD COLUMN active INTEGER DEFAULT 1;")
        if "created_at" not in cols:
            conn.execute(f"ALTER TABLE {USERS_TABLE} ADD COLUMN created_at TEXT DEFAULT (datetime('now'));")

        # índices
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({USERS_TABLE})")}
        if "email" in cols:
            conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_email ON {USERS_TABLE}(email);")
        if "username" in cols:
            conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_username ON {USERS_TABLE}(username);")

# ==================== Queries/helpers ====================
def _fetch_user_where(where_sql: str, params: tuple) -> Optional[User]:
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT id, username, email, nome AS name, role FROM {USERS_TABLE} {where_sql} LIMIT 1;",
            params
        ).fetchone()
    return User(**row) if row else None

def _get_user_by_login(login: str) -> Optional[User]:
    login = (login or "").strip()
    if not login:
        return None
    with get_conn() as conn:
        # username (case-insensitive + trim)
        row = conn.execute(
            f"""
            SELECT id, username, email, nome AS name, role
            FROM {USERS_TABLE}
            WHERE LOWER(TRIM(username)) = LOWER(TRIM(?))
            LIMIT 1
            """,
            (login,)
        ).fetchone()
        if row:
            return User(**row)
        # email (case-insensitive + trim)
        row = conn.execute(
            f"""
            SELECT id, username, email, nome AS name, role
            FROM {USERS_TABLE}
            WHERE LOWER(TRIM(email)) = LOWER(TRIM(?))
            LIMIT 1
            """,
            (login,)
        ).fetchone()
        return User(**row) if row else None

def _verify_password(user: User, pwd: str) -> bool:
    pwd = (pwd or "")
    expected_hash = _hash_password(pwd)
    with get_conn() as conn:
        # Quais colunas existem?
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({USERS_TABLE})")}
        select_cols = ["senha_hash"]
        if "hash_senha" in cols:
            select_cols.append("hash_senha")
        if "senha" in cols:
            select_cols.append("senha")

        row = conn.execute(
            f"SELECT {', '.join(select_cols)} FROM {USERS_TABLE} WHERE id=?",
            (user.id,)
        ).fetchone()
        if not row:
            return False

        # Valores salvos (ignorando None)
        saved_values = [(row[c] if isinstance(row, dict) else row[idx]) for idx, c in enumerate(select_cols)]
        saved_values = [s or "" for s in saved_values]

        # 1) Bate com SHA-256
        if expected_hash in saved_values:
            # garante migração p/ senha_hash se estiver faltando
            if "senha_hash" in select_cols and (row["senha_hash"] if isinstance(row, dict) else saved_values[select_cols.index("senha_hash")]) != expected_hash:
                conn.execute(f"UPDATE {USERS_TABLE} SET senha_hash=? WHERE id=?", (expected_hash, user.id))
            return True

        # 2) Bate com texto puro legado
        if pwd in saved_values:
            # migra para senha_hash
            conn.execute(f"UPDATE {USERS_TABLE} SET senha_hash=? WHERE id=?", (expected_hash, user.id))
            return True

    return False

# ==================== UI (login) ====================
def login_form():
    _inject_login_css()

    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    col = st.columns([1,1,1])[1]  # centro

    with col:
        # logo
        try:
            st.image("assets/oxe.logo.png", width=120)
        except Exception:
            st.markdown('<div class="login-logo"> </div>', unsafe_allow_html=True)

        st.markdown('<div class="login-title">Acesso ao Sistema</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Informe suas credenciais para continuar</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            st.text_input("Usuário", key="login_user", placeholder="seu.usuario")
            st.text_input("Senha", key="login_pwd", type="password", placeholder="••••••••")
            st.checkbox("Manter conectado neste navegador", key="login_keep", value=False)
            submitted = st.form_submit_button("Entrar")

        st.markdown('<div class="login-footer">Desenvolvido por <b>NeuralSys</b> • 2025</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        _ensure_schema()
        login = (st.session_state.get("login_user") or "").strip()
        pwd   = (st.session_state.get("login_pwd") or "")
        u = _get_user_by_login(login)
        if not u or not _verify_password(u, pwd):
            st.error("Usuário/e-mail ou senha inválidos.")
            return None
        return u
    return None

def require_login() -> dict:
    _ensure_schema()
    # sessão ativa?
    if "auth_user" in st.session_state and st.session_state["auth_user"]:
        return st.session_state["auth_user"]

    # primeiro acesso: criar admin
    with get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM {USERS_TABLE};").fetchone()["c"]

    if total == 0:
        _inject_login_css()
        st.markdown('<div class="login-logo"><img src="assets/oxe.logo.png" width="140"></div>', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Acesso ao Sistema</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Crie o usuário administrador inicial</div>', unsafe_allow_html=True)

        with st.form("create_first_admin"):
            username = st.text_input("Usuário (obrigatório)").strip().lower()
            email    = st.text_input("E-mail (opcional)").strip().lower()
            name     = st.text_input("Nome").strip()
            pwd1     = st.text_input("Senha", type="password")
            pwd2     = st.text_input("Confirmar senha", type="password")
            submitted = st.form_submit_button("Criar admin")
        if submitted:
            if not username or not pwd1:
                st.error("Usuário e senha são obrigatórios.")
            elif pwd1 != pwd2:
                st.error("As senhas não conferem.")
            else:
                try:
                    uid = create_user(username=username, email=email or None, name=name, password=pwd1, role="admin", active=True)
                    st.success(f"Admin criado (id={uid}). Faça login abaixo.")
                except Exception as e:
                    st.error(f"Não foi possível criar o admin: {e}")
        st.markdown('<div class="login-footer">Desenvolvido por <b>NeuralSys</b> • 2025</div>', unsafe_allow_html=True)
        st.stop()

    user = login_form()
    if user:
        st.session_state["auth_user"] = user.as_dict()
        st.rerun()
    st.stop()

# ==================== Admin helpers (CRUD para admin_users.py) ====================
def list_users() -> pd.DataFrame:
    """Retorna DataFrame com colunas esperadas pelo admin (id, username, email, name, role, active, created_at)."""
    _ensure_schema()
    with get_conn() as conn:
        rows = conn.execute(f"""
            SELECT id, username, email, nome AS name, role, active, created_at
            FROM {USERS_TABLE}
            ORDER BY id ASC
        """).fetchall()
    df = pd.DataFrame(rows, columns=["id","username","email","name","role","active","created_at"])
    return df

def get_user_by_id(user_id: int) -> Optional[User]:
    return _fetch_user_where("WHERE id = ?", (user_id,))

def update_user(user_id: int, *, username: Optional[str] = None,
                email: Optional[str] = None, name: Optional[str] = None,
                role: Optional[str] = None, active: Optional[bool] = None) -> None:
    """Atualiza campos do usuário por id (apenas os informados)."""
    _ensure_schema()
    sets, vals = [], []
    if username is not None:
        sets.append("username = ?"); vals.append(username.strip().lower() or None)
    if email is not None:
        sets.append("email = ?"); vals.append((email or "").strip().lower() or None)
    if name is not None:
        sets.append("nome = ?"); vals.append((name or "").strip() or None)
    if role is not None:
        sets.append("role = ?"); vals.append((role or "user").lower())
    if active is not None:
        sets.append("active = ?"); vals.append(1 if active else 0)
    if not sets:
        return
    vals.append(user_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE {USERS_TABLE} SET {', '.join(sets)} WHERE id = ?;", vals)

def set_password(username: str, new_password: str) -> None:
    """Altera a senha pelo username (usado no admin)."""
    if not new_password or len(new_password) < 4:
        raise ValueError("Senha muito curta (mín. 4).")
    new_hash = _hash_password(new_password)
    with get_conn() as conn:
        conn.execute(f"UPDATE {USERS_TABLE} SET senha_hash = ? WHERE username = ?;", (new_hash, username))
        # sincroniza coluna legada se existir
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({USERS_TABLE})")}
        if "hash_senha" in cols:
            conn.execute(f"UPDATE {USERS_TABLE} SET hash_senha = ? WHERE username = ?;", (new_hash, username))

def set_active(username: str, is_active: bool) -> None:
    with get_conn() as conn:
        conn.execute(f"UPDATE {USERS_TABLE} SET active = ? WHERE username = ?;", (1 if is_active else 0, username))

def set_role(username: str, role: str) -> None:
    role = (role or "user").lower()
    with get_conn() as conn:
        conn.execute(f"UPDATE {USERS_TABLE} SET role = ? WHERE username = ?;", (role, username))

def delete_user(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute(f"DELETE FROM {USERS_TABLE} WHERE id = ?;", (user_id,))

# alias de compat
ensure_schema = _ensure_schema
