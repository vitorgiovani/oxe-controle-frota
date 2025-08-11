import sqlite3
import hashlib
from datetime import datetime, timedelta
import random

# Função para gerar hash SHA-256 da senha
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# Conecta/cria o banco
conn = sqlite3.connect("data.db")
cur = conn.cursor()

# ===== Criação das tabelas =====
cur.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    nome TEXT NOT NULL,
    senha_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS veiculos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    placa TEXT NOT NULL,
    modelo TEXT NOT NULL,
    ano INTEGER,
    status TEXT NOT NULL DEFAULT 'ativo',
    criado_em TEXT NOT NULL,
    num_frota TEXT,
    marca TEXT,
    ano_fabricacao TEXT,
    chassi TEXT,
    classe_mecanica TEXT,
    classe_operacional TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS ordens_servico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    veiculo_id INTEGER,
    data_abertura TEXT,
    num_os TEXT,
    placa TEXT,
    descricao TEXT,
    prioridade TEXT,
    sc TEXT,
    orcamento REAL,
    previsao_saida TEXT,
    data_liberacao TEXT,
    responsavel TEXT,
    status TEXT,
    FOREIGN KEY (veiculo_id) REFERENCES veiculos (id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS manutencoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    veiculo_id INTEGER,
    placa TEXT,
    data TEXT,
    mes TEXT,
    sc TEXT,
    tipo TEXT,
    cod_peca TEXT,
    desc_peca TEXT,
    qtd INTEGER,
    vlr_unitario REAL,
    fornecedor TEXT,
    nf TEXT,
    vlr_peca REAL,
    FOREIGN KEY (veiculo_id) REFERENCES veiculos (id)
)
""")

# ===== Inserindo usuários =====
usuarios = [
    ("admin", "admin@teste.com", "Administrador", hash_password("admin123"), "admin", 1, datetime.now().isoformat()),
    ("user01", "user01@teste.com", "Usuário 01", hash_password("teste123"), "user", 1, datetime.now().isoformat()),
    ("user02", "user02@teste.com", "Usuário 02", hash_password("teste123"), "user", 1, datetime.now().isoformat())
]
cur.executemany("""
INSERT INTO usuarios (username, email, nome, senha_hash, role, active, created_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", usuarios)

# ===== Inserindo 30 veículos =====
veiculos = []
for i in range(1, 31):
    veiculos.append((
        f"ABC{i:03d}0",
        f"Modelo {i}",
        2010 + (i % 13),
        "ativo",
        datetime.now().isoformat(),
        f"FROTA-{i:03d}",
        f"Marca {i % 5 + 1}",
        str(2010 + (i % 13)),
        f"CHASSI{i:05d}",
        f"Classe Mecânica {i % 3 + 1}",
        f"Classe Operacional {i % 4 + 1}"
    ))
cur.executemany("""
INSERT INTO veiculos (
    placa, modelo, ano, status, criado_em, num_frota, marca, ano_fabricacao, chassi, classe_mecanica, classe_operacional
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", veiculos)

# ===== Inserindo 10 OS de exemplo =====
ordens = []
for i in range(1, 11):
    veiculo_id = random.randint(1, 30)
    data_abertura = datetime.now() - timedelta(days=random.randint(0, 60))
    ordens.append((
        veiculo_id,
        data_abertura.isoformat(),
        f"OS-{1000 + i}",
        f"ABC{veiculo_id:03d}0",
        f"Reparo geral no veículo {veiculo_id}",
        random.choice(["Alta", "Média", "Baixa"]),
        f"SC-{i:03d}",
        round(random.uniform(500, 5000), 2),
        (data_abertura + timedelta(days=5)).isoformat(),
        (data_abertura + timedelta(days=7)).isoformat(),
        random.choice(["João", "Maria", "Carlos"]),
        random.choice(["Aberta", "Em execução", "Fechada"])
    ))
    
cur.executemany("""
INSERT INTO ordens_servico (
    veiculo_id, data_abertura, num_os, placa, descricao, prioridade, sc, orcamento,
    previsao_saida, data_liberacao, responsavel, status
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", ordens)

# ===== Inserindo 15 manutenções de exemplo =====
manutencoes = []
for i in range(1, 16):
    veiculo_id = random.randint(1, 30)
    data_manut = datetime.now() - timedelta(days=random.randint(0, 180))
    manutencoes.append((
        veiculo_id,
        f"ABC{veiculo_id:03d}0",
        data_manut.isoformat(),
        data_manut.strftime("%m/%Y"),
        f"SC-MAN-{i:03d}",
        random.choice(["Preventiva", "Corretiva"]),
        f"PC-{i:04d}",
        f"Peça exemplo {i}",
        random.randint(1, 5),
        round(random.uniform(50, 500), 2),
        f"Fornecedor {random.randint(1, 5)}",
        f"NF-{10000 + i}",
        round(random.uniform(100, 2000), 2)
    ))
cur.executemany("""
INSERT INTO manutencoes (
    veiculo_id, placa, data, mes, sc, tipo, cod_peca, desc_peca, qtd, vlr_unitario,
    fornecedor, nf, vlr_peca
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", manutencoes)

conn.commit()
conn.close()

print("Banco criado e populado com sucesso!")
