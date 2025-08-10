import os
import re
import sqlite3
import pandas as pd
import streamlit as st
from datetime import date, datetime

DB_PATH = "ordens_servico.db"
TABLE   = "abertura_os"

# --------- Helpers infra ----------
@st.cache_resource
def get_conn(path=DB_PATH):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def _iso(d):
    if isinstance(d, date): return d.strftime("%Y-%m-%d")
    if isinstance(d, datetime): return d.date().strftime("%Y-%m-%d")
    return str(d) if d else None

def _inject_css():
    st.markdown("""
    <style>
      .stApp { background-color: #004d00 !important; color: #ffffff !important; }
      header[data-testid="stHeader"] { background-color: #004d00 !important; }
      .stTabs [data-baseweb="tab"] {
        background-color: #006400 !important; color: #ffffff !important;
        font-weight: 700; font-size: 16px;
      }
      .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"],
      .stDateInput input, textarea {
        background-color: #ffffff !important; color: #000000 !important;
      }
      .stButton>button {
        background-color: #ffffff !important; color: #004d00 !important; font-weight: 700;
        border: 0; border-radius: 8px;
      }
      .stDataFrame thead tr th { background-color: #d9f2d9 !important; color: #000000 !important; }
      .stDataFrame tbody tr td { background-color: #eaf8ea !important; color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

def _ensure_table(conn: sqlite3.Connection):
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_abertura  TEXT,
            numero_os      TEXT UNIQUE,
            num_frota      TEXT,
            placa          TEXT,
            modelo         TEXT,
            marca          TEXT,
            ano            INTEGER CHECK(ano IS NULL OR (ano >= 1980 AND ano <= 2100)),
            chassi         TEXT,
            descritivo_servico TEXT,
            sc             TEXT,
            orcamento      REAL,
            previsao_saida TEXT,
            data_liberacao TEXT,
            responsavel    TEXT,
            status         TEXT
        );
    """)
    conn.commit()

# --------- Validações ----------
_PLACA_LEGADO   = re.compile(r"^[A-Z]{3}\d{4}$")            # AAA1234
_PLACA_MERCOSUL = re.compile(r"^[A-Z]{3}\d[A-Z]\d{2}$")     # ABC1D23
_CHASSI_RE      = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")      # 17 chars, sem I,O,Q
_OS_RE          = re.compile(r"^[A-Z0-9\-_]{5,20}$")        # ex: FVT0625001, OS-2025-001, etc.

def _norm(s: str, upper=False):
    if s is None: return ""
    s = str(s).strip()
    return s.upper() if upper else s

def _valid_placa(p: str) -> bool:
    if not p or len(p) != 7: return False
    p = p.upper()
    return bool(_PLACA_LEGADO.match(p) or _PLACA_MERCOSUL.match(p))

def _valid_chassi(c: str) -> bool:
    if not c: return True
    return bool(_CHASSI_RE.match(c.replace(" ", "").upper()))

def _valid_os(osn: str) -> bool:
    if not osn: return False
    return bool(_OS_RE.match(osn.upper()))

# --------- UI ----------
def show(com_expansor: bool = False):
    _inject_css()
    conn = get_conn()
    _ensure_table(conn)

    st.subheader("🧾 Abertura de OS")

    aba_form, aba_lista = st.tabs(["➕ Nova OS", "📋 OS Abertas"])

    # ===== Aba 1: Cadastro =====
    with aba_form:
        with st.form("form_os"):
            col1, col2 = st.columns(2)
            with col1:
                data_abertura = st.date_input("Data de Abertura", value=date.today())
                numero_os     = st.text_input("Nº da OS", placeholder="Ex: FVT0625001").upper()
                num_frota     = st.text_input("Nº da Frota", placeholder="Ex: FR-06").upper()
                placa         = st.text_input("Placa", placeholder="Ex: RNE8A74").upper()
                modelo        = st.text_input("Modelo")
            with col2:
                marca   = st.text_input("Marca").upper()
                ano     = st.number_input("Ano de Fabricação", min_value=1980, max_value=2100, step=1)
                chassi  = st.text_input("Chassi (VIN)", placeholder="Ex: 9BVRG40D5ME899353").upper().replace(" ", "")
                descritivo = st.text_area("Descritivo do Serviço")
                sc      = st.text_input("SC (Chamado)", placeholder="Ex: FVT06250001").upper()
                orcamento = st.number_input("Orçamento (R$)", min_value=0.0, format="%.2f")

            col3, col4 = st.columns(2)
            with col3:
                previsao_saida = st.date_input("Previsão de Saída", value=None)
            with col4:
                data_liberacao = st.date_input("Data de Liberação", value=None)

            responsavel = st.text_input("Responsável")
            status_opt  = st.selectbox("Status", ["Aberta", "Em execução", "Fechada"], index=0)

            submitted = st.form_submit_button("Salvar")

        if submitted:
            # Tipagem/normalização
            payload = {
                "data_abertura": _iso(data_abertura),
                "numero_os": _norm(numero_os, upper=True),
                "num_frota": _norm(num_frota, upper=True),
                "placa": _norm(placa, upper=True),
                "modelo": _norm(modelo),
                "marca": _norm(marca, upper=True),
                "ano": int(ano) if ano else None,
                "chassi": _norm(chassi, upper=True).replace(" ", ""),
                "descritivo_servico": _norm(descritivo),
                "sc": _norm(sc, upper=True),
                "orcamento": float(orcamento) if orcamento is not None else None,
                "previsao_saida": _iso(previsao_saida) if previsao_saida else None,
                "data_liberacao": _iso(data_liberacao) if data_liberacao else None,
                "responsavel": _norm(responsavel),
                "status": status_opt,
            }

            # Regras de validação
            erros = []
            if not _valid_os(payload["numero_os"]):
                erros.append("**Nº da OS** inválido (use apenas letras, números, hífen ou sublinhado; 5–20 chars).")
            if not payload["placa"] and not payload["num_frota"]:
                erros.append("Informe pelo menos **Placa** ou **Nº da Frota**.")
            if payload["placa"] and not _valid_placa(payload["placa"]):
                erros.append("**Placa** inválida. Formatos aceitos: AAA9999 (antigo) ou ABC1D23 (Mercosul).")
            if payload["chassi"] and not _valid_chassi(payload["chassi"]):
                erros.append("**Chassi** inválido (17 caracteres, sem I, O, Q).")
            if payload["ano"] and not (1980 <= payload["ano"] <= 2100):
                erros.append("**Ano de Fabricação** deve estar entre 1980 e 2100.")

            if erros:
                for e in erros: st.error(e)
            else:
                # UPSERT pela chave numero_os
                cols = ", ".join(payload.keys())
                qs   = ", ".join(["?"] * len(payload))
                set_clause = ", ".join([f"{k}=excluded.{k}" for k in payload.keys() if k != "numero_os"])
                sql = f"""
                    INSERT INTO {TABLE} ({cols}) VALUES ({qs})
                    ON CONFLICT(numero_os) DO UPDATE SET {set_clause};
                """
                conn.execute(sql, list(payload.values()))
                conn.commit()
                st.success("Ordem de Serviço salva/atualizada com sucesso!")

    # ===== Aba 2: Listagem + Filtros =====
    with aba_lista:
        df = pd.read_sql(f"SELECT * FROM {TABLE}", conn)

        colf1, colf2, colf3, colf4 = st.columns(4)
        with colf1: f_num_frota = st.text_input("Filtro: Nº da Frota")
        with colf2: f_num_os    = st.text_input("Filtro: Nº da OS")
        with colf3: f_placa     = st.text_input("Filtro: Placa")
        with colf4: f_data      = st.date_input("Filtro: Data de Abertura (exata)", value=None)

        if not df.empty:
            if f_num_frota: df = df[df["num_frota"].astype(str).str.contains(f_num_frota, case=False, na=False)]
            if f_num_os:    df = df[df["numero_os"].astype(str).str.contains(f_num_os, case=False, na=False)]
            if f_placa:     df = df[df["placa"].astype(str).str.contains(f_placa, case=False, na=False)]
            if f_data:      df = df[df["data_abertura"] == _iso(f_data)]

            if "id" in df.columns: df = df.drop(columns=["id"])
            if "data_abertura" in df.columns: df = df.sort_values("data_abertura", ascending=False)

            # formatações de exibição
            def _fmt_br(s): return pd.to_datetime(s, errors="coerce").dt.strftime("%d/%m/%Y").fillna(s)
            for c in ["data_abertura","previsao_saida","data_liberacao"]:
                if c in df.columns: df[c] = _fmt_br(df[c])
            if "orcamento" in df.columns:
                df["orcamento"] = pd.to_numeric(df["orcamento"], errors="coerce").fillna(0)
                df["orcamento"] = df["orcamento"].map(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

            # headers amigáveis
            friendly = {
                "data_abertura":"Data Abertura","numero_os":"Nº da OS","num_frota":"Nº da Frota","placa":"Placa",
                "modelo":"Modelo","marca":"Marca","ano":"Ano de Fabricação","chassi":"Chassi (VIN)",
                "descritivo_servico":"Descritivo Serviço","sc":"SC","orcamento":"Orçamento R$",
                "previsao_saida":"Previsão Saída","data_liberacao":"Data Liberação","responsavel":"Responsável",
                "status":"Status",
            }
            df = df.rename(columns={k:v for k,v in friendly.items() if k in df.columns})

            # ordem de colunas
            order = ["Data Abertura","Nº da OS","Nº da Frota","Placa","Modelo","Marca","Ano de Fabricação","Chassi (VIN)",
                     "Descritivo Serviço","SC","Orçamento R$","Previsão Saída","Data Liberação","Responsável","Status"]
            exist = [c for c in order if c in df.columns]; other = [c for c in df.columns if c not in exist]
            df = df[exist + other]

            # chips de Status
            def chip_status(val:str):
                if isinstance(val,str):
                    v = val.strip().lower()
                    if v=="aberta": return "background-color:#2e7d32; color:white; font-weight:700; text-align:center;"
                    if v in ("em execução","em execucao"): return "background-color:#f9a825; color:black; font-weight:700; text-align:center;"
                    if v=="fechada": return "background-color:#546e7a; color:white; font-weight:700; text-align:center;"
                return ""
            styled = df.style.applymap(chip_status, subset=["Status"]) if "Status" in df.columns else df.style

            # exportar CSV (após filtros e renome)
            csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Exportar CSV (OS filtradas)", data=csv_bytes, file_name="os_filtradas.csv",
                               mime="text/csv", use_container_width=True)

            container = st.expander("📋 Visualizar OS Abertas") if com_expansor else st.container()
            with container: st.dataframe(styled, use_container_width=True)
        else:
            st.info("Nenhuma OS encontrada.")
