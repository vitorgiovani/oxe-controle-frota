# modules/abertura_os.py
import pandas as pd
import streamlit as st
from datetime import date, datetime

from db import get_conn  # ✅ usa data.db central
TABLE = "ordens_servico"

# --------- CSS ----------
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

# --------- Utils ----------
def _iso(d):
    if isinstance(d, date): return d.strftime("%Y-%m-%d")
    if isinstance(d, datetime): return d.date().strftime("%Y-%m-%d")
    return str(d) if d else None

def _load_veiculos_opts():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, COALESCE(num_frota,'--') AS nf, COALESCE(placa,'--') AS placa,
                   COALESCE(marca,'') AS marca, COALESCE(modelo,'') AS modelo
            FROM veiculos
            ORDER BY COALESCE(num_frota, placa)
        """).fetchall()
    opts = []
    for r in rows:
        label = f"{r['nf']} · {r['placa']} · {r['marca']} {r['modelo']}".strip()
        opts.append({"id": r["id"], "placa": r["placa"], "label": label})
    return opts

def _find_os_id_by_num(num_os: str) -> int | None:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM ordens_servico WHERE num_os=?", (num_os,)).fetchone()
        return row["id"] if row else None

# --------- UI ----------
def show(com_expansor: bool = False):
    _inject_css()
    st.subheader("🧾 Abertura de OS")

    aba_form, aba_lista = st.tabs(["➕ Nova/Editar OS", "📋 OS Cadastradas"])

    # ===== Aba 1: Cadastro/Upsert =====
    with aba_form:
        veiculos = _load_veiculos_opts()
        if not veiculos:
            st.warning("Cadastre veículos primeiro na aba **Frota**.")
        else:
            idx = st.selectbox("Veículo", options=range(len(veiculos)),
                               format_func=lambda i: veiculos[i]["label"])

            with st.form("form_os"):
                col1, col2 = st.columns(2)
                with col1:
                    data_abertura = st.date_input("Data de Abertura", value=date.today())
                    num_os        = st.text_input("Nº da OS", placeholder="Ex: OS-2025-001").upper().strip()
                    prioridade    = st.selectbox("Prioridade", ["baixa","média","alta","crítica"], index=1)
                    sc            = st.text_input("SC (Chamado)", placeholder="Ex: FVT06250001").upper().strip()
                    orcamento     = st.number_input("Orçamento (R$)", min_value=0.0, format="%.2f")
                with col2:
                    descricao     = st.text_area("Descrição do Serviço")
                    previsao_saida= st.date_input("Previsão de Saída", value=None)
                    data_lib      = st.date_input("Data de Liberação", value=None)
                    responsavel   = st.text_input("Responsável").strip()
                    status        = st.selectbox("Status", ["aberta","em execução","fechada"], index=0)

                submitted = st.form_submit_button("Salvar")

            if submitted:
                v = veiculos[idx]
                veiculo_id = v["id"]
                placa      = v["placa"]

                payload_ins = {
                    "data_abertura": _iso(data_abertura),
                    "num_os": num_os,
                    "veiculo_id": veiculo_id,
                    "placa": placa,
                    "descricao": descricao.strip(),
                    "prioridade": prioridade.strip().lower(),
                    "sc": sc,
                    "orcamento": float(orcamento) if orcamento is not None else None,
                    "previsao_saida": _iso(previsao_saida) if previsao_saida else None,
                    "data_liberacao": _iso(data_lib) if data_lib else None,
                    "responsavel": responsavel,
                    "status": status.strip().lower(),
                }

                erros = []
                if not num_os:
                    erros.append("Informe o **Nº da OS**.")
                if not descricao.strip():
                    erros.append("Informe a **Descrição do Serviço**.")
                if erros:
                    for e in erros: st.error(e)
                else:
                    try:
                        os_id = _find_os_id_by_num(num_os)
                        with get_conn() as conn:
                            if os_id:  # UPDATE
                                sets = ", ".join(f"{k}=?" for k in payload_ins.keys())
                                params = list(payload_ins.values()) + [num_os]
                                conn.execute(f"UPDATE {TABLE} SET {sets} WHERE num_os=?", params)
                            else:      # INSERT
                                cols = ", ".join(payload_ins.keys())
                                qs   = ", ".join(["?"] * len(payload_ins))
                                conn.execute(f"INSERT INTO {TABLE} ({cols}) VALUES ({qs})", list(payload_ins.values()))
                        st.success("Ordem de Serviço salva com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao salvar OS: {e}")

    # ===== Aba 2: Listagem + Filtros =====
    with aba_lista:
        try:
            with get_conn() as conn:
                df = pd.read_sql("""
                    SELECT
                        os.id,
                        os.data_abertura,
                        os.num_os,
                        v.num_frota,
                        os.placa,
                        v.modelo,
                        v.marca,
                        v.ano_fabricacao,
                        v.chassi,
                        os.descricao,
                        os.prioridade,
                        os.sc,
                        os.orcamento,
                        os.previsao_saida,
                        os.data_liberacao,
                        os.responsavel,
                        os.status
                    FROM ordens_servico os
                    LEFT JOIN veiculos v ON v.id = os.veiculo_id
                    ORDER BY COALESCE(os.data_abertura,'' ) DESC, os.id DESC
                """, conn)
        except Exception as e:
            st.error(f"Erro ao carregar OS: {e}")
            df = pd.DataFrame()

        colf1, colf2, colf3, colf4 = st.columns(4)
        with colf1: f_num_frota = st.text_input("Filtro: Nº da Frota")
        with colf2: f_num_os    = st.text_input("Filtro: Nº da OS")
        with colf3: f_placa     = st.text_input("Filtro: Placa")
        with colf4: f_data      = st.date_input("Filtro: Data de Abertura (exata)", value=None)

        colf5, colf6 = st.columns(2)
        with colf5: f_status    = st.selectbox("Filtro: Status", ["","aberta","em execução","fechada"], index=0)
        with colf6: f_prior     = st.selectbox("Filtro: Prioridade", ["","baixa","média","alta","crítica"], index=0)

        if not df.empty:
            if f_num_frota: df = df[df["num_frota"].astype(str).str.contains(f_num_frota, case=False, na=False)]
            if f_num_os:    df = df[df["num_os"].astype(str).str.contains(f_num_os, case=False, na=False)]
            if f_placa:     df = df[df["placa"].astype(str).str.contains(f_placa, case=False, na=False)]
            if f_data:      df = df[df["data_abertura"] == _iso(f_data)]
            if f_status:    df = df[df["status"].astype(str).str.lower() == f_status]
            if f_prior:     df = df[df["prioridade"].astype(str).str.lower() == f_prior]

            # headers amigáveis
            friendly = {
                "data_abertura":"Data Abertura","num_os":"Nº da OS","num_frota":"Nº da Frota","placa":"Placa",
                "modelo":"Modelo","marca":"Marca","ano_fabricacao":"Ano de Fabricação","chassi":"Chassi (VIN)",
                "descricao":"Descrição Serviço","prioridade":"Prioridade","sc":"SC","orcamento":"Orçamento R$",
                "previsao_saida":"Previsão Saída","data_liberacao":"Data Liberação","responsavel":"Responsável",
                "status":"Status",
            }
            df = df.rename(columns={k:v for k,v in friendly.items() if k in df.columns})

            # formatações
            def _fmt_br(s): return pd.to_datetime(s, errors="coerce").dt.strftime("%d/%m/%Y").fillna(s)
            for c in ["Data Abertura","Previsão Saída","Data Liberação"]:
                if c in df.columns: df[c] = _fmt_br(df[c])

            if "Orçamento R$" in df.columns:
                df["Orçamento R$"] = pd.to_numeric(df["Orçamento R$"], errors="coerce").fillna(0)
                df["Orçamento R$"] = df["Orçamento R$"].map(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

            # ordenação/colunas
            if "Data Abertura" in df.columns:
                df = df.sort_values("Data Abertura", ascending=False, key=lambda s: pd.to_datetime(s, dayfirst=True, errors="coerce"))

            order = ["Data Abertura","Nº da OS","Nº da Frota","Placa","Modelo","Marca","Ano de Fabricação","Chassi (VIN)",
                     "Descrição Serviço","Prioridade","SC","Orçamento R$","Previsão Saída","Data Liberação","Responsável","Status"]
            exist = [c for c in order if c in df.columns]; other = [c for c in df.columns if c not in exist]
            df = df[exist + other]

            # chips
            def chip_status(val:str):
                if not isinstance(val,str): return ""
                v = val.strip().lower()
                if v=="aberta": return "background-color:#2e7d32; color:white; font-weight:700; text-align:center;"
                if v in ("em execução","em execucao"): return "background-color:#f9a825; color:black; font-weight:700; text-align:center;"
                if v=="fechada": return "background-color:#546e7a; color:white; font-weight:700; text-align:center;"
                return ""
            def chip_prior(val:str):
                if not isinstance(val,str): return ""
                v = val.strip().lower()
                colors = {"baixa":"#1565c0", "média":"#6a1b9a", "media":"#6a1b9a", "alta":"#ef6c00", "crítica":"#b71c1c", "critica":"#b71c1c"}
                bg = colors.get(v, "#546e7a"); fg = "#fff" if v not in ("baixa","alta") else "#fff"
                return f"background-color:{bg}; color:{fg}; font-weight:700; text-align:center;"

            styled = df.style
            if "Status" in df.columns:     styled = styled.applymap(chip_status, subset=["Status"])
            if "Prioridade" in df.columns: styled = styled.applymap(chip_prior, subset=["Prioridade"])

            csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Exportar CSV (OS filtradas)", data=csv_bytes,
                               file_name="os_filtradas.csv", mime="text/csv", use_container_width=True)

            container = st.expander("📋 Visualizar OS") if com_expansor else st.container()
            with container:
                st.dataframe(styled, use_container_width=True)
        else:
            st.info("Nenhuma OS encontrada.")
