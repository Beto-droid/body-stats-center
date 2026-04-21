"""
Dashboard de Mi Scale — corre con:
    streamlit run gui.py
"""
import asyncio
import threading
from datetime import datetime, timedelta

import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from catalog import CARDIO_TYPES, EXERCISES, FOODS
from database import (delete_cardio_session, delete_food_entry, delete_gym_session,
                      delete_tape_measurement, delete_caliper_measurement,
                      get_all_measurements, get_cardio_sessions, get_daily_averages,
                      get_daily_nutrition, get_exercise_history, get_food_log,
                      get_gym_sessions, get_latest_measurement, init_db,
                      get_tape_measurements, get_caliper_measurements,
                      log_cardio, log_food, log_gym_session,
                      log_tape_measurement, log_caliper_measurement)
from caliper import (jackson_pollock_3_male, jackson_pollock_3_female,
                     jackson_pollock_7, caliper_results,
                     JP3_MALE_SITES, JP3_FEMALE_SITES, JP7_SITES)

# ── Scanner en background ─────────────────────────────────────────────────────
_scanner_thread: threading.Thread | None = None

scanner_status: dict = {
    "state": "idle",
    "device": None,
    "message": "",
}


def _run_scanner():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    import scan as scan_mod

    _orig_find = scan_mod.find_miscale_device
    async def patched_find():
        scanner_status["state"] = "scanning"
        scanner_status["message"] = "Buscando MIBFS..."
        device = await _orig_find()
        if device:
            scanner_status["state"] = "found"
            scanner_status["message"] = f"Encontrado: {getattr(device, 'name', str(device))}"
        return device
    scan_mod.find_miscale_device = patched_find

    _orig_handler = scan_mod.notification_handler
    def patched_handler(char, data):
        from parsing import parse_body_composition_message
        msg = parse_body_composition_message(data)
        scanner_status["state"] = "connected"
        scanner_status["message"] = f"{msg.measurement.weight:.2f} kg {'✅' if msg.stabilized else '⏳'}"
        _orig_handler(char, data)
    scan_mod.notification_handler = patched_handler

    async def run_loop():
        scanner_status["state"] = "scanning"
        scanner_status["message"] = "Iniciando..."
        while True:
            try:
                await scan_mod.connect_and_measure()
            except Exception as e:
                scanner_status["state"] = "error"
                scanner_status["message"] = str(e)
                await asyncio.sleep(5)
            scanner_status["state"] = "scanning"
            scanner_status["message"] = "Reconectando..."

    try:
        loop.run_until_complete(run_loop())
    except Exception as e:
        scanner_status["state"] = "error"
        scanner_status["message"] = str(e)


def ensure_scanner_running():
    global _scanner_thread
    if _scanner_thread is None or not _scanner_thread.is_alive():
        _scanner_thread = threading.Thread(target=_run_scanner, daemon=True, name="ble-scanner")
        _scanner_thread.start()


# ── Helpers de gráficos ───────────────────────────────────────────────────────
DARK_BG = "#1e1e1e"

STAT_LABELS = [
    ("weight_kg",       "⚖️ Weight",      "kg",   "#4FC3F7"),
    ("bmi",             "📊 BMI",          "",     "#CE93D8"),
    ("fat_percent",     "🥩 Body Fat",     "%",    "#EF9A9A"),
    ("muscle_mass_kg",  "💪 Muscle",       "kg",   "#A5D6A7"),
    ("bone_mass_kg",    "🦴 Bone",         "kg",   "#BCAAA4"),
    ("water_percent",   "💧 Water",        "%",    "#80DEEA"),
    ("visceral_fat",    "🫀 Visceral Fat", "",     "#FF8A65"),
    ("bmr_kcal",        "🔥 BMR",          "kcal", "#FFCC80"),
    ("lean_mass_kg",    "🏃 Lean Mass",    "kg",   "#B39DDB"),
    ("protein_percent", "🥛 Protein",      "%",    "#F48FB1"),
]


def make_line_chart(data, key, label, color):
    dates = [r["timestamp"] for r in data if r.get(key) is not None]
    vals  = [r[key]         for r in data if r.get(key) is not None]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=vals, mode="lines+markers", name=label,
                             line=dict(color=color, width=2), marker=dict(size=5)))
    fig.update_layout(paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG, font=dict(color="white"),
                      margin=dict(l=40, r=20, t=30, b=30),
                      xaxis=dict(gridcolor="#333", tickformat="%d/%m"),
                      yaxis=dict(gridcolor="#333", title=label), height=280)
    return fig


def filter_days(data, days):
    if days is None:
        return data
    cutoff = datetime.now() - timedelta(days=days)
    return [r for r in data if datetime.fromisoformat(r["timestamp"]) >= cutoff]


def draw_scale_charts(data, suffix, daily_avg, use_daily):
    tab7, tab30, tabAll, tabComp = st.tabs(["7 días", "30 días", "Todo", "Composición"])
    charts = [
        ("weight_kg",      "Weight (kg)",    "#4FC3F7"),
        ("fat_percent",    "Body Fat (%)",   "#EF9A9A"),
        ("muscle_mass_kg", "Muscle (kg)",    "#A5D6A7"),
        ("bmi",            "BMI",            "#CE93D8"),
        ("water_percent",  "Water (%)",      "#80DEEA"),
        ("lean_mass_kg",   "Lean Mass (kg)", "#B39DDB"),
    ]
    for tab, days, sfx in [(tab7, 7, "w"), (tab30, 30, "m"), (tabAll, None, "a")]:
        with tab:
            src = filter_days(daily_avg if use_daily else data, days)
            if not src:
                st.info("Sin datos para este período.")
            else:
                c1, c2 = st.columns(2)
                for i, (k, lbl, col) in enumerate(charts):
                    with (c1 if i % 2 == 0 else c2):
                        st.plotly_chart(make_line_chart(src, k, lbl, col), key=f"{k}_{sfx}", width="stretch")
    with tabComp:
        src = filter_days(daily_avg if use_daily else data, 30)
        if not src:
            st.info("Sin datos.")
        else:
            c1, c2 = st.columns(2)
            for i, (k, lbl, col) in enumerate([
                ("bone_mass_kg",    "Bone (kg)",      "#BCAAA4"),
                ("visceral_fat",    "Visceral Fat",   "#FF8A65"),
                ("bmr_kcal",        "BMR (kcal/day)", "#FFCC80"),
                ("protein_percent", "Protein (%)",    "#F48FB1"),
            ]):
                with (c1 if i % 2 == 0 else c2):
                    st.plotly_chart(make_line_chart(src, k, lbl, col), key=f"comp_{k}", width="stretch")


# ── App init ──────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Mi Scale Dashboard", page_icon="⚖️", layout="wide")
init_db()
ensure_scanner_running()
st_autorefresh(interval=20_000, key="autorefresh")

import pandas as pd

# ═══════════════════════ SIDEBAR ══════════════════════════════════════════════
with st.sidebar:
    st.markdown("# ⚖️ Mi Scale")
    st.divider()

    # ── Navegación ──
    page = st.radio(
        "Navegación",
        ["⚖️  Balanza", "🏋️  Gym", "🍽️  Nutrición", "📏  Mediciones"],
        label_visibility="collapsed",
    )
    st.divider()

    # ── Estado scanner ──
    st.markdown("**Scanner BLE**")
    alive = _scanner_thread is not None and _scanner_thread.is_alive()
    state = scanner_status["state"]
    msg   = scanner_status["message"]

    if not alive:
        st.error("🔴 Detenido")
        if st.button("▶️ Reiniciar"):
            ensure_scanner_running()
            st.rerun()
    elif state == "scanning":
        st.warning(f"🔍 {msg}")
    elif state == "found":
        st.info(f"📡 {msg}")
    elif state == "connected":
        st.success(f"🟢 {msg}")
    elif state == "error":
        st.error(f"❌ {msg}")
    else:
        st.success("🟢 Corriendo")

    st.divider()
    st.caption("1. Encendé la balanza\n2. Subite y quedate quieto\n3. Esperá que estabilice\n4. Se guarda solo 💾")

# ═══════════════════════ PÁGINA: BALANZA ══════════════════════════════════════
if page == "⚖️  Balanza":
    st.title("⚖️ Balanza")

    all_data  = get_all_measurements()
    daily_avg = get_daily_averages()
    latest    = get_latest_measurement()

    if not latest:
        st.info("Sin mediciones aún. ¡Subite a la balanza!")
    else:
        st.caption(f"🕐 {latest.get('timestamp', '—')}")
        cols = st.columns(5)
        for i, (key, label, unit, color) in enumerate(STAT_LABELS):
            val = latest.get(key)
            display = f"{val:.1f} {unit}".strip() if isinstance(val, float) else (f"{val} {unit}").strip() if val else "—"
            with cols[i % 5]:
                st.metric(label=label, value=display)

    st.divider()
    st.subheader("📈 Historial")
    use_daily = st.radio("Ver", ["Promedio diario", "Todas las mediciones"], horizontal=True) == "Promedio diario"
    draw_scale_charts(all_data, "s", daily_avg, use_daily)

    with st.expander("🗂️ Datos crudos"):
        if all_data:
            df = pd.DataFrame(all_data).drop(columns=["id"], errors="ignore")
            st.dataframe(df.sort_values("timestamp", ascending=False), width="stretch")
        else:
            st.write("Sin datos aún.")

# ═══════════════════════ PÁGINA: GYM ══════════════════════════════════════════
elif page == "🏋️  Gym":
    st.title("🏋️ Gym")

    col_form, col_hist = st.columns([1, 2])

    with col_form:
        st.subheader("➕ Registrar ejercicio")
        with st.form("gym_form", clear_on_submit=True):
            date_gym = st.date_input("Fecha", value=datetime.now())
            all_categories = list(EXERCISES.keys()) + ["✏️ Personalizado"]
            cat = st.selectbox("Categoría", all_categories)
            if cat == "✏️ Personalizado":
                exercise_name = st.text_input("Nombre del ejercicio")
                cat_label = "Personalizado"
            else:
                exercise_name = st.selectbox("Ejercicio", EXERCISES[cat])
                cat_label = cat
            c1, c2, c3 = st.columns(3)
            with c1: sets  = st.number_input("Series", min_value=1, max_value=20,    value=3)
            with c2: reps  = st.number_input("Reps",   min_value=1, max_value=100,   value=10)
            with c3: w_kg  = st.number_input("Peso kg",min_value=0.0,max_value=500.0,value=0.0,step=2.5)
            notes_gym = st.text_input("Notas (opcional)")
            if st.form_submit_button("💾 Guardar ejercicio", use_container_width=True):
                if exercise_name:
                    log_gym_session(str(date_gym), exercise_name, cat_label, int(sets), int(reps), float(w_kg), notes_gym)
                    st.success(f"✅ {exercise_name} guardado!")
                    st.rerun()
                else:
                    st.warning("Escribí el nombre del ejercicio.")

        st.subheader("🏃 Registrar cardio")
        with st.form("cardio_form", clear_on_submit=True):
            date_cardio = st.date_input("Fecha ", value=datetime.now())
            cardio_type = st.selectbox("Tipo", CARDIO_TYPES)
            c1, c2 = st.columns(2)
            with c1: duration = st.number_input("Duración (min)", min_value=1,   max_value=300,   value=30)
            with c2: distance = st.number_input("Distancia (km)", min_value=0.0, max_value=200.0, value=0.0, step=0.1)
            notes_cardio = st.text_input("Notas (opcional) ")
            if st.form_submit_button("💾 Guardar cardio", use_container_width=True):
                log_cardio(str(date_cardio), cardio_type, int(duration), float(distance) or None, notes_cardio)
                st.success("✅ Cardio guardado!")
                st.rerun()

    with col_hist:
        st.subheader("📋 Historial (últimos 30 días)")
        gym_data    = get_gym_sessions(days=30)
        cardio_data = get_cardio_sessions(days=30)

        if gym_data:
            df_gym = pd.DataFrame(gym_data)
            df_show = df_gym[["date","category","exercise","sets","reps","weight_kg","notes"]].copy()
            df_show.columns = ["Fecha","Categoría","Ejercicio","Series","Reps","Peso (kg)","Notas"]
            st.dataframe(df_show, width="stretch", height=260)
            with st.expander("🗑️ Eliminar ejercicio"):
                del_id = st.selectbox("Entrada", [r["id"] for r in gym_data],
                                      format_func=lambda x: f"#{x} — " + next(r["exercise"] for r in gym_data if r["id"]==x))
                if st.button("Eliminar", key="del_gym"):
                    delete_gym_session(del_id); st.rerun()
        else:
            st.info("Sin ejercicios registrados.")

        if cardio_data:
            st.markdown("**Cardio reciente:**")
            df_c = pd.DataFrame(cardio_data)[["date","type","duration_min","distance_km","notes"]]
            df_c.columns = ["Fecha","Tipo","Min","Km","Notas"]
            st.dataframe(df_c, width="stretch", height=150)
            with st.expander("🗑️ Eliminar cardio"):
                del_cid = st.selectbox("Entrada ", [r["id"] for r in cardio_data],
                                       format_func=lambda x: f"#{x} — " + next(r["type"] for r in cardio_data if r["id"]==x))
                if st.button("Eliminar", key="del_cardio"):
                    delete_cardio_session(del_cid); st.rerun()

    if gym_data:
        st.subheader("📈 Progresión por ejercicio")
        df_gym_all    = pd.DataFrame(gym_data)
        exercise_list = sorted(df_gym_all["exercise"].unique())
        sel_ex        = st.selectbox("Ejercicio:", exercise_list)
        hist          = get_exercise_history(sel_ex)
        if hist:
            df_h = pd.DataFrame(hist)
            fig  = go.Figure()
            fig.add_trace(go.Scatter(x=df_h["date"], y=df_h["max_kg"], mode="lines+markers",
                                     name="Peso máx (kg)", line=dict(color="#4FC3F7", width=2), marker=dict(size=6)))
            fig.update_layout(paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG, font=dict(color="white"),
                               margin=dict(l=40,r=20,t=30,b=30), height=260,
                               xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333", title="kg"))
            st.plotly_chart(fig, key="gym_prog", width="stretch")

# ═══════════════════════ PÁGINA: NUTRICIÓN ════════════════════════════════════
elif page == "🍽️  Nutrición":
    st.title("🍽️ Nutrición")

    col_form, col_today = st.columns([1, 2])

    with col_form:
        st.subheader("➕ Registrar comida")
        with st.form("food_form", clear_on_submit=True):
            date_food    = st.date_input("Fecha  ", value=datetime.now())
            food_options = list(FOODS.keys()) + ["✏️ Personalizado"]
            sel_food     = st.selectbox("Alimento", food_options)

            if sel_food == "✏️ Alimento personalizado":
                food_display_name = st.text_input("Nombre")
                c1,c2,c3,c4 = st.columns(4)
                with c1: cal100 = st.number_input("Cal",  min_value=0.0, value=0.0)
                with c2: pro100 = st.number_input("Prot", min_value=0.0, value=0.0)
                with c3: car100 = st.number_input("Carb", min_value=0.0, value=0.0)
                with c4: fat100 = st.number_input("Gras", min_value=0.0, value=0.0)
                macros_per_100 = (cal100, pro100, car100, fat100)
            else:
                macros_per_100    = FOODS[sel_food]
                food_display_name = sel_food
                c, p, ch, f       = macros_per_100
                st.caption(f"Por 100g → {c:.0f} kcal | P:{p}g C:{ch}g G:{f}g")

            qty    = st.number_input("Cantidad (g)", min_value=1.0, max_value=5000.0, value=100.0, step=10.0)
            factor = qty / 100
            cal_f, pro_f, car_f, fat_f = [round(x * factor, 1) for x in macros_per_100]
            st.info(f"**{cal_f} kcal** · P:{pro_f}g · C:{car_f}g · G:{fat_f}g")

            if st.form_submit_button("💾 Guardar", use_container_width=True):
                if food_display_name:
                    log_food(str(date_food), food_display_name, qty, cal_f, pro_f, car_f, fat_f)
                    st.success("✅ Guardado!")
                    st.rerun()
                else:
                    st.warning("Escribí el nombre.")

    with col_today:
        st.subheader("📊 Hoy")
        today_log  = [r for r in get_food_log(days=1) if r["date"] == datetime.now().strftime("%Y-%m-%d")]
        total_cal  = sum(r["calories"]  for r in today_log)
        total_pro  = sum(r["protein_g"] for r in today_log)
        total_car  = sum(r["carbs_g"]   for r in today_log)
        total_fat  = sum(r["fat_g"]     for r in today_log)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔥 Calorías",  f"{total_cal:.0f} kcal")
        c2.metric("🥩 Proteínas", f"{total_pro:.1f} g")
        c3.metric("🍚 Carbos",    f"{total_car:.1f} g")
        c4.metric("🧈 Grasas",    f"{total_fat:.1f} g")

        if today_log:
            df_t = pd.DataFrame(today_log)[["food_name","quantity_g","calories","protein_g","carbs_g","fat_g"]]
            df_t.columns = ["Alimento","g","Kcal","Prot","Carbs","Grasa"]
            st.dataframe(df_t, width="stretch", height=200)
            with st.expander("🗑️ Eliminar"):
                del_fid = st.selectbox("Entrada", [r["id"] for r in today_log],
                                       format_func=lambda x: f"#{x} — " + next(r["food_name"] for r in today_log if r["id"]==x))
                if st.button("Eliminar", key="del_food"):
                    delete_food_entry(del_fid); st.rerun()

    st.subheader("📈 Macros — últimos 30 días")
    daily_nut = get_daily_nutrition(days=30)
    if daily_nut:
        df_nut = pd.DataFrame(daily_nut)
        fig_nut = go.Figure()
        fig_nut.add_trace(go.Bar(x=df_nut["date"], y=df_nut["protein_g"], name="Proteínas",     marker_color="#EF9A9A"))
        fig_nut.add_trace(go.Bar(x=df_nut["date"], y=df_nut["carbs_g"],   name="Carbohidratos", marker_color="#FFCC80"))
        fig_nut.add_trace(go.Bar(x=df_nut["date"], y=df_nut["fat_g"],     name="Grasas",        marker_color="#A5D6A7"))
        fig_nut.update_layout(barmode="stack", paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG,
                              font=dict(color="white"), height=300, margin=dict(l=40,r=20,t=30,b=30),
                              xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333", title="gramos"))
        st.plotly_chart(fig_nut, key="macros_bar", width="stretch")

        fig_cal = go.Figure()
        fig_cal.add_trace(go.Scatter(x=df_nut["date"], y=df_nut["calories"], mode="lines+markers",
                                     line=dict(color="#4FC3F7", width=2), marker=dict(size=5), name="Calorías"))
        fig_cal.update_layout(paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG, font=dict(color="white"),
                              height=220, margin=dict(l=40,r=20,t=10,b=30),
                              xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333", title="kcal"))
        st.plotly_chart(fig_cal, key="cal_line", width="stretch")
    else:
        st.info("Registrá comidas para ver tus macros históricos.")

# ═══════════════════════ PÁGINA: MEDICIONES ═══════════════════════════════════
elif page == "📏  Mediciones":
    st.title("📏 Mediciones Corporales")

    from user_config import AGE, SEX

    # Peso de la balanza (último registrado)
    latest_scale = get_latest_measurement()
    scale_weight = latest_scale["weight_kg"] if latest_scale else None

    tab_tape, tab_caliper, tab_hist = st.tabs(["📐 Cinta métrica", "🔵 Calibrador (caliper)", "📈 Historial"])

    # ── TAB: CINTA MÉTRICA ────────────────────────────────────────────────────
    with tab_tape:
        col_form, col_prev = st.columns([1, 1])

        with col_form:
            st.subheader("➕ Registrar medidas")
            with st.form("tape_form", clear_on_submit=True):
                date_tape = st.date_input("Fecha", value=datetime.now())
                st.markdown("*Todas en centímetros. Dejá en 0 las que no mediste.*")

                c1, c2 = st.columns(2)
                with c1:
                    neck       = st.number_input("Cuello",          min_value=0.0, max_value=100.0, value=0.0, step=0.5)
                    chest      = st.number_input("Pecho",           min_value=0.0, max_value=200.0, value=0.0, step=0.5)
                    waist      = st.number_input("Cintura",         min_value=0.0, max_value=200.0, value=0.0, step=0.5)
                    hips       = st.number_input("Caderas",         min_value=0.0, max_value=200.0, value=0.0, step=0.5)
                    left_calf  = st.number_input("Pantorrilla izq", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
                with c2:
                    left_bicep  = st.number_input("Bíceps izq",    min_value=0.0, max_value=100.0, value=0.0, step=0.5)
                    right_bicep = st.number_input("Bíceps der",    min_value=0.0, max_value=100.0, value=0.0, step=0.5)
                    left_thigh  = st.number_input("Muslo izq",     min_value=0.0, max_value=100.0, value=0.0, step=0.5)
                    right_thigh = st.number_input("Muslo der",     min_value=0.0, max_value=100.0, value=0.0, step=0.5)
                    right_calf  = st.number_input("Pantorrilla der",min_value=0.0, max_value=100.0, value=0.0, step=0.5)

                notes_tape = st.text_input("Notas (opcional)")

                if st.form_submit_button("💾 Guardar medidas", use_container_width=True):
                    def _v(x): return x if x > 0 else None
                    log_tape_measurement(
                        str(date_tape), _v(neck), _v(chest), _v(waist), _v(hips),
                        _v(left_bicep), _v(right_bicep), _v(left_thigh), _v(right_thigh),
                        _v(left_calf), _v(right_calf), notes_tape
                    )
                    st.success("✅ Medidas guardadas!")
                    st.rerun()

        with col_prev:
            st.subheader("📋 Últimas medidas")
            tape_data = get_tape_measurements(days=90)
            if tape_data:
                latest_tape = tape_data[0]
                fields = [
                    ("Cuello",          "neck_cm"),
                    ("Pecho",           "chest_cm"),
                    ("Cintura",         "waist_cm"),
                    ("Caderas",         "hips_cm"),
                    ("Bíceps izq",      "left_bicep_cm"),
                    ("Bíceps der",      "right_bicep_cm"),
                    ("Muslo izq",       "left_thigh_cm"),
                    ("Muslo der",       "right_thigh_cm"),
                    ("Pantorrilla izq", "left_calf_cm"),
                    ("Pantorrilla der", "right_calf_cm"),
                ]
                st.caption(f"🕐 {latest_tape['date']}")
                r1, r2 = st.columns(2)
                for i, (label, key) in enumerate(fields):
                    val = latest_tape.get(key)
                    with (r1 if i % 2 == 0 else r2):
                        st.metric(label, f"{val:.1f} cm" if val else "—")

                # Evolución de cintura
                if len(tape_data) > 1:
                    st.markdown("**📈 Evolución de cintura:**")
                    waist_data = [{"timestamp": r["date"], "waist_cm": r["waist_cm"]} for r in reversed(tape_data) if r.get("waist_cm")]
                    if waist_data:
                        st.plotly_chart(make_line_chart(waist_data, "waist_cm", "Cintura (cm)", "#EF9A9A"),
                                        key="waist_chart", width="stretch")

                with st.expander("🗑️ Eliminar entrada"):
                    del_tid = st.selectbox("Fecha", [r["id"] for r in tape_data],
                                           format_func=lambda x: next(r["date"] for r in tape_data if r["id"]==x))
                    if st.button("Eliminar", key="del_tape"):
                        delete_tape_measurement(del_tid); st.rerun()
            else:
                st.info("Sin medidas aún.")

    # ── TAB: CALIBRADOR ───────────────────────────────────────────────────────
    with tab_caliper:
        col_cal, col_res = st.columns([1, 1])

        with col_cal:
            st.subheader("🔵 Método de medición")

            if scale_weight:
                st.success(f"⚖️ Usando peso de la balanza: **{scale_weight:.2f} kg** (última medición)")
            else:
                st.warning("No hay peso en la balanza. Ingresalo manualmente.")

            method = st.selectbox("Fórmula", [
                "Jackson-Pollock 3 pliegues",
                "Jackson-Pollock 7 pliegues",
            ])

            with st.form("caliper_form", clear_on_submit=True):
                date_cal = st.date_input("Fecha  ", value=datetime.now())

                weight_input = st.number_input(
                    "Peso (kg)", min_value=30.0, max_value=250.0,
                    value=float(scale_weight) if scale_weight else 80.0, step=0.1,
                    help="Se carga automáticamente de la balanza. Podés modificarlo."
                )
                age_input = st.number_input("Edad", min_value=10, max_value=99, value=AGE)
                sex_input = st.selectbox("Sexo", ["male", "female"], index=0 if SEX=="male" else 1,
                                         format_func=lambda x: "Masculino" if x=="male" else "Femenino")

                st.markdown("**Pliegues (mm) — medí 3 veces y usá el promedio:**")

                if method == "Jackson-Pollock 3 pliegues":
                    sites_def = JP3_MALE_SITES if sex_input == "male" else JP3_FEMALE_SITES
                    values = []
                    for label, _ in sites_def:
                        values.append(st.number_input(label, min_value=0.0, max_value=100.0, value=0.0, step=0.5, key=f"cal_{label}"))
                    site_vals = values + [None] * 4  # pad to 7
                else:
                    values = []
                    for label, _ in JP7_SITES:
                        values.append(st.number_input(label, min_value=0.0, max_value=100.0, value=0.0, step=0.5, key=f"cal7_{label}"))
                    site_vals = values

                notes_cal = st.text_input("Notas (opcional)  ")

                submitted = st.form_submit_button("📊 Calcular y guardar", use_container_width=True)

            if submitted:
                # Calcular fat%
                try:
                    if method == "Jackson-Pollock 3 pliegues":
                        if sex_input == "male":
                            fat_pct = jackson_pollock_3_male(values[0], values[1], values[2], int(age_input))
                        else:
                            fat_pct = jackson_pollock_3_female(values[0], values[1], values[2], int(age_input))
                    else:
                        fat_pct = jackson_pollock_7(values[0], values[1], values[2], values[3],
                                                     values[4], values[5], values[6], int(age_input), sex_input)

                    fat_mass, lean_mass = caliper_results(fat_pct, weight_input)

                    log_caliper_measurement(
                        str(date_cal), method, weight_input, int(age_input), sex_input,
                        site_vals, fat_pct, lean_mass, fat_mass, notes_cal
                    )

                    # Mostrar resultado prominente
                    st.success("✅ Guardado!")
                    with col_res:
                        st.subheader("📊 Resultado")
                        st.metric("🥩 % Grasa corporal", f"{fat_pct:.1f} %")
                        st.metric("🏃 Masa magra",        f"{lean_mass:.2f} kg")
                        st.metric("💧 Masa grasa",         f"{fat_mass:.2f} kg")
                        st.metric("⚖️ Peso usado",         f"{weight_input:.2f} kg")

                        # Clasificación
                        if sex_input == "male":
                            if fat_pct < 6:     cat = ("Esencial", "🔵")
                            elif fat_pct < 14:  cat = ("Atlético", "🟢")
                            elif fat_pct < 18:  cat = ("En forma", "🟢")
                            elif fat_pct < 25:  cat = ("Normal",   "🟡")
                            else:               cat = ("Obesidad",  "🔴")
                        else:
                            if fat_pct < 14:    cat = ("Esencial", "🔵")
                            elif fat_pct < 21:  cat = ("Atlético", "🟢")
                            elif fat_pct < 25:  cat = ("En forma", "🟢")
                            elif fat_pct < 32:  cat = ("Normal",   "🟡")
                            else:               cat = ("Obesidad",  "🔴")

                        st.info(f"{cat[1]} Categoría: **{cat[0]}**")

                    st.rerun()

                except Exception as e:
                    st.error(f"Error en el cálculo: {e}")

        # Mostrar último resultado si no se acaba de calcular
        with col_res:
            cal_data = get_caliper_measurements(days=90)
            if cal_data and not submitted:
                st.subheader("📊 Último resultado")
                last = cal_data[0]
                st.caption(f"🕐 {last['date']} — {last['method']}")
                st.metric("🥩 % Grasa corporal", f"{last['fat_percent']:.1f} %")
                st.metric("🏃 Masa magra",        f"{last['lean_mass_kg']:.2f} kg")
                st.metric("💧 Masa grasa",         f"{last['fat_mass_kg']:.2f} kg")
                st.metric("⚖️ Peso",               f"{last['weight_kg']:.2f} kg")

    # ── TAB: HISTORIAL ────────────────────────────────────────────────────────
    with tab_hist:
        cal_data  = get_caliper_measurements(days=180)
        tape_data = get_tape_measurements(days=180)

        if cal_data:
            st.subheader("🔵 Evolución % grasa (caliper)")
            chart_data = [{"timestamp": r["date"], "fat_percent": r["fat_percent"],
                           "lean_mass_kg": r["lean_mass_kg"]} for r in reversed(cal_data)]
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(make_line_chart(chart_data, "fat_percent",  "% Grasa",      "#EF9A9A"), key="cal_fat",  width="stretch")
            with c2:
                st.plotly_chart(make_line_chart(chart_data, "lean_mass_kg", "Masa magra kg","#A5D6A7"), key="cal_lean", width="stretch")

            df_cal = pd.DataFrame(cal_data)[["date","method","weight_kg","fat_percent","lean_mass_kg","fat_mass_kg"]]
            df_cal.columns = ["Fecha","Método","Peso (kg)","Grasa (%)","Magra (kg)","Grasa (kg)"]
            st.dataframe(df_cal, width="stretch")
            with st.expander("🗑️ Eliminar entrada caliper"):
                del_cid2 = st.selectbox("Fecha  ", [r["id"] for r in cal_data],
                                         format_func=lambda x: next(r["date"] for r in cal_data if r["id"]==x))
                if st.button("Eliminar", key="del_cal2"):
                    delete_caliper_measurement(del_cid2); st.rerun()

        if tape_data:
            st.subheader("📐 Evolución medidas (cinta)")
            tape_chart = [{"timestamp": r["date"], **{k: r[k] for k in ["chest_cm","waist_cm","hips_cm","left_bicep_cm"]}}
                          for r in reversed(tape_data)]
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(make_line_chart(tape_chart, "waist_cm",      "Cintura (cm)", "#EF9A9A"), key="t_waist",  width="stretch")
                st.plotly_chart(make_line_chart(tape_chart, "left_bicep_cm", "Bíceps (cm)",  "#4FC3F7"), key="t_bicep",  width="stretch")
            with c2:
                st.plotly_chart(make_line_chart(tape_chart, "chest_cm",      "Pecho (cm)",   "#A5D6A7"), key="t_chest",  width="stretch")
                st.plotly_chart(make_line_chart(tape_chart, "hips_cm",       "Caderas (cm)", "#FFCC80"), key="t_hips",   width="stretch")

        if not cal_data and not tape_data:
            st.info("Sin mediciones registradas aún.")

