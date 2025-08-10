# modules/auth.py
import os, binascii, hashlib, sqlite3
from datetime import datetime
import streamlit as st

DB_PATH = "auth.db"
TABLE   = "users"

# ================= Hash seguro (PBKDF2-SHA256) =================
_ITER = 120_000

def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITER)
    return f"pbkdf2_sha256${_ITER}${binascii.hexlify(salt).decode()}${binascii.hexlify(dk).decode()}"

def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iter_s, salt_hex, hash_hex = stored.split("$")
        assert algo == "pbkdf2_sha256"
        iters = int(iter_s)
        salt  = binascii.unhexlify(salt_hex.encode())
        dk    = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
        return binascii.hexlify(dk).decode() == hash_hex
    except Exception:
        return False

# ================= Infra / SQLite =================
@st.cache_resource
def _conn():
    folder = os.path.dirname(DB_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.execute("PRAGMA foreign_keys = ON;")
    return c

def _ensure_table():
    con = _conn()
    con.execute(f"""
      CREATE TABLE IF NOT EXISTS {TABLE} (
        username   TEXT PRIMARY KEY,
        name       TEXT,
        password   TEXT NOT NULL,
        role       TEXT DEFAULT 'user',
        active     INTEGER DEFAULT 1,
        created_at TEXT
      );
    """)
    con.commit()

def _ensure_default_admin():
    """Cria admin inicial (env -> fallback)."""
    con = _conn()
    cur = con.execute(f"SELECT COUNT(*) FROM {TABLE};").fetchone()
    if cur and cur[0] == 0:
        admin_user = os.getenv("ADMIN_USER", "admin").lower().strip()
        admin_pwd  = os.getenv("ADMIN_PASSWORD", "admin123")
        con.execute(
            f"INSERT INTO {TABLE} (username, name, password, role, active, created_at) VALUES (?,?,?,?,?,?)",
            (admin_user, "Administrador", _hash_password(admin_pwd), "admin", 1, datetime.utcnow().isoformat())
        )
        con.commit()

def _ensure_demo_user():
    """Usuário de demonstração (remova em produção se quiser)."""
    con = _conn()
    demo_user = "apresentacao"
    demo_pwd  = "oxe2025"
    row = con.execute(f"SELECT 1 FROM {TABLE} WHERE username=?;", (demo_user,)).fetchone()
    if not row:
        con.execute(
            f"INSERT INTO {TABLE} (username,name,password,role,active,created_at) VALUES (?,?,?,?,?,?)",
            (demo_user, "Usuário de Demonstração", _hash_password(demo_pwd), "user", 1, datetime.utcnow().isoformat())
        )
        con.commit()

# ================= API Pública =================
def init_auth():
    _ensure_table()
    _ensure_default_admin()
    _ensure_demo_user()

def login_form():
    # CSS mínimo e estável (só fundo/cores; nada de wrappers)
    st.markdown("""
    <style>
      header[data-testid="stHeader"], section[data-testid="stSidebar"] { display:none !important; }
      .stApp, .main, .block-container, [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #0b3d0b 0%, #0e5a0e 100%) !important;
      }
      .login-title  { text-align:center; font-weight:800; font-size:22px; color:#eaffec; margin:6px 0 4px; }
      .login-sub    { text-align:center; font-size:13px;  color:#dff7e1; margin-bottom:14px; }
      .stTextInput>div>div>input, .stPassword>div>div>input {
        height:40px!important; font-size:15px!important; border-radius:9999px!important;
        background:#fff!important; color:#0c140c!important;
      }
      .stButton>button{
        width:100%; height:44px; border-radius:9999px;
        background:#2e7d32!important; color:#fff!important; font-weight:700; font-size:15px;
        border:0;
      }
      .stButton>button:hover{ filter:brightness(1.06); }
      .login-foot { text-align:center; font-size:12px; color:#cfead3; margin-top:10px; }
    </style>
    """, unsafe_allow_html=True)

    # Layout: 3 colunas para centralizar e limitar a largura
    left, center, right = st.columns([1, 0.9, 1])  # a coluna do meio ~40% da tela

    with center:
        # Logo centralizado
        from os.path import exists
        logo_path = "assets/oxe.logo.png"
        if exists(logo_path):
            st.image(logo_path, use_container_width=False, width=210)

        st.markdown('<div class="login-title">Acesso ao Sistema</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Informe suas credenciais para continuar</div>', unsafe_allow_html=True)

        # Campos (ficam naturalmente limitados à largura da coluna central)
        u = st.text_input("Usuário", key="auth_username", placeholder="seu.usuario")
        p = st.text_input("Senha",   key="auth_password", type="password", placeholder="••••••••")
        remember = st.checkbox("Manter conectado neste navegador", value=False)

        ok = st.button("Entrar", use_container_width=True)
        st.markdown('<div class="login-foot">Desenvolvido por <strong>NeuralSys</strong> • 2025</div>', unsafe_allow_html=True)

    # Autenticação
    if ok:
        username = (u or "").strip().lower()
        con = _conn()
        row = con.execute(
            f"SELECT username,name,password,role,active FROM {TABLE} WHERE username=?;", (username,)
        ).fetchone()
        if not row:
            st.error("Usuário ou senha inválidos."); return False
        db_username, name, pwd_hash, role, active = row
        if not active:
            st.error("Usuário inativo. Fale com o administrador."); return False
        if not _verify_password(p or "", pwd_hash):
            st.error("Usuário ou senha inválidos."); return False

        st.session_state["auth_user"] = {"username": db_username, "name": name, "role": role}
        st.session_state["auth_remember"] = bool(remember)
        st.rerun()
    return False

def require_login():
    init_auth()
    user = st.session_state.get("auth_user")
    if user:
        return user
    login_form()
    st.stop()

def is_logged_in() -> bool:
    return "auth_user" in st.session_state

def current_user() -> dict | None:
    return st.session_state.get("auth_user")

def logout():
    for k in ["auth_user", "auth_remember", "auth_username", "auth_password"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

# ================= Helpers de administração =================
def create_user(username: str, name: str, password: str, role: str = "user", active: bool = True):
    username = (username or "").strip().lower()
    con = _conn()
    con.execute(
        f"INSERT INTO {TABLE} (username,name,password,role,active,created_at) VALUES (?,?,?,?,?,?)",
        (username, name.strip(), _hash_password(password), role, 1 if active else 0, datetime.utcnow().isoformat())
    )
    con.commit()

def set_password(username: str, new_password: str):
    username = (username or "").strip().lower()
    con = _conn()
    con.execute(f"UPDATE {TABLE} SET password=? WHERE username=?;", (_hash_password(new_password), username))
    con.commit()

def set_active(username: str, active: bool):
    username = (username or "").strip().lower()
    con = _conn()
    con.execute(f"UPDATE {TABLE} SET active=? WHERE username=?;", (1 if active else 0, username))
    con.commit()

def set_role(username: str, role: str):
    username = (username or "").strip().lower()
    role = (role or "user").strip().lower()
    if role not in ("user", "admin"):
        role = "user"
    con = _conn()
    con.execute(f"UPDATE {TABLE} SET role=? WHERE username=?;", (role, username))
    con.commit()

def list_users():
    import pandas as pd
    con = _conn()
    return pd.read_sql(f"SELECT username, name, role, active, created_at FROM {TABLE} ORDER BY username;", con)
