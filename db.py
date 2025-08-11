# db.py
import sqlite3
from contextlib import contextmanager
from config import DB_PATH

@contextmanager
def get_conn():
    # Se usar threads no Streamlit, pode usar check_same_thread=False
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Cria as tabelas alvo, se não existirem."""
    with get_conn() as conn:
        c = conn.cursor()

        # Tabela de usuários (auth)
        c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            nome TEXT
        );
        """)

        # Veículos (cadastro_frotas)
        c.execute("""
        CREATE TABLE IF NOT EXISTS veiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_frota TEXT,
            classe_mecanica TEXT,
            classe_operacional TEXT,
            placa TEXT UNIQUE,
            modelo TEXT,
            marca TEXT,
            ano_fabricacao INTEGER,
            chassi TEXT,
            status TEXT DEFAULT 'ativo'
        );
        """)

        # Manutenções
        c.execute("""
        CREATE TABLE IF NOT EXISTS manutencoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            veiculo_id INTEGER NOT NULL,
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
            FOREIGN KEY (veiculo_id) REFERENCES veiculos(id) ON DELETE CASCADE
        );
        """)

        # Ordens de serviço
        c.execute("""
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            criada_em TEXT DEFAULT (datetime('now')),
            data_abertura TEXT,
            num_os TEXT,
            veiculo_id INTEGER,
            placa TEXT,
            descricao TEXT,            -- renomeando descritivo_servico -> descricao
            prioridade TEXT,
            sc TEXT,
            orcamento REAL,
            previsao_saida TEXT,
            data_liberacao TEXT,
            responsavel TEXT,
            status TEXT DEFAULT 'aberta',
            FOREIGN KEY (veiculo_id) REFERENCES veiculos(id) ON DELETE SET NULL
        );
        """)


def migrate_legacy():
    """Migra dados de tabelas antigas para o novo padrão (idempotente)."""
    with get_conn() as conn:
        cur = conn.cursor()

        # limpeza defensiva caso um run anterior tenha parado no meio
        cur.execute("DROP TABLE IF EXISTS ordens_servico_new;")
        cur.execute("DROP TABLE IF EXISTS manutencoes_new;")

        # --- 1) frota -> veiculos
        legacy_has_frota = cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='frota'"
        ).fetchone()
        has_veiculos = cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='veiculos'"
        ).fetchone()

        if legacy_has_frota and not has_veiculos:
            cur.execute("ALTER TABLE frota RENAME TO veiculos;")

        # --- 2) manutencao -> manutencoes (e id_frota -> veiculo_id)
        legacy_has_manutencao = cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='manutencao'"
        ).fetchone()
        has_manutencoes = cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='manutencoes'"
        ).fetchone()

        if legacy_has_manutencao and not has_manutencoes:
            cur.execute("ALTER TABLE manutencao RENAME TO manutencoes;")

        if cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='manutencoes'").fetchone():
            cols = [r["name"] for r in cur.execute("PRAGMA table_info(manutencoes);")]
            if "id_frota" in cols and "veiculo_id" not in cols:
                # recria para renomear coluna com segurança
                cur.execute("DROP TABLE IF EXISTS manutencoes_new;")
                cur.execute("""
                    CREATE TABLE manutencoes_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        veiculo_id INTEGER NOT NULL,
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
                        FOREIGN KEY (veiculo_id) REFERENCES veiculos(id) ON DELETE CASCADE
                    );
                """)
                cur.execute("""
                    INSERT INTO manutencoes_new
                    (id, veiculo_id, placa, data, mes, sc, tipo, cod_peca, desc_peca, qtd, vlr_unitario, fornecedor, nf, vlr_peca)
                    SELECT id, id_frota, placa, data, mes, sc, tipo, cod_peca, desc_peca, qtd, vlr_unitario, fornecedor, nf, vlr_peca
                    FROM manutencoes;
                """)
                cur.execute("DROP TABLE manutencoes;")
                cur.execute("ALTER TABLE manutencoes_new RENAME TO manutencoes;")

        # --- 3) ordens_servico: id_frota -> veiculo_id, descritivo_servico -> descricao,
        #     garantir colunas prioridade/status/criada_em
        has_os = cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ordens_servico'"
        ).fetchone()

        if has_os:
            cols = [r["name"] for r in cur.execute("PRAGMA table_info(ordens_servico);")]
            needs_rename = (
                ("id_frota" in cols) or
                ("descritivo_servico" in cols) or
                ("prioridade" not in cols) or
                ("status" not in cols) or
                ("criada_em" not in cols)
            )

            if needs_rename:
                cur.execute("DROP TABLE IF EXISTS ordens_servico_new;")
                cur.execute("""
                    CREATE TABLE ordens_servico_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        criada_em TEXT DEFAULT (datetime('now')),
                        data_abertura TEXT,
                        num_os TEXT,
                        veiculo_id INTEGER,
                        placa TEXT,
                        descricao TEXT,
                        prioridade TEXT,
                        sc TEXT,
                        orcamento REAL,
                        previsao_saida TEXT,
                        data_liberacao TEXT,
                        responsavel TEXT,
                        status TEXT DEFAULT 'aberta',
                        FOREIGN KEY (veiculo_id) REFERENCES veiculos(id) ON DELETE SET NULL
                    );
                """)

                # monta SELECT conforme colunas disponíveis
                col = lambda name: name if name in cols else "NULL"
                veiculo_id_expr = "veiculo_id" if "veiculo_id" in cols else ("id_frota" if "id_frota" in cols else "NULL")
                descricao_expr  = "descricao"  if "descricao"  in cols else ("descritivo_servico" if "descritivo_servico" in cols else "NULL")
                prioridade_expr = f"COALESCE({col('prioridade')}, 'média')"
                status_expr     = f"COALESCE({col('status')}, 'aberta')"
                criada_em_expr  = f"COALESCE({col('criada_em')}, datetime('now'))"

                cur.execute(f"""
                    INSERT INTO ordens_servico_new
                    (id, criada_em, data_abertura, num_os, veiculo_id, placa, descricao, prioridade, sc, orcamento, previsao_saida, data_liberacao, responsavel, status)
                    SELECT
                        {col('id')} AS id,
                        {criada_em_expr} AS criada_em,
                        {col('data_abertura')} AS data_abertura,
                        {col('num_os')} AS num_os,
                        {veiculo_id_expr} AS veiculo_id,
                        {col('placa')} AS placa,
                        {descricao_expr} AS descricao,
                        {prioridade_expr} AS prioridade,
                        {col('sc')} AS sc,
                        {col('orcamento')} AS orcamento,
                        {col('previsao_saida')} AS previsao_saida,
                        {col('data_liberacao')} AS data_liberacao,
                        {col('responsavel')} AS responsavel,
                        {status_expr} AS status
                    FROM ordens_servico;
                """)
                cur.execute("DROP TABLE ordens_servico;")
                cur.execute("ALTER TABLE ordens_servico_new RENAME TO ordens_servico;")

                # índice único opcional para num_os (evita duplicidades)
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_ordens_servico_num_os ON ordens_servico(num_os);")

        conn.commit()

def bootstrap():
    init_db()
    with get_conn() as conn:
        ver = conn.execute("PRAGMA user_version;").fetchone()[0]
        if ver < 1:
            migrate_legacy()
            conn.execute("PRAGMA user_version = 1;")
