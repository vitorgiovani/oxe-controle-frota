# modules/relatorios.py
from datetime import date, datetime
from typing import Optional, Tuple
import pandas as pd
import streamlit as st
from db import get_conn  # ✅ usa o data.db central

def _inject_css():
    st.markdown("""
    <style>
      .stApp { background-color: #004d00 !important; color: #ffffff !important; }
      header[data-testid="stHeader"] { background-color: #004d00 !important; }
      .stTabs [data-baseweb="tab"] {
        background-color: #006400 !important; color: #ffffff !important;
        font-weight: 700; font-size: 16px;
      }
      .metric-card { background:#eaf8ea; color:#0a2e0a; padding:14px; border-radius:12px; border:1px solid #bfe8bf; }
      .metric-val { font-size:28px; font-weight:800; }
      .metric-lbl { font-size:12px; opacity:.8; text-transform:uppercase; letter-spacing:.6px; }
      .stDataFrame thead tr th { background-color: #d9f2d9 !important; color: #000000 !important; }
      .stDataFrame tbody tr td { background-color: #eaf8ea !important; color: #000000 !important; }
      .stButton>button {
        background:#ffffff !important; color:#004d00 !important; font-weight:700;
        border:0; border-radius:8px;
      }
    </style>
    """, unsafe_allow_html=True)

def _fmt_date_iso(d):
    if isinstance(d, date): return d.strftime("%Y-%m-%d")
    if isinstance(d, datetime): return d.date().strftime("%Y-%m-%d")
    return str(d) if d else None

def _fmt_br_date_col(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.strftime("%d/%m/%Y").fillna(df[c])
    return df

def _style_chip_status(val: str, mapping: dict):
    if isinstance(val, str):
        v = val.strip().lower()
        color = mapping.get(v)
        if color:
            return f"background-color:{color['bg']}; color:{color['fg']}; font-weight:700; text-align:center;"
    return ""

def _style_pill(val: str):
    if isinstance(val, str) and val.strip():
        return ("background-color:#d9f2d9; color:#0f5132; border:1px solid #99d6a6; "
                "border-radius:999px; padding:2px 8px; font-weight:700; text-align:center;")
    return ""

def _download_csv_button(df: pd.DataFrame, label: str, fname: str):
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(label, data=csv_bytes, file_name=fname, mime="text/csv", use_container_width=True)

# =================== Carga unificada (data.db) ===================
def _load_data():
    with get_conn() as conn:
        df_os = pd.read_sql("""
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
        """, conn)

        df_man = pd.read_sql("""
            SELECT
                m.id,
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
                COALESCE(m.vlr_peca, m.qtd * m.vlr_unitario) AS custo,
                m.fornecedor,
                m.nf
            FROM manutencoes m
            LEFT JOIN veiculos v ON v.id = m.veiculo_id
        """, conn)

        df_frota = pd.read_sql("""
            SELECT id, num_frota, placa, modelo, marca, ano_fabricacao,
                   classe_mecanica, classe_operacional, chassi, status
            FROM veiculos
        """, conn)

    return df_os, df_man, df_frota

def _apply_global_filters(
    df_os: pd.DataFrame,
    df_man: pd.DataFrame,
    df_frota: pd.DataFrame,
    dt_range: Tuple[Optional[date], Optional[date]],
    status_os: str,
    placa: str,
    num_frota: str,
):
    start, end = dt_range
    if not df_os.empty:
        if start: df_os = df_os[df_os["data_abertura"] >= _fmt_date_iso(start)]
        if end:   df_os = df_os[df_os["data_abertura"] <= _fmt_date_iso(end)]
        if status_os: df_os = df_os[df_os["status"].astype(str).str.lower() == status_os.strip().lower()]
        if placa: df_os = df_os[df_os["placa"].astype(str).str.contains(placa, case=False, na=False)]
        if num_frota: df_os = df_os[df_os["num_frota"].astype(str).str.contains(num_frota, case=False, na=False)]

    if not df_man.empty:
        if start: df_man = df_man[df_man["data"] >= _fmt_date_iso(start)]
        if end:   df_man = df_man[df_man["data"] <= _fmt_date_iso(end)]
        if placa: df_man = df_man[df_man["placa"].astype(str).str.contains(placa, case=False, na=False)]
        if num_frota: df_man = df_man[df_man["num_frota"].astype(str).str.contains(num_frota, case=False, na=False)]

    if not df_frota.empty:
        if placa: df_frota = df_frota[df_frota["placa"].astype(str).str.contains(placa, case=False, na=False)]
        if num_frota: df_frota = df_frota[df_frota["num_frota"].astype(str).str.contains(num_frota, case=False, na=False)]

    return df_os, df_man, df_frota

# =================== UI principal ===================
def show():
    _inject_css()
    st.subheader("📊 Relatórios")

    # --- Filtros globais ---
    colf1, colf2, colf3 = st.columns([2,2,2])
    with colf1:
        dt_start = st.date_input("De", value=None)
    with colf2:
        dt_end = st.date_input("Até", value=None)
    with colf3:
        placa = st.text_input("Placa (contém)", value="")
    colf4, colf5 = st.columns([2,2])
    with colf4:
        num_frota = st.text_input("Nº da Frota (contém)", value="")
    with colf5:
        status_os = st.selectbox("Status OS", ["", "aberta", "em execução", "fechada"], index=0)

    # --- Carrega dados do data.db ---
    df_os, df_man, df_frota = _load_data()

    # --- Aplica filtros globais ---
    df_os, df_man, df_frota = _apply_global_filters(
        df_os, df_man, df_frota,
        (dt_start if dt_start else None, dt_end if dt_end else None),
        status_os, placa, num_frota
    )

    # --- KPIs ---
    c1, c2, c3, c4 = st.columns(4)
    total_os = len(df_os) if not df_os.empty else 0
    abertas  = int((df_os.get("status","").astype(str).str.lower() == "aberta").sum()) if not df_os.empty else 0
    execucao = int(df_os.get("status","").astype(str).str.lower().isin(["em execução", "em execucao"]).sum()) if not df_os.empty else 0
    fechadas = int((df_os.get("status","").astype(str).str.lower() == "fechada").sum()) if not df_os.empty else 0
    total_man = len(df_man) if not df_man.empty else 0
    custo_total = float(pd.to_numeric(df_man.get("custo", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not df_man.empty else 0.0
    frota_total = len(df_frota) if not df_frota.empty else 0
    ativos = int((df_frota.get("status","").astype(str).str.lower() == "ativo").sum()) if not df_frota.empty else 0

    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-lbl">OS (total)</div><div class="metric-val">{total_os}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-lbl">OS (abertas / exec / fech)</div><div class="metric-val">{abertas} / {execucao} / {fechadas}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-lbl">Manutenções (total)</div><div class="metric-val">{total_man}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="metric-lbl">Custo total</div><div class="metric-val">R$ {custo_total:,.2f}</div></div>'.replace(",", "X").replace(".", ",").replace("X","."), unsafe_allow_html=True)

    c5, c6 = st.columns(2)
    with c5:
        st.markdown(f'<div class="metric-card"><div class="metric-lbl">Frota (total)</div><div class="metric-val">{frota_total}</div></div>', unsafe_allow_html=True)
    with c6:
        st.markmarkdown = st.markdown(f'<div class="metric-card"><div class="metric-lbl">Veículos ativos</div><div class="metric-val">{ativos}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    tab_os, tab_man, tab_frota, tab_grafs = st.tabs(["🧾 OS", "🛠️ Manutenções", "🚛 Frota", "📈 Gráficos"])

    # ====== Tabela OS ======
    with tab_os:
        df = df_os.copy()
        if not df.empty:
            df = _fmt_br_date_col(df, ["data_abertura","previsao_saida","data_liberacao"])
            if "orcamento" in df.columns:
                df["orcamento"] = pd.to_numeric(df["orcamento"], errors="coerce").fillna(0)
                df["orcamento"] = df["orcamento"].map(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

            if "id" in df.columns: df = df.drop(columns=["id"])
            friendly = {
                "num_os":"Nº da OS","num_frota":"Nº da Frota","placa":"Placa",
                "data_abertura":"Data de Abertura","previsao_saida":"Previsão de Saída","data_liberacao":"Data de Liberação",
                "modelo":"Modelo","marca":"Marca","ano_fabricacao":"Ano de Fabricação","chassi":"Chassi (VIN)",
                "descricao":"Descrição do Serviço","prioridade":"Prioridade","sc":"SC (Chamado)","orcamento":"Orçamento",
                "responsavel":"Responsável","status":"Status",
            }
            df = df.rename(columns={k:v for k,v in friendly.items() if k in df.columns})

            order = ["Nº da OS","Nº da Frota","Placa","Data de Abertura","Previsão de Saída","Data de Liberação",
                     "Status","Prioridade","Responsável","Modelo","Marca","Ano de Fabricação","Chassi (VIN)","SC (Chamado)","Orçamento","Descrição do Serviço"]
            exist = [c for c in order if c in df.columns]; other = [c for c in df.columns if c not in exist]
            df = df[exist + other]

            styled = df.style
            if "Status" in df.columns:
                os_map = {
                    "aberta":{"bg":"#2e7d32","fg":"#fff"},
                    "em execução":{"bg":"#f9a825","fg":"#000"},
                    "em execucao":{"bg":"#f9a825","fg":"#000"},
                    "fechada":{"bg":"#546e7a","fg":"#fff"},
                }
                styled = styled.applymap(lambda v: _style_chip_status(v, os_map), subset=["Status"])
            if "Placa" in df.columns:
                styled = styled.applymap(_style_pill, subset=["Placa"])

            _download_csv_button(df, "⬇️ Exportar CSV (OS)", "relatorio_os.csv")
            st.dataframe(styled, use_container_width=True)
        else:
            st.info("Sem dados de OS neste filtro.")

    # ====== Tabela Manutenções ======
    with tab_man:
        df = df_man.copy()
        if not df.empty:
            df = _fmt_br_date_col(df, ["data"])
            if "custo" in df.columns:
                df["custo"] = pd.to_numeric(df["custo"], errors="coerce").fillna(0)
                df["custo"] = df["custo"].map(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

            if "id" in df.columns: df = df.drop(columns=["id"])
            friendly = {
                "num_frota":"Nº da Frota","placa":"Placa","tipo":"Tipo",
                "data":"Data","mes":"Mês (aaaa-mm)","sc":"SC",
                "cod_peca":"Código Peça","desc_peca":"Descrição",
                "qtd":"Qtd","vlr_unitario":"Vlr Unitário","fornecedor":"Fornecedor",
                "nf":"NF.","custo":"Custo",
                "modelo":"Modelo","marca":"Marca","ano_fabricacao":"Ano de Fabricação","chassi":"Chassi (VIN)",
            }
            df = df.rename(columns={k:v for k,v in friendly.items() if k in df.columns})

            # Mês legível
            if "Mês (aaaa-mm)" in df.columns:
                tmp = pd.to_datetime(df["Mês (aaaa-mm)"]+"-01", errors="coerce")
                df["Mês"] = tmp.dt.strftime("%b/%y").str.lower()
                df = df.drop(columns=["Mês (aaaa-mm)"])

            order = ["Nº da Frota","Placa","Data","Mês","Tipo","SC","Código Peça","Descrição","Qtd","Vlr Unitário","Custo","Fornecedor","NF.",
                     "Modelo","Marca","Ano de Fabricação","Chassi (VIN)"]
            exist = [c for c in order if c in df.columns]; other = [c for c in df.columns if c not in exist]
            df = df[exist + other]

            styled = df.style
            if "Placa" in df.columns:
                styled = styled.applymap(_style_pill, subset=["Placa"])

            _download_csv_button(df, "⬇️ Exportar CSV (Manutenções)", "relatorio_manutencoes.csv")
            st.dataframe(styled, use_container_width=True)
        else:
            st.info("Sem dados de Manutenções neste filtro.")

    # ====== Tabela Frota ======
    with tab_frota:
        df = df_frota.copy()
        if not df.empty:
            if "id" in df.columns: df = df.drop(columns=["id"])
            friendly = {
                "num_frota":"Nº da Frota","placa":"Placa","modelo":"Modelo","marca":"Marca",
                "ano_fabricacao":"Ano de Fabricação","classe_mecanica":"Classe Mecânica",
                "classe_operacional":"Classe Operacional","chassi":"Chassi (VIN)","status":"Status"
            }
            df = df.rename(columns={k:v for k,v in friendly.items() if k in df.columns})
            order = ["Nº da Frota","Placa","Modelo","Marca","Ano de Fabricação","Classe Mecânica","Classe Operacional","Chassi (VIN)","Status"]
            exist = [c for c in order if c in df.columns]; other = [c for c in df.columns if c not in exist]
            df = df[exist + other]

            styled = df.style
            if "Placa" in df.columns:
                styled = styled.applymap(_style_pill, subset=["Placa"])

            _download_csv_button(df, "⬇️ Exportar CSV (Frota)", "relatorio_frota.csv")
            st.dataframe(styled, use_container_width=True)
        else:
            st.info("Sem dados de Frota neste filtro.")

    # ====== Gráficos rápidos ======
    with tab_grafs:
        g1, g2 = st.columns(2)

        with g1:
            st.markdown("**OS por Status**")
            if not df_os.empty and "status" in df_os.columns:
                os_status = df_os["status"].astype(str).str.title().value_counts().rename_axis("Status").reset_index(name="Qtd")
                st.bar_chart(os_status.set_index("Status"))
            else:
                st.info("Sem dados de OS para este gráfico.")

        with g2:
            st.markdown("**Manutenções por Tipo**")
            if not df_man.empty and "tipo" in df_man.columns:
                man_tipo = df_man["tipo"].astype(str).value_counts().rename_axis("Tipo").reset_index(name="Qtd")
                st.bar_chart(man_tipo.set_index("Tipo"))
            else:
                st.info("Sem dados de Manutenções para este gráfico.")

        st.markdown("---")
        st.markdown("**Top 10 Placas por Custo de Manutenção**")
        if not df_man.empty and {"placa","custo"}.issubset(df_man.columns):
            rank = df_man.copy()
            rank["custo"] = pd.to_numeric(rank["custo"], errors="coerce").fillna(0)
            top = (rank.groupby("placa", dropna=False)["custo"].sum()
                        .sort_values(ascending=False)
                        .head(10)
                        .rename_axis("Placa").reset_index(name="Custo Total"))
            top_fmt = top.copy()
            top_fmt["Custo Total"] = top_fmt["Custo Total"].map(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
            _download_csv_button(top_fmt, "⬇️ Exportar CSV (Top Placas por Custo)", "top_placas_custo.csv")
            st.bar_chart(top.set_index("Placa"))
        else:
            st.info("Sem dados para ranking de custo.")
