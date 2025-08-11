# modules/cadastro_frota.py
import os
import re
import pandas as pd
import streamlit as st
from datetime import date, datetime

from db import get_conn  # ✅ usa data.db via DB_PATH central
TABLE     = "veiculos"   # ✅ nome novo
FOTOS_DIR = "fotos_frota"

def _fmt_date(d):
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
      .stDateInput input, textarea, .stFileUploader {
        background-color: #ffffff !important; color: #000000 !important;
      }
      .stButton>button {
        background-color: #ffffff !important; color: #004d00 !important; font-weight: 700;
        border: 0; border-radius: 8px;
      }
      .stButton>button:hover { filter: brightness(0.95); }
      .stDataFrame thead tr th { background-color: #d9f2d9 !important; color: #000000 !important; }
      .stDataFrame tbody tr td { background-color: #eaf8ea !important; color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

# ========= Validações =========
import re
_PLACA_LEGADO   = re.compile(r"^[A-Z]{3}\d{4}$")         # AAA1234
_PLACA_MERCOSUL = re.compile(r"^[A-Z]{3}\d[A-Z]\d{2}$")  # ABC1D23
_CHASSI_RE      = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")   # sem I,O,Q

def _validar_placa(placa: str) -> bool:
    if not placa or len(placa) != 7: 
        return False
    placa = placa.upper()
    return bool(_PLACA_LEGADO.match(placa) or _PLACA_MERCOSUL.match(placa))

def _validar_chassi(chassi: str) -> bool:
    if not chassi:
        return True  # opcional
    c = chassi.replace(" ", "").upper()
    return bool(_CHASSI_RE.match(c))

def _coerce_ano(v) -> int | None:
    try:
        iv = int(v)
    except Exception:
        return None
    return iv if 1980 <= iv <= 2100 else None

def _normalize_str(s: str, upper=False) -> str:
    if s is None: 
        return ""
    s = str(s).strip()
    return s.upper() if upper else s

def show(com_expansor: bool = False):
    _inject_css()
    os.makedirs(FOTOS_DIR, exist_ok=True)

    st.subheader("🚛 Cadastro de Frota")

    aba_form, aba_lista = st.tabs(["➕ Nova Frota", "📋 Frotas Cadastradas"])

    # --- Aba 1: Nova Frota ---
    with aba_form:
        with st.form("form_frota"):
            col1, col2 = st.columns(2)
            with col1:
                num_frota = st.text_input("Nº da Frota", placeholder="Ex: FR-06")
                classe_mec = st.text_input("Classe Mecânica", placeholder="Ex: CAMINHÃO TRATOR")
                classe_op  = st.text_input("Classe Operacional", placeholder="Ex: CAVALO MECÂNICO")
                placa = st.text_input("Placa", placeholder="Ex: RNE8A74")
            with col2:
                modelo = st.text_input("Modelo", placeholder="Ex: FH540 6X4T CE")
                marca  = st.text_input("Marca", placeholder="Ex: VOLVO")
                ano    = st.number_input("Ano de Fabricação", min_value=1980, max_value=2100, step=1)
                chassi = st.text_input("Chassi (VIN)", placeholder="Ex: 9BVRG40D5ME899353")

            col3, col4 = st.columns(2)
            with col3:
                status_opt = st.selectbox("Status do veículo", ["Ativo", "Inativo"], index=0)
            with col4:
                foto = st.file_uploader("Foto do Veículo (opcional)", type=["jpg","jpeg","png"])

            submitted = st.form_submit_button("Salvar")

        if submitted:
            payload = {
                "num_frota": _normalize_str(num_frota, upper=True),
                "classe_mecanica": _normalize_str(classe_mec),
                "classe_operacional": _normalize_str(classe_op),
                "placa": _normalize_str(placa, upper=True),
                "modelo": _normalize_str(modelo),
                "marca": _normalize_str(marca, upper=True),
                "ano_fabricacao": _coerce_ano(ano),
                "chassi": _normalize_str(chassi, upper=True).replace(" ", ""),
                "status": status_opt.strip().lower(),  # ✅ casa com default 'ativo'
            }

            erros = []
            if not payload["num_frota"] and not payload["placa"]:
                erros.append("Informe pelo menos **Nº da Frota** ou **Placa**.")
            if payload["placa"] and not _validar_placa(payload["placa"]):
                erros.append("**Placa** inválida. Use formato AAA1234 (antigo) ou ABC1D23 (Mercosul).")
            if payload["chassi"] and not _validar_chassi(payload["chassi"]):
                erros.append("**Chassi** inválido. Deve ter 17 caracteres alfanuméricos (sem I, O, Q).")
            if ano and payload["ano_fabricacao"] is None:
                erros.append("**Ano de Fabricação** fora do intervalo permitido (1980–2100).")

            if erros:
                for e in erros:
                    st.error(e)
            else:
                upsert_key = "num_frota" if payload["num_frota"] else "placa"
                cols = ", ".join(payload.keys())
                qs   = ", ".join(["?"] * len(payload))
                set_clause = ", ".join([f"{k}=excluded.{k}" for k in payload.keys() if k != upsert_key])

                sql = f"""
                    INSERT INTO {TABLE} ({cols}) VALUES ({qs})
                    ON CONFLICT({upsert_key}) DO UPDATE SET {set_clause};
                """
                try:
                    with get_conn() as conn:
                        conn.execute(sql, list(payload.values()))
                    if foto and payload["placa"]:
                        with open(os.path.join(FOTOS_DIR, f"{payload['placa']}.jpg"), "wb") as f:
                            f.write(foto.read())
                    st.success("Frota salva/atualizada com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

    # --- Aba 2: Frotas Cadastradas ---
    with aba_lista:
        try:
            with get_conn() as conn:
                df = pd.read_sql(f"SELECT * FROM {TABLE}", conn)
        except Exception as e:
            st.error(f"Erro ao carregar frota: {e}")
            df = pd.DataFrame()

        colf1, colf2, colf3, colf4 = st.columns(4)
        with colf1:
            f_num_frota = st.text_input("Filtro: Nº da Frota")
        with colf2:
            f_mec = st.text_input("Filtro: Classe Mecânica")
        with colf3:
            f_op = st.text_input("Filtro: Classe Operacional")
        with colf4:
            f_marca = st.text_input("Filtro: Marca")
        colf5, colf6 = st.columns(2)
        with colf5:
            f_status = st.selectbox("Filtro: Status", ["", "Ativo", "Inativo"], index=0)
        with colf6:
            f_placa = st.text_input("Filtro: Placa")

        if not df.empty:
            if f_num_frota: df = df[df["num_frota"].astype(str).str.contains(f_num_frota, case=False, na=False)]
            if f_mec:       df = df[df["classe_mecanica"].astype(str).str.contains(f_mec, case=False, na=False)]
            if f_op:        df = df[df["classe_operacional"].astype(str).str.contains(f_op, case=False, na=False)]
            if f_marca:     df = df[df["marca"].astype(str).str.contains(f_marca, case=False, na=False)]
            if f_status:    df = df[df["status"].astype(str).str.lower() == f_status.strip().lower()]
            if f_placa:     df = df[df["placa"].astype(str).str.contains(f_placa.strip(), case=False, na=False)]

            if "id" in df.columns: df = df.drop(columns=["id"])

            friendly = {
                "num_frota": "Nº da Frota",
                "classe_mecanica": "Classe Mecânica",
                "classe_operacional": "Classe Operacional",
                "placa": "Placa",
                "modelo": "Modelo",
                "marca": "Marca",
                "ano_fabricacao": "Ano de Fabricação",
                "chassi": "Chassi (VIN)",
                "status": "Status",
            }
            df = df.rename(columns={k: v for k, v in friendly.items() if k in df.columns})

            order = [
                "Nº da Frota","Placa","Modelo","Marca","Ano de Fabricação",
                "Classe Mecânica","Classe Operacional","Chassi (VIN)","Status"
            ]
            existing = [c for c in order if c in df.columns]
            other    = [c for c in df.columns if c not in existing]
            df = df[existing + other]

            def pill_placa(val: str):
                if isinstance(val, str) and val.strip():
                    return ("background-color:#d9f2d9; color:#0f5132; border:1px solid #99d6a6; "
                            "border-radius:999px; padding:2px 8px; font-weight:700; text-align:center;")
                return ""
            def chip_status(val: str):
                if isinstance(val, str):
                    v = val.strip().lower()
                    if v == "ativo":   return "background-color:#2e7d32; color:white; font-weight:700; text-align:center;"
                    if v == "inativo": return "background-color:#546e7a; color:white; font-weight:700; text-align:center;"
                return ""

            styled = df.style
            if "Placa" in df.columns:  styled = styled.applymap(pill_placa, subset=["Placa"])
            if "Status" in df.columns: styled = styled.applymap(chip_status, subset=["Status"])

            csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Exportar CSV (frota filtrada)", data=csv_bytes,
                               file_name="frota_filtrada.csv", mime="text/csv", use_container_width=True)

            container = st.expander("📋 Ver Frotas Cadastradas") if com_expansor else st.container()
            with container:
                st.dataframe(styled, use_container_width=True)
        else:
            st.info("Nenhuma frota encontrada.")
