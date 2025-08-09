import sqlite3

def get_conn(path="frota.db"):
    return sqlite3.connect(path, check_same_thread=False)

def init_db(conn):
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS frota (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        num_frota TEXT,
        classe_mecanica TEXT,
        classe_operacional TEXT,
        placa TEXT UNIQUE,
        modelo TEXT,
        marca TEXT,
        ano_fabricacao INTEGER,
        chassi TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_abertura TEXT,
        num_os TEXT,
        id_frota INTEGER,
        placa TEXT,
        descritivo_servico TEXT,
        sc TEXT,
        orcamento REAL,
        previsao_saida TEXT,
        data_liberacao TEXT,
        responsavel TEXT,
        FOREIGN KEY(id_frota) REFERENCES frota(id)
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS manutencao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_frota INTEGER,
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
        FOREIGN KEY(id_frota) REFERENCES frota(id)
    )
    """)
    conn.commit()
