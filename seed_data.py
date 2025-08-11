import sqlite3
import hashlib
import random
from datetime import datetime, timedelta

DB_PATH = "data.db"

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def create_tables(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        nome TEXT NOT NULL,
        hash_senha TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','user','viewer')),
        ativo INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS veiculos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        placa TEXT UNIQUE NOT NULL,
        modelo TEXT NOT NULL,
        ano INTEGER,
        status TEXT NOT NULL DEFAULT 'ativo', -- ativo, manutencao, inativo
        criado_em TEXT NOT NULL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        veiculo_id INTEGER NOT NULL,
        descricao TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'aberta', -- aberta, em_andamento, fechada
        aberto_em TEXT NOT NULL,
        fechado_em TEXT,
        responsavel_id INTEGER,
        FOREIGN KEY (veiculo_id) REFERENCES veiculos(id),
        FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS manutencoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        veiculo_id INTEGER NOT NULL,
        tipo TEXT NOT NULL,   -- preventiva, corretiva
        custo REAL,
        data TEXT NOT NULL,
        obs TEXT,
        FOREIGN KEY (veiculo_id) REFERENCES veiculos(id)
    );
    """)

def seed_usuarios(cur, n=30):
    nomes = [
        "Ana", "Bruno", "Carla", "Diego", "Eduarda", "Felipe", "Gabriela", "Henrique",
        "Isabela", "João", "Karina", "Lucas", "Mariana", "Natan", "Olivia", "Paulo",
        "Queila", "Rafael", "Sofia", "Thiago", "Ursula", "Valter", "Wesley", "Xavier",
        "Yara", "Zilda", "Beto", "Cris", "Dani", "Elias"
    ]
    roles = ["user", "viewer", "user", "user", "viewer"]
    base = datetime.now() - timedelta(days=120)

    # garante um admin
    cur.execute("SELECT COUNT(1) FROM usuarios WHERE username='admin'")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO usuarios(username, nome, hash_senha, role, ativo, created_at)
            VALUES (?, ?, ?, 'admin', 1, ?)
        """, ("admin", "Administrador", sha256("admin123"), base.isoformat()))
    # gera mais usuários
    for i in range(n):
        u = f"user{i+1:02d}"
        nome = nomes[i % len(nomes)] + f" {random.choice(['Silva','Souza','Lima','Costa','Almeida'])}"
        role = random.choice(roles)
        created = (base + timedelta(days=random.randint(0, 120))).isoformat()
        try:
            cur.execute("""
                INSERT INTO usuarios(username, nome, hash_senha, role, ativo, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (u, nome, sha256("123"), role, 1, created))
        except sqlite3.IntegrityError:
            pass  # se já existir, ignora

def seed_veiculos(cur, n=30):
    modelos = ["Hilux", "Strada", "Fiorino", "S10", "Ducato", "Sprinter", "Toro", "Duster Oroch"]
    status_opts = ["ativo", "manutencao", "ativo", "ativo", "inativo"]
    base = datetime.now() - timedelta(days=200)

    for i in range(n):
        placa = f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}-{random.randint(1000,9999)}"
        modelo = random.choice(modelos)
        ano = random.randint(2010, 2024)
        status = random.choice(status_opts)
        criado = (base + timedelta(days=random.randint(0, 200))).isoformat()
        try:
            cur.execute("""
                INSERT INTO veiculos(placa, modelo, ano, status, criado_em)
                VALUES (?, ?, ?, ?, ?)
            """, (placa, modelo, ano, status, criado))
        except sqlite3.IntegrityError:
            pass

def seed_os(cur, n=30):
    # pega ids existentes
    cur.execute("SELECT id FROM veiculos")
    veic_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT id FROM usuarios")
    user_ids = [r[0] for r in cur.fetchall()]
    if not veic_ids or not user_ids:
        return

    descricoes = [
        "Troca de óleo", "Revisão de freios", "Alinhamento e balanceamento",
        "Substituição de pneu", "Verificação elétrica", "Troca de filtros",
        "Reparo na suspensão", "Diagnóstico de ruídos", "Vazamento identificado"
    ]
    status_opts = ["aberta", "em_andamento", "fechada"]
    base = datetime.now() - timedelta(days=90)

    for _ in range(n):
        veiculo_id = random.choice(veic_ids)
        descricao = random.choice(descricoes)
        status = random.choices(status_opts, weights=[4,3,3], k=1)[0]
        aberto = base + timedelta(days=random.randint(0, 90))
        fechado = None
        resp_id = random.choice(user_ids)
        if status == "fechada":
            fechado = aberto + timedelta(days=random.randint(0, 10))
        cur.execute("""
            INSERT INTO ordens_servico(veiculo_id, descricao, status, aberto_em, fechado_em, responsavel_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (veiculo_id, descricao, status, aberto.isoformat(), fechado.isoformat() if fechado else None, resp_id))

def seed_manutencoes(cur, n=30):
    cur.execute("SELECT id FROM veiculos")
    veic_ids = [r[0] for r in cur.fetchall()]
    if not veic_ids:
        return
    tipos = ["preventiva", "corretiva"]
    base = datetime.now() - timedelta(days=180)

    for _ in range(n):
        veiculo_id = random.choice(veic_ids)
        tipo = random.choice(tipos)
        custo = round(random.uniform(150, 3500), 2)
        data = (base + timedelta(days=random.randint(0, 180))).date().isoformat()
        obs = random.choice([
            "Peças substituídas", "Ajustes finos", "Retorno em garantia",
            "Check-list completo", "Reparo emergencial", "Diagnóstico concluído"
        ])
        cur.execute("""
            INSERT INTO manutencoes(veiculo_id, tipo, custo, data, obs)
            VALUES (?, ?, ?, ?, ?)
        """, (veiculo_id, tipo, custo, data, obs))

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    create_tables(cur)
    seed_usuarios(cur, n=30)
    seed_veiculos(cur, n=30)
    seed_os(cur, n=30)
    seed_manutencoes(cur, n=30)
    conn.commit()

    # mostra contagens
    for tab in ["usuarios", "veiculos", "ordens_servico", "manutencoes"]:
        cur.execute(f"SELECT COUNT(1) FROM {tab}")
        print(f"{tab}: {cur.fetchone()[0]} registros")

    conn.close()
    print(f"\nOK! Banco populado em {DB_PATH}")

if __name__ == "__main__":
    main()
