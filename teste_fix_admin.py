# fix_admin_sql.py
import sqlite3, hashlib, os

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")  # ajuste se seu .db estiver noutro lugar
ADMIN_USER = "admin"
NEW_PASS   = "1234"  # troque depois no sistema

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row

# 1) Garante tabela e colunas mínimas
con.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT)")
cols = {r["name"] for r in con.execute("PRAGMA table_info(usuarios)")}
def addcol(cname, csql):
    if cname not in cols:
        con.execute(f"ALTER TABLE usuarios ADD COLUMN {cname} {csql}")
        print(f"ADD coluna {cname}")
        cols.add(cname)

addcol("username", "TEXT")
addcol("email", "TEXT")
addcol("nome", "TEXT")
addcol("senha_hash", "TEXT")
addcol("role", "TEXT DEFAULT 'user'")
addcol("active", "INTEGER DEFAULT 1")
addcol("created_at", "TEXT DEFAULT (datetime('now'))")

# 2) Normaliza usernames
con.execute("UPDATE usuarios SET username = LOWER(TRIM(username)) WHERE username IS NOT NULL")

# 3) Upsert do admin
row = con.execute("SELECT id FROM usuarios WHERE username = ?", (ADMIN_USER,)).fetchone()
if not row:
    con.execute("""
        INSERT INTO usuarios (username, email, nome, senha_hash, role, active)
        VALUES (?, NULL, ?, ?, 'admin', 1)
    """, (ADMIN_USER, "Administrador", sha256(NEW_PASS)))
    print(f"✔ Criado usuário '{ADMIN_USER}' com senha '{NEW_PASS}'")
else:
    con.execute("UPDATE usuarios SET senha_hash = ?, role='admin', active=1 WHERE username = ?",
                (sha256(NEW_PASS), ADMIN_USER))
    print(f"✔ Senha do '{ADMIN_USER}' redefinida para '{NEW_PASS}' e marcado como admin/ativo")

con.commit()

# 4) Mostra estado final
final = con.execute("""
    SELECT id, username, role, active, LENGTH(COALESCE(senha_hash,'')) AS hash_len
    FROM usuarios WHERE username = ?
""", (ADMIN_USER,)).fetchone()
print("Estado final:", dict(final) if final else "não encontrado")
con.close()
