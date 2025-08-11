# modules/listar_editar_carros.py
import sqlite3, io, csv
import streamlit as st

TABLE = "veiculos"

# ---------- conexão ----------
def _fallback_conn():
    return sqlite3.connect("data.db", check_same_thread=False)

try:
    from db import get_connection as _get_connection
    def get_connection():
        return _get_connection()
except Exception:
    def get_connection():
        return _fallback_conn()

# ---------- colunas ----------
COLS_REQUIRED = ["id", "placa", "modelo", "ano", "marca", "status", "criado_em"]
COLS_OPTIONAL = ["num_frota", "ano_fabricacao", "chassi", "classe_mecanica", "classe_operacional"]
COLS = COLS_REQUIRED + COLS_OPTIONAL

def _get_existing_cols(conn):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({TABLE})")
    return [row[1] for row in cur.fetchall()]

def _ensure_required(existing_cols):
    miss = [c for c in COLS_REQUIRED if c not in existing_cols]
    if miss:
        raise RuntimeError(f"Tabela `{TABLE}` não tem as colunas obrigatórias: {', '.join(miss)}")

# ---------- utils ----------
def _to_int_or_none(v: str):
    v = (v or "").strip()
    if v == "": return None
    try: return int(v)
    except: return v

def _chip(txt: str) -> str:
    return ("<span style=\"display:inline-block;background:#132e13;"
            "border:1px solid rgba(255,255,255,.15);padding:2px 8px;"
            "border-radius:999px;font-size:12px;line-height:18px;\">"
            f"{txt}</span>")

def _status_badge(txt: str) -> str:
    t = (txt or "").strip().lower()
    if t in ("ativo","ok","disponível","disponivel"):
        bg, fg = "#c8f7c5", "#0a4d0a"
    elif t in ("manutenção","manutencao","oficina"):
        bg, fg = "#fff0c2", "#8a6d1f"
    elif t in ("inativo","baixa","desativado"):
        bg, fg = "#ffd6d6", "#7a1f1f"
    else:
        bg, fg = "rgba(255,255,255,.12)", "#ddd"
    return f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:999px;font-size:12px;">{txt or "-"}</span>'

def _row_key(prefix, vid): return f"{prefix}_{vid}"

def _confirm_delete_ui(vid):
    st.warning(f"Excluir o veículo ID {vid}? Essa ação é irreversível.")
    c1, c2 = st.columns(2)
    return c1.button("Sim, excluir", type="primary", key=_row_key("conf_del", vid)), \
           c2.button("Cancelar", key=_row_key("cancel_del", vid))

def _csv_bytes_from_rows(cols, rows):
    wanted = [c for c in ["placa","modelo","marca","ano","status","num_frota","chassi"] if c in cols]
    buf = io.StringIO(); w = csv.writer(buf); w.writerow(wanted)
    for r in rows:
        d = dict(zip(cols, r)); w.writerow([d.get(c, "") for c in wanted])
    return buf.getvalue().encode("utf-8-sig")

# ---------- queries ----------
def listar(conn, filtro=""):
    cur = conn.cursor()
    base = f"SELECT id, placa, modelo, ano, marca, status FROM {TABLE}"
    if filtro:
        like = f"%{filtro}%"
        cur.execute(base + " WHERE placa LIKE ? OR modelo LIKE ? ORDER BY placa", (like, like))
    else:
        cur.execute(base + " ORDER BY placa")
    cols = [d[0] for d in cur.description]
    return cols, cur.fetchall()

def buscar(conn, vid: int, cols_present):
    sel_cols = ", ".join(cols_present)
    cur = conn.cursor()
    cur.execute(f"SELECT {sel_cols} FROM {TABLE} WHERE id = ?", (vid,))
    row = cur.fetchone()
    return dict(zip(cols_present, row)) if row else None

def atualizar(conn, vid: int, data: dict, cols_present):
    settable = [c for c in cols_present if c not in ("id","criado_em")]
    parts, params = [], []
    for c in settable:
        if c in data: parts.append(f"{c} = ?"); params.append(data[c])
    if not parts: return
    sql = f"UPDATE {TABLE} SET {', '.join(parts)} WHERE id = ?"
    params.append(vid)
    cur = conn.cursor(); cur.execute(sql, params); conn.commit()

def excluir(conn, vid: int):
    cur = conn.cursor(); cur.execute(f"DELETE FROM {TABLE} WHERE id = ?", (vid,)); conn.commit()

# ---------- editor (reuso) ----------
def _render_edit_form(current: dict, cols_present, conn, vid):
    with st.form(_row_key("form", vid)):
        f1, f2 = st.columns(2)
        with f1:
            placa = st.text_input("Placa", (current.get("placa") or "")).upper().strip()
            modelo = st.text_input("Modelo", (current.get("modelo") or "")).strip()
            ano = _to_int_or_none(st.text_input("Ano (modelo)", str(current.get("ano") or "")).strip())
            marca = st.text_input("Marca", (current.get("marca") or "")).strip()
            status_opts = ["ativo","manutenção","inativo"]
            cur_status = (current.get("status") or "ativo").lower()
            idx = status_opts.index(cur_status) if cur_status in status_opts else 0
            status = st.selectbox("Status", status_opts, index=idx)
        with f2:
            num_frota = st.text_input("Nº da frota / rota", str(current.get("num_frota") or "")).strip() if "num_frota" in cols_present else None
            ano_fabricacao = _to_int_or_none(st.text_input("Ano de fabricação", str(current.get("ano_fabricacao") or "")).strip()) if "ano_fabricacao" in cols_present else None
            chassi = st.text_input("Chassi (VIN)", (current.get("chassi") or "")).strip() if "chassi" in cols_present else None
            classe_mecanica = st.text_input("Classe Mecânica", (current.get("classe_mecanica") or "")).strip() if "classe_mecanica" in cols_present else None
            classe_operacional = st.text_input("Classe Operacional", (current.get("classe_operacional") or "")).strip() if "classe_operacional" in cols_present else None
            st.text_input("Criado em", str(current.get("criado_em") or ""), disabled=True)

        bsave, bcancel = st.columns([2,1])
        salvar = bsave.form_submit_button("💾 Salvar", type="primary")
        cancelar = bcancel.form_submit_button("Cancelar")

    if salvar:
        if not placa or not modelo:
            st.error("Placa e modelo são obrigatórios.")
        else:
            try:
                payload = {"placa": placa, "modelo": modelo, "ano": ano, "status": status, "marca": marca}
                if "num_frota" in cols_present: payload["num_frota"] = num_frota
                if "ano_fabricacao" in cols_present: payload["ano_fabricacao"] = ano_fabricacao
                if "chassi" in cols_present: payload["chassi"] = chassi
                if "classe_mecanica" in cols_present: payload["classe_mecanica"] = classe_mecanica
                if "classe_operacional" in cols_present: payload["classe_operacional"] = classe_operacional
                atualizar(conn, vid, payload, cols_present)
                st.success("Atualizado com sucesso!")
                st.session_state.edit_id = None
                st.rerun()
            except sqlite3.IntegrityError as e:
                st.error(f"Erro de integridade (ex.: UNIQUE/NOT NULL): {e}")
            except Exception as e:
                st.error(f"Falha ao atualizar: {e}")

    if cancelar:
        st.session_state.edit_id = None
        st.rerun()

def _open_editor(conn, vid, cols_present):
    current = buscar(conn, vid, cols_present)
    title = f"Editar veículo — {(current.get('placa') or '').upper()}" if current else "Editar veículo"
    # Se tiver suporte a modal (st.dialog), abre janelinha; senão, cai no inline
    if hasattr(st, "dialog"):
        @st.dialog(title)
        def _dlg():
            _render_edit_form(current, cols_present, conn, vid)
        _dlg()
    else:
        st.session_state.edit_id = vid

# ---------- página ----------
def page():
    st.title("🚗 Frota — Listar & Editar")

    # estilos (zebra + hover + linha ativa) e botão de placa estilo link
    st.markdown("""
    <style>
      .row-strip{padding:8px 10px;border-radius:10px;margin:4px 0;}
      .row-strip:nth-child(odd){background:rgba(255,255,255,.035);}
      .row-strip:nth-child(even){background:rgba(0,0,0,.08);}
      .row-strip:hover{background:rgba(255,255,255,.08);outline:1px solid rgba(255,255,255,.12);}
      .row-active{background:rgba(255,255,255,.14)!important;outline:1px solid rgba(255,255,255,.28)!important;}
      /* botão da placa com cara de link */
      .placa-btn button{background:transparent!important;color:#fff!important;border:0!important;
                        padding:0!important;text-decoration:underline;}
      .placa-btn button:hover{filter:brightness(1.1);}
    </style>
    """, unsafe_allow_html=True)

    if "edit_id" not in st.session_state: st.session_state.edit_id = None
    if "confirm_del" not in st.session_state: st.session_state.confirm_del = None

    with get_connection() as conn:
        existing_cols = _get_existing_cols(conn)
        _ensure_required(existing_cols)
        cols_present = [c for c in COLS if c in existing_cols]

        # ---- Controles (autocomplete + filtro + limpar)
        st.caption("Busque digitando a placa/modelo (autocomplete) ou filtre por placa.")
        cols_all, rows_all = listar(conn, "")
        choices, id_by_label = [], {}
        for row in rows_all:
            d = dict(zip(cols_all, row))
            placa = (d.get("placa") or "").upper()
            modelo = d.get("modelo") or ""
            marca  = d.get("marca")  or ""
            label = f"{placa} — {modelo}{(' · ' + marca) if marca else ''}"
            choices.append(label); id_by_label[label] = d["id"]

        c1, c2, c3 = st.columns([3,2,1])
        sel = c1.selectbox("Selecionar veículo (autocomplete)", [""] + choices, index=0, placeholder="Digite placa ou modelo…")
        filtro_placa = c2.text_input("Filtro por placa (contém)", "")
        if c3.button("Limpar filtros"):
            st.session_state.edit_id = None
            st.rerun()

        # dataset filtrado (antes da paginação)
        if sel:
            sel_id = id_by_label[sel]
            row_sel = next((r for r in rows_all if dict(zip(cols_all, r))["id"] == sel_id), None)
            cols_f, rows_f = cols_all, ([row_sel] if row_sel else [])
        else:
            cols_f, rows_f = listar(conn, filtro_placa.strip())

        if not rows_f:
            st.info("Nenhum veículo encontrado."); return

        # barra superior: +Novo / Exportar CSV
        topL, topS, topR = st.columns([1,6,1])
        if topL.button("➕ Novo", help="Ir para a aba Cadastrar"):
            st.session_state["frota_tab"] = "Cadastrar"; st.rerun()
        csv_bytes = _csv_bytes_from_rows(cols_f, rows_f)
        topR.download_button("⬇️ Exportar CSV", data=csv_bytes, file_name="frota_filtrada.csv", mime="text/csv")

        # --- paginação (select Por página + página atual)
        total = len(rows_f)
        p1, p2, p3 = st.columns([1,1,2])
        page_size = p1.selectbox("Por página", [10,25,50], index=1)  # 25 default
        n_pages = (total + page_size - 1) // page_size if total else 1
        page_idx = p2.number_input("Página", 1, max(n_pages,1), 1, step=1)
        start = (page_idx-1)*page_size; end = min(start + page_size, total)
        p3.markdown(f"<div style='text-align:right;opacity:.85'>Mostrando <b>{start+1}-{end}</b> de <b>{total}</b></div>", unsafe_allow_html=True)
        rows = rows_f[start:end]; cols = cols_f

        # Cabeçalho
        header = st.columns([0.8, 2.2, 3.2, 1.1, 2.2, 1.4])
        header[0].markdown("**#**")
        header[1].markdown("**Placa**")
        header[2].markdown("**Modelo / Status**")
        header[3].markdown("**Ano**")
        header[4].markdown("**Marca**")
        header[5].markdown("**Ações**")

        # Linhas
        for i, r in enumerate(rows, start=start+1):
            d = dict(zip(cols, r)); vid = d["id"]
            row_cls = "row-strip row-active" if st.session_state.edit_id == vid else "row-strip"
            st.markdown(f'<div class="{row_cls}">', unsafe_allow_html=True)

            c = st.columns([0.8, 2.2, 3.2, 1.1, 2.2, 1.4])
            c[0].markdown(_chip(str(i)), unsafe_allow_html=True)

            # Placa clicável (abre modal se disponível)
            with c[1]:
                st.markdown('<div class="placa-btn">', unsafe_allow_html=True)
                if st.button((d.get("placa") or "").upper(), key=_row_key("plk", vid), help="Abrir editor"):
                    _open_editor(conn, vid, cols_present)
                st.markdown('</div>', unsafe_allow_html=True)

            modelo = d.get("modelo") or ""
            c[2].markdown(f"{modelo}<br>{_status_badge(d.get('status') or '')}", unsafe_allow_html=True)
            c[3].markdown(_chip(d.get("ano") or ""), unsafe_allow_html=True)
            c[4].write(d.get("marca") or "")

            b_edit, b_del = c[5].columns(2)
            if b_edit.button("✏️", key=_row_key("edit", vid), help="Editar"):
                _open_editor(conn, vid, cols_present)
            if b_del.button("🗑️", key=_row_key("del", vid), help="Excluir"):
                st.session_state.confirm_del = vid; st.session_state.edit_id = None

            if st.session_state.confirm_del == vid:
                ok, cancel = _confirm_delete_ui(vid)
                if ok:
                    try:
                        excluir(conn, vid); st.success("Veículo excluído.")
                        st.session_state.confirm_del = None; st.rerun()
                    except Exception as e:
                        st.error(f"Falha ao excluir: {e}")
                if cancel:
                    st.session_state.confirm_del = None; st.rerun()

            # Fallback inline (se não houver st.dialog)
            if (st.session_state.edit_id == vid) and (not hasattr(st, "dialog")):
                st.subheader(f"Editar veículo — {(d.get('placa') or '').upper()}")
                current = buscar(conn, vid, cols_present)
                if not current:
                    st.error("Registro não encontrado.")
                else:
                    _render_edit_form(current, cols_present, conn, vid)

            st.markdown("</div>", unsafe_allow_html=True)
