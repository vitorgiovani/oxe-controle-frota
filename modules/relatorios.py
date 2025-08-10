import os
import sqlite3
from datetime import date, datetime
from typing import Optional, Tuple
import pandas as pd
import streamlit as st

# ====== Bancos e tabelas (ajuste se quiser unificar) ======
DB_OS_PATH    = "ordens_servico.db"
DB_MAN_PATH   = "manutencao.db"
DB_FROTA_PATH = "frota.db"

T_OS   = "abertura_os"
T_MAN  = "manutencoes"
T_FROT = "frota"

# =================== Infra ===================
@st.cache_resource
def _conn(path: str):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    return sqlite3.connect(path, check_same_thread=False)

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

# =================== Carga de dados ===================
def _load_df(path: str, table: str) -> pd.DataFrame:
    try:
        con = _conn(path)
        return pd.read_sql(f"SELECT * FROM {table}", con)
    except Exception:
        return pd.DataFrame()

def _apply_global_filters(
    df_os: pd.DataFrame,
    df_man: pd.DataFrame,
    df_frota: pd.DataFrame,
    dt_range: Tuple[Optional[date], Optional[date]],
    status_os: str,
    status_man: str,
    placa: str,
    num_frota: str,
):
    start, end = dt_range
    # OS
    if not df_os.empty:
        if start: df_os = df_os[df_os["data_abertura"] >= _fmt_date_iso(start)]
        if end:   df_os = df_os[df_os["data_abertura"] <= _fmt_date_iso(end)]
        if status_os: df_os = df_os[df_os["status"] == status_os]
        if placa: df_os = df_os[df_os["placa"].astype(str).str.contains(placa, case=False, na=False)]
        if num_frota: df_os = df_os[df_os["num_frota"].astype(str).str.contains(num_frota, case=False, na=False)]
    # Manutenção
    if not df_man.empty:
        if start: df_man = df_man[df_man["data_manutencao"] >= _fmt_date_iso(start)]
        if end:   df_man = df_man[df_man["data_manutencao"] <= _fmt_date_iso(end)]
        if status_man: df_man = df_man[df_man["status"] == status_man]
        if placa: df_man = df_man[df_man["placa"].astype(str).str.contains(placa, case=False, na=False)]
        if num_frota: df_man = df_man[df_man["num_frota"].astype(str).str.contains(num_frota, case=False, na=False)]
    # Frota (sem data)
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
    colf4, colf5, colf6 = st.columns([2,2,2])
    with colf4:
        num_frota = st.text_input("Nº da Frota (contém)", value="")
    with colf5:
        status_os = st.selectbox("Status OS", ["", "Aberta", "Em execução", "Fechada"], index=0)
    with colf6:
        status_man = st.selectbox("Status Manutenção", ["", "Pendente", "Em execução", "Concluída"], index=0)

    # --- Carrega dados ---
    df_os   = _load_df(DB_OS_PATH, T_OS)
    df_man  = _load_df(DB_MAN_PATH, T_MAN)
    df_frot = _load_df(DB_FROTA_PATH, T_FROT)

    df_os, df_man, df_frot = _apply_global_filters(
        df_os, df_man, df_frot,
        (dt_start if dt_start else None, dt_end if dt_end else None),
        status_os, status_man, placa, num_frota
    )

    # --- KPIs ---
    c1, c2, c3, c4 = st.columns(4)
    total_os = len(df_os) if not df_os.empty else 0
    abertas  = int((df_os["status"].str.lower() == "aberta").sum()) if "status" in df_os.columns else 0
    execucao = int(df_os["status"].str.lower().isin(["em execução", "em execucao"]).sum()) if "status" in df_os.columns else 0
    fechadas = int((df_os["status"].str.lower() == "fechada").sum()) if "status" in df_os.columns else 0
    total_man = len(df_man) if not df_man.empty else 0
    custo_total = float(pd.to_numeric(df_man.get("custo", pd.Series([])), errors="coerce").fillna(0).sum()) if not df_man.empty else 0.0
    frota_total = len(df_frot) if not df_frot.empty else 0
    ativos = int((df_frot["status"].str.lower() == "ativo").sum()) if "status" in df_frot.columns else 0

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
        st.markdown(f'<div class="metric-card"><div class="metric-lbl">Veículos ativos</div><div class="metric-val">{ativos}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # --- Abas de relatórios detalhados ---
    tab_os, tab_man, tab_frota, tab_grafs = st.tabs(["🧾 OS", "🛠️ Manutenções", "🚛 Frota", "📈 Gráficos"])

    # ====== Tabela OS ======
    with tab_os:
        df = df_os.copy()
        if not df.empty:
            # formatações
            df = _fmt_br_date_col(df, ["data_abertura","previsao_saida","data_liberacao"])
            if "orcamento" in df.columns:
                df["orcamento"] = pd.to_numeric(df["orcamento"], errors="coerce").fillna(0)
                df["orcamento"] = df["orcamento"].map(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
            if "id" in df.columns: df = df.drop(columns=["id"])

            friendly = {
                "numero_os":"Nº da OS","num_frota":"Nº da Frota","placa":"Placa",
                "data_abertura":"Data de Abertura","previsao_saida":"Previsão de Saída","data_liberacao":"Data de Liberação",
                "modelo":"Modelo","marca":"Marca","ano":"Ano de Fabricação","chassi":"Chassi (VIN)",
                "descritivo_servico":"Descritivo do Serviço","sc":"SC (Chamado)","orcamento":"Orçamento",
                "responsavel":"Responsável","status":"Status",
            }
            df = df.rename(columns={k:v for k,v in friendly.items() if k in df.columns})

            order = ["Nº da OS","Nº da Frota","Placa","Data de Abertura","Previsão de Saída","Data de Liberação",
                     "Status","Responsável","Modelo","Marca","Ano de Fabricação","Chassi (VIN)","SC (Chamado)","Orçamento","Descritivo do Serviço"]
            exist = [c for c in order if c in df.columns]; other = [c for c in df.columns if c not in exist]
            df = df[exist + other]

            # Style chips/pills
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
            df = _fmt_br_date_col(df, ["data_manutencao"])
            if "custo" in df.columns:
                df["custo"] = pd.to_numeric(df["custo"], errors="coerce").fillna(0)
                df["custo"] = df["custo"].map(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
            if "id" in df.columns: df = df.drop(columns=["id"])

            friendly = {
                "numero_os":"Nº da OS","num_frota":"Nº da Frota","placa":"Placa","tipo":"Tipo",
                "data_manutencao":"Data","km":"Quilometragem","custo":"Custo",
                "descricao":"Descrição","responsavel":"Responsável","status":"Status",
            }
            df = df.rename(columns={k:v for k,v in friendly.items() if k in df.columns})

            order = ["Nº da OS","Nº da Frota","Placa","Tipo","Data","Status","Responsável","Quilometragem","Custo","Descrição"]
            exist = [c for c in order if c in df.columns]; other = [c for c in df.columns if c not in exist]
            df = df[exist + other]

            styled = df.style
            if "Status" in df.columns:
                man_map = {
                    "pendente":{"bg":"#b71c1c","fg":"#fff"},
                    "em execução":{"bg":"#f9a825","fg":"#000"},
                    "em execucao":{"bg":"#f9a825","fg":"#000"},
                    "concluída":{"bg":"#2e7d32","fg":"#fff"},
                    "concluida":{"bg":"#2e7d32","fg":"#fff"},
                }
                styled = styled.applymap(lambda v: _style_chip_status(v, man_map), subset=["Status"])
            if "Placa" in df.columns:
                styled = styled.applymap(_style_pill, subset=["Placa"])

            _download_csv_button(df, "⬇️ Exportar CSV (Manutenções)", "relatorio_manutencoes.csv")
            st.dataframe(styled, use_container_width=True)
        else:
            st.info("Sem dados de Manutenções neste filtro.")

    # ====== Tabela Frota ======
    with tab_frota:
        df = df_frot.copy()
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
            if "Status" in df.columns:
                frota_map = {
                    "ativo":{"bg":"#2e7d32","fg":"#fff"},
                    "inativo":{"bg":"#546e7a","fg":"#fff"},
                }
                styled = styled.applymap(lambda v: _style_chip_status(v, frota_map), subset=["Status"])
            if "Placa" in df.columns:
                styled = styled.applymap(_style_pill, subset=["Placa"])

            _download_csv_button(df, "⬇️ Exportar CSV (Frota)", "relatorio_frota.csv")
            st.dataframe(styled, use_container_width=True)
        else:
            st.info("Sem dados de Frota neste filtro.")

    # ====== Gráficos rápidos ======
    with tab_grafs:
        g1, g2 = st.columns(2)

        # OS por Status
        with g1:
            st.markdown("**OS por Status**")
            if not df_os.empty and "status" in df_os.columns:
                os_status = df_os["status"].str.title().value_counts().rename_axis("Status").reset_index(name="Qtd")
                st.bar_chart(os_status.set_index("Status"))
            else:
                st.info("Sem dados de OS para este gráfico.")

        # Manutenção por Tipo
        with g2:
            st.markdown("**Manutenções por Tipo**")
            if not df_man.empty and "tipo" in df_man.columns:
                man_tipo = df_man["tipo"].value_counts().rename_axis("Tipo").reset_index(name="Qtd")
                st.bar_chart(man_tipo.set_index("Tipo"))
            else:
                st.info("Sem dados de Manutenções para este gráfico.")

        st.markdown("---")
        # Top Placas por Custo
        st.markdown("**Top 10 Placas por Custo de Manutenção**")
        if not df_man.empty and {"placa","custo"}.issubset(df_man.columns):
            rank = df_man.copy()
            rank["custo"] = pd.to_numeric(rank["custo"], errors="coerce").fillna(0)
            top = (rank.groupby("placa", dropna=False)["custo"].sum()
                        .sort_values(ascending=False)
                        .head(10)
                        .rename_axis("Placa").reset_index(name="Custo Total"))
            # formato BR pra exibição
            top_fmt = top.copy()
            top_fmt["Custo Total"] = top_fmt["Custo Total"].map(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
            _download_csv_button(top_fmt, "⬇️ Exportar CSV (Top Placas por Custo)", "top_placas_custo.csv")
            st.bar_chart(top.set_index("Placa"))
        else:
            st.info("Sem dados para ranking de custo.")
