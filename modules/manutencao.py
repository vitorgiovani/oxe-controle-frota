import os
import re
import sqlite3
from datetime import date, datetime
import pandas as pd
import streamlit as st

DB_PATH = "manutencao.db"      # troque para "frota.db" se quiser unificar
TABLE   = "manutencoes"        # usa/expande a mesma tabela

# =============== Helpers infra ===============
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

# =============== Schema / Migrations (ADD COLUMN) ===============
SCHEMA = {
    "id":                 "INTEGER PRIMARY KEY AUTOINCREMENT",
    "num_frota":          "TEXT",
    "placa":              "TEXT",
    "modelo":             "TEXT",
    "marca":              "TEXT",
    "ano_fabricacao":     "INTEGER",
    "chassi":             "TEXT",
    "data_manutencao":    "TEXT",
    "mes_ref":            "TEXT",   # yyyy-mm
    "sc":                 "TEXT",
    "tipo":               "TEXT",   # Peça/Serviço/Fluido/Pneu/Outro
    "codigo_peca":        "TEXT",
    "descricao_peca":     "TEXT",
    "qtd_peca":           "INTEGER",
    "vlr_unitario":       "REAL",
    "fornecedor":         "TEXT",
    "nf":                 "TEXT",
    "vlr_total":          "REAL"    # calculado: qtd_peca * vlr_unitario
}

def _ensure_table(conn: sqlite3.Connection):
    # cria se não existir
    cols_sql = ", ".join([f"{k} {v}" for k, v in SCHEMA.items()])
    conn.execute(f"CREATE TABLE IF NOT EXISTS {TABLE} ({cols_sql});")
    conn.commit()
    # adiciona colunas faltantes
    cur = conn.execute(f"PRAGMA table_info({TABLE});").fetchall()
    existing = {row[1] for row in cur}
    for col, coltype in SCHEMA.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE {TABLE} ADD COLUMN {col} {coltype};")
    conn.commit()

# =============== Validações / normalizações ===============
_PLACA_LEGADO   = re.compile(r"^[A-Z]{3}\d{4}$")
_PLACA_MERCOSUL = re.compile(r"^[A-Z]{3}\d[A-Z]\d{2}$")
_CHASSI_RE      = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")

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

def _coerce_ano(v) -> int | None:
    try: iv = int(v)
    except Exception: return None
    return iv if 1980 <= iv <= 2100 else None

def _fmt_br_col(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.strftime("%d/%m/%Y").fillna(df[c])
    return df

# =============== UI principal ===============
def show(com_expansor: bool = False):
    _inject_css()
    conn = get_conn()
    _ensure_table(conn)

    st.subheader("🛠️ Manutenções")

    aba_form, aba_lista = st.tabs(["➕ Nova Manutenção", "📋 Manutenções Registradas"])

    # ---------- ABA 1: Formulário ----------
    with aba_form:
        with st.form("form_manutencao"):
            col1, col2 = st.columns(2)
            with col1:
                num_frota = st.text_input("Nº da Frota", placeholder="Ex: FR-24").upper()
                placa = st.text_input("Placa", placeholder="Ex: RTX6C26").upper()
                modelo = st.text_input("Modelo", placeholder="Ex: AXOR 3344S 6X4")
                marca  = st.text_input("Marca", placeholder="Ex: MERCEDES").upper()
                ano    = st.number_input("Ano de Fabricação", min_value=1980, max_value=2100, step=1)
                chassi = st.text_input("Chassi (VIN)", placeholder="Ex: 9BM958471NB262510").upper().replace(" ", "")
                data   = st.date_input("Data", value=date.today())
            with col2:
                # mês pode ser calculado da Data; deixo editável se quiser corrigir
                mes_txt = st.text_input("Mês (formato mmm/aa)", value=(pd.to_datetime(date.today()).strftime("%b/%y")).lower())
                sc      = st.text_input("SC (Chamado)", placeholder="Ex: FVT-0625008").upper()
                tipo    = st.selectbox("Tipo", ["Peça", "Serviço", "Fluido", "Pneu", "Outro"], index=0)
                cod     = st.text_input("Código Peça", placeholder="Ex: 9020").upper()
                desc    = st.text_input("Descrição Peça / Serviço", placeholder="Ex: Catraca de Freio Mercedes AXOR")
                qtd     = st.number_input("Qtd Peça", min_value=0, step=1)
                vlr_uni = st.number_input("Vlr Unitário (R$)", min_value=0.0, format="%.2f")
                fornecedor = st.text_input("Fornecedor", placeholder="Ex: DIFERENCIAL").upper()
                nf      = st.text_input("NF.", placeholder="Ex: 252039").upper()

            submitted = st.form_submit_button("Salvar")

        if submitted:
            # normalização + tipagem
            ano_i = _coerce_ano(ano)
            erros = []
            if not placa and not num_frota:
                erros.append("Informe pelo menos **Placa** ou **Nº da Frota**.")
            if placa and not _valid_placa(placa):
                erros.append("**Placa** inválida. Formatos aceitos: AAA9999 (antigo) ou ABC1D23 (Mercosul).")
            if chassi and not _valid_chassi(chassi):
                erros.append("**Chassi** inválido (17 caracteres, sem I, O, Q).")
            if ano and ano_i is None:
                erros.append("**Ano de Fabricação** deve estar entre 1980 e 2100.")
            if qtd is not None and int(qtd) < 0:
                erros.append("**Qtd Peça** não pode ser negativa.")

            if erros:
                for e in erros: st.error(e)
            else:
                mes_ref = pd.to_datetime(data).strftime("%Y-%m")  # yyyy-mm (fácil pra filtrar)
                vlr_total = float(qtd) * float(vlr_uni) if (qtd is not None and vlr_uni is not None) else None

                payload = {
                    "num_frota": _norm(num_frota, upper=True),
                    "placa": placa,
                    "modelo": _norm(modelo),
                    "marca": _norm(marca, upper=True),
                    "ano_fabricacao": ano_i,
                    "chassi": chassi,
                    "data_manutencao": _iso(data),
                    "mes_ref": mes_ref,
                    "sc": _norm(sc, upper=True),
                    "tipo": tipo,
                    "codigo_peca": _norm(cod, upper=True),
                    "descricao_peca": _norm(desc),
                    "qtd_peca": int(qtd) if qtd is not None else None,
                    "vlr_unitario": float(vlr_uni) if vlr_uni is not None else None,
                    "fornecedor": _norm(fornecedor, upper=True),
                    "nf": _norm(nf, upper=True),
                    "vlr_total": vlr_total,
                }

                cols = ", ".join(payload.keys())
                qs   = ", ".join(["?"] * len(payload))
                sql  = f"INSERT INTO {TABLE} ({cols}) VALUES ({qs});"
                conn.execute(sql, list(payload.values()))
                conn.commit()
                st.success("Manutenção registrada com sucesso!")

    # ---------- ABA 2: Listagem + Filtros ----------
    with aba_lista:
        df = pd.read_sql(f"SELECT * FROM {TABLE}", conn)

        # filtros
        colf1, colf2, colf3, colf4 = st.columns(4)
        with colf1: f_num_frota = st.text_input("Filtro: Nº da Frota")
        with colf2: f_placa     = st.text_input("Filtro: Placa")
        with colf3: f_sc        = st.text_input("Filtro: SC")
        with colf4: f_tipo      = st.selectbox("Filtro: Tipo", ["", "Peça", "Serviço", "Fluido", "Pneu", "Outro"], index=0)
        colf5, colf6, colf7 = st.columns(3)
        with colf5: f_mes  = st.text_input("Filtro: Mês (mmm/aa, ex: jun/25)")
        with colf6: f_dt   = st.date_input("Filtro: Data (exata)", value=None)
        with colf7: f_forn = st.text_input("Filtro: Fornecedor")

        if not df.empty:
            if f_num_frota: df = df[df["num_frota"].astype(str).str.contains(f_num_frota, case=False, na=False)]
            if f_placa:     df = df[df["placa"].astype(str).str.contains(f_placa, case=False, na=False)]
            if f_sc:        df = df[df["sc"].astype(str).str.contains(f_sc, case=False, na=False)]
            if f_tipo:      df = df[df["tipo"] == f_tipo]
            if f_mes:
                # aceita "jun/25" etc. converte para yyyy-mm
                try:
                    ym = pd.to_datetime("01/"+f_mes, format="%d/%b/%y", errors="coerce")
                    if pd.notna(ym):
                        df = df[df["mes_ref"] == ym.strftime("%Y-%m")]
                except Exception:
                    pass
            if f_dt:        df = df[df["data_manutencao"] == _iso(f_dt)]
            if f_forn:      df = df[df["fornecedor"].astype(str).str.contains(f_forn, case=False, na=False)]

            if "id" in df.columns: df = df.drop(columns=["id"])

            # formatação de exibição
            df = _fmt_br_col(df, ["data_manutencao"])
            if "vlr_unitario" in df.columns:
                df["vlr_unitario"] = pd.to_numeric(df["vlr_unitario"], errors="coerce").fillna(0)
                df["vlr_unitario"] = df["vlr_unitario"].map(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
            if "vlr_total" in df.columns:
                df["vlr_total"] = pd.to_numeric(df["vlr_total"], errors="coerce").fillna(0)
                df["vlr_total"] = df["vlr_total"].map(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

            friendly = {
                "num_frota":"Nº da Frota", "placa":"Placa", "modelo":"Modelo", "marca":"Marca",
                "ano_fabricacao":"Ano de Fabricação", "chassi":"Chassi (VIN)",
                "data_manutencao":"Data", "mes_ref":"Mês (aaaa-mm)", "sc":"SC",
                "tipo":"Tipo", "codigo_peca":"Código Peça", "descricao_peca":"Descrição Peça",
                "qtd_peca":"Qtd Peça", "vlr_unitario":"Vlr Unitário", "fornecedor":"Fornecedor",
                "nf":"NF.", "vlr_total":"Vlr Peça",
            }
            df = df.rename(columns={k:v for k,v in friendly.items() if k in df.columns})

            # melhora coluna de mês para mmm/aa
            if "Mês (aaaa-mm)" in df.columns:
                tmp = pd.to_datetime(df["Mês (aaaa-mm)"]+"-01", errors="coerce")
                df["Mês"] = tmp.dt.strftime("%b/%y").str.lower()
                df = df.drop(columns=["Mês (aaaa-mm)"])

            # ordenação e ordem de colunas
            if "Data" in df.columns:
                df = df.sort_values("Data", ascending=False, key=lambda s: pd.to_datetime(s, dayfirst=True, errors="coerce"))

            order = ["Nº da Frota","Placa","Modelo","Marca","Ano de Fabricação","Chassi (VIN)",
                     "Data","Mês","SC","Tipo","Código Peça","Descrição Peça","Qtd Peça","Vlr Unitário","Fornecedor","NF.","Vlr Peça"]
            exist = [c for c in order if c in df.columns]; other = [c for c in df.columns if c not in exist]
            df = df[exist + other]

            # ------- Estilo (pílula e chip) -------
            def pill_placa(val: str):
                if isinstance(val, str) and val.strip():
                    return "background-color:#d9f2d9; color:#0f5132; border:1px solid #99d6a6; border-radius:999px; padding:2px 8px; font-weight:700; text-align:center;"
                return ""
            def chip_tipo(val: str):
                if not isinstance(val, str): return ""
                v = val.lower()
                colors = {
                    "peça":     ("#1565c0","#fff"),
                    "serviço":  ("#6a1b9a","#fff"),
                    "servico":  ("#6a1b9a","#fff"),
                    "fluido":   ("#00897b","#fff"),
                    "pneu":     ("#8d6e63","#fff"),
                    "outro":    ("#546e7a","#fff"),
                }
                bg, fg = colors.get(v, ("#546e7a","#fff"))
                return f"background-color:{bg}; color:{fg}; font-weight:700; text-align:center;"

            styled = df.style
            if "Placa" in df.columns: styled = styled.applymap(pill_placa, subset=["Placa"])
            if "Tipo"  in df.columns: styled = styled.applymap(chip_tipo, subset=["Tipo"])

            # Export CSV
            csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Exportar CSV (manutenções filtradas)", data=csv_bytes,
                               file_name="manutencoes_filtradas.csv", mime="text/csv", use_container_width=True)

            container = st.expander("📋 Ver Manutenções Registradas") if com_expansor else st.container()
            with container:
                st.dataframe(styled, use_container_width=True)
        else:
            st.info("Nenhuma manutenção encontrada.")
