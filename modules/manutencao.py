# modules/manutencao.py
import pandas as pd
import streamlit as st
from datetime import date, datetime

from db import get_conn  # ✅ usa o data.db central
TABLE = "manutencoes"

# =============== CSS ===============
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

# =============== Utils ===============
def _iso(d):
    if isinstance(d, date): return d.strftime("%Y-%m-%d")
    if isinstance(d, datetime): return d.date().strftime("%Y-%m-%d")
    return str(d) if d else None

def _money_fmt(v: float | int | None) -> str:
    try:
        v = float(v)
    except Exception:
        return ""
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X",".")

def _carregar_veiculos():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, num_frota, placa, modelo, marca, chassi
            FROM veiculos
            ORDER BY COALESCE(num_frota, placa)
        """).fetchall()
    # monta label amigável
    opts = []
    for r in rows:
        label = f"{r['num_frota'] or '--'} · {r['placa'] or '--'} · {r['marca'] or ''} {r['modelo'] or ''}".strip()
        opts.append({"id": r["id"], "placa": r["placa"], "label": label})
    return opts

# =============== UI principal ===============
def show(com_expansor: bool = False):
    _inject_css()
    st.subheader("🛠️ Manutenções")

    aba_form, aba_lista = st.tabs(["➕ Nova Manutenção", "📋 Manutenções Registradas"])

    # ---------- ABA 1: Formulário ----------
    with aba_form:
        veiculos = _carregar_veiculos()
        if not veiculos:
            st.warning("Cadastre veículos primeiro na aba **Frota** para lançar manutenções.")
        else:
            labels = [v["label"] for v in veiculos]
            idx = st.selectbox("Veículo", options=range(len(labels)), format_func=lambda i: labels[i])

            with st.form("form_manutencao"):
                col1, col2 = st.columns(2)
                with col1:
                    data   = st.date_input("Data", value=date.today())
                    tipo   = st.selectbox("Tipo", ["Peça", "Serviço", "Fluido", "Pneu", "Outro"], index=0)
                    sc     = st.text_input("SC (Chamado)", placeholder="Ex: FVT-0625008").upper()
                    cod    = st.text_input("Código Peça", placeholder="Ex: 9020").upper()
                with col2:
                    desc   = st.text_input("Descrição Peça / Serviço", placeholder="Ex: Catraca de Freio")
                    qtd    = st.number_input("Qtd", min_value=0, step=1)
                    vlr_uni= st.number_input("Vlr Unitário (R$)", min_value=0.0, format="%.2f")
                    fornecedor = st.text_input("Fornecedor", placeholder="Ex: DIFERENCIAL").upper()
                    nf     = st.text_input("NF.", placeholder="Ex: 252039").upper()

                submitted = st.form_submit_button("Salvar")

            if submitted:
                v = veiculos[idx]
                veiculo_id = v["id"]
                placa      = v["placa"]

                mes = pd.to_datetime(data).strftime("%Y-%m")
                vlr_peca = (float(qtd) * float(vlr_uni)) if (qtd is not None and vlr_uni is not None) else None

                payload = {
                    "veiculo_id": veiculo_id,
                    "placa": placa,
                    "data": _iso(data),
                    "mes": mes,
                    "sc": sc,
                    "tipo": tipo,
                    "cod_peca": cod,
                    "desc_peca": desc,
                    "qtd": int(qtd) if qtd is not None else None,
                    "vlr_unitario": float(vlr_uni) if vlr_uni is not None else None,
                    "fornecedor": fornecedor,
                    "nf": nf,
                    "vlr_peca": vlr_peca,
                }

                cols = ", ".join(payload.keys())
                qs   = ", ".join(["?"] * len(payload))
                sql  = f"INSERT INTO {TABLE} ({cols}) VALUES ({qs});"

                try:
                    with get_conn() as conn:
                        conn.execute(sql, list(payload.values()))
                    st.success("Manutenção registrada com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

    # ---------- ABA 2: Listagem + Filtros ----------
    with aba_lista:
        try:
            with get_conn() as conn:
                df = pd.read_sql("""
                    SELECT
                        m.id,
                        m.veiculo_id,
                        v.num_frota,
                        m.placa,
                        v.modelo,
                        v.marca,
                        v.ano_fabricacao,
                        v.chassi,
                        m.data,
                        m.mes,
                        m.sc,
                        m.tipo,
                        m.cod_peca,
                        m.desc_peca,
                        m.qtd,
                        m.vlr_unitario,
                        m.fornecedor,
                        m.nf,
                        m.vlr_peca
                    FROM manutencoes m
                    LEFT JOIN veiculos v ON v.id = m.veiculo_id
                    ORDER BY COALESCE(m.data, '') DESC, m.id DESC
                """, conn)
        except Exception as e:
            st.error(f"Erro ao carregar manutenções: {e}")
            df = pd.DataFrame()

        colf1, colf2, colf3, colf4 = st.columns(4)
        with colf1: f_num_frota = st.text_input("Filtro: Nº da Frota")
        with colf2: f_placa     = st.text_input("Filtro: Placa")
        with colf3: f_sc        = st.text_input("Filtro: SC")
        with colf4: f_tipo      = st.selectbox("Filtro: Tipo", ["", "Peça", "Serviço", "Fluido", "Pneu", "Outro"], index=0)

        colf5, colf6, colf7 = st.columns(3)
        with colf5: f_mes_txt = st.text_input("Filtro: Mês (mmm/aa, ex: jun/25)")
        with colf6: f_dt      = st.date_input("Filtro: Data (exata)", value=None)
        with colf7: f_forn    = st.text_input("Filtro: Fornecedor")

        if not df.empty:
            if f_num_frota: df = df[df["num_frota"].astype(str).str.contains(f_num_frota, case=False, na=False)]
            if f_placa:     df = df[df["placa"].astype(str).str.contains(f_placa, case=False, na=False)]
            if f_sc:        df = df[df["sc"].astype(str).str.contains(f_sc, case=False, na=False)]
            if f_tipo:      df = df[df["tipo"] == f_tipo]
            if f_mes_txt:
                try:
                    ym = pd.to_datetime("01/"+f_mes_txt, format="%d/%b/%y", errors="coerce")
                    if pd.notna(ym):
                        df = df[df["mes"] == ym.strftime("%Y-%m")]
                except Exception:
                    pass
            if f_dt is not None:
                df = df[df["data"] == _iso(f_dt)]
            if f_forn:      df = df[df["fornecedor"].astype(str).str.contains(f_forn, case=False, na=False)]

            # formatação
            friendly = {
                "num_frota":"Nº da Frota", "placa":"Placa", "modelo":"Modelo", "marca":"Marca",
                "ano_fabricacao":"Ano de Fabricação", "chassi":"Chassi (VIN)",
                "data":"Data", "mes":"Mês (aaaa-mm)", "sc":"SC",
                "tipo":"Tipo", "cod_peca":"Código Peça", "desc_peca":"Descrição",
                "qtd":"Qtd", "vlr_unitario":"Vlr Unitário", "fornecedor":"Fornecedor",
                "nf":"NF.", "vlr_peca":"Vlr Total",
            }
            df = df.rename(columns={k:v for k,v in friendly.items() if k in df.columns})

            # Data → dd/mm/aaaa
            if "Data" in df.columns:
                df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.strftime("%d/%m/%Y").fillna(df["Data"])

            # Mês legível
            if "Mês (aaaa-mm)" in df.columns:
                tmp = pd.to_datetime(df["Mês (aaaa-mm)"]+"-01", errors="coerce")
                df["Mês"] = tmp.dt.strftime("%b/%y").str.lower()
                df = df.drop(columns=["Mês (aaaa-mm)"])

            # Moedas
            if "Vlr Unitário" in df.columns:
                df["Vlr Unitário"] = pd.to_numeric(df["Vlr Unitário"], errors="coerce").map(_money_fmt)
            if "Vlr Total" in df.columns:
                df["Vlr Total"] = pd.to_numeric(df["Vlr Total"], errors="coerce").map(_money_fmt)

            order = ["Nº da Frota","Placa","Modelo","Marca","Ano de Fabricação","Chassi (VIN)",
                     "Data","Mês","SC","Tipo","Código Peça","Descrição","Qtd","Vlr Unitário","Fornecedor","NF.","Vlr Total"]
            exist = [c for c in order if c in df.columns]
            other = [c for c in df.columns if c not in exist]
            df = df[exist + other]

            # Estilos
            def pill_placa(val: str):
                if isinstance(val, str) and val.strip():
                    return "background-color:#d9f2d9; color:#0f5132; border:1px solid #99d6a6; border-radius:999px; padding:2px 8px; font-weight:700; text-align:center;"
                return ""
            def chip_tipo(val: str):
                if not isinstance(val, str): return ""
                v = val.lower()
                colors = {
                    "peça":("#1565c0","#fff"), "serviço":("#6a1b9a","#fff"),
                    "servico":("#6a1b9a","#fff"), "fluido":("#00897b","#fff"),
                    "pneu":("#8d6e63","#fff"), "outro":("#546e7a","#fff"),
                }
                bg, fg = colors.get(v, ("#546e7a","#fff"))
                return f"background-color:{bg}; color:{fg}; font-weight:700; text-align:center;"

            styled = df.style
            if "Placa" in df.columns: styled = styled.applymap(pill_placa, subset=["Placa"])
            if "Tipo"  in df.columns: styled = styled.applymap(chip_tipo, subset=["Tipo"])

            csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Exportar CSV (manutenções filtradas)", data=csv_bytes,
                               file_name="manutencoes_filtradas.csv", mime="text/csv", use_container_width=True)

            container = st.expander("📋 Ver Manutenções Registradas") if com_expansor else st.container()
            with container:
                st.dataframe(styled, use_container_width=True)
        else:
            st.info("Nenhuma manutenção encontrada.")
