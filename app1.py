import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(
    page_title="Suite de Calculo Electrico y Dimensionamiento Normativo",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS Blanco Cientifico / Ingenieria
st.markdown("""
<style>
    .stApp {
        background-color: #FFFFFF;
        color: #0F172A;
    }
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
    div[data-testid="stMetric"] {
        background-color: #F8FAFC;
        border: 1px solid #CBD5E1;
        padding: 12px 16px;
        border-radius: 4px;
    }
    div[data-testid="stMetricLabel"] {
        color: #475569;
        font-family: 'Courier New', monospace;
        font-size: 0.78rem;
        font-weight: 600;
    }
    div[data-testid="stMetricValue"] {
        color: #0F172A;
        font-family: 'Courier New', monospace;
        font-size: 1.3rem;
        font-weight: 700;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #FFFFFF;
        border-bottom: 1px solid #CBD5E1;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-bottom: none;
        color: #475569;
        padding: 8px 20px;
        font-family: monospace;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF;
        color: #1D4ED8;
        border-top: 2px solid #1D4ED8;
        font-weight: 600;
    }
    h1, h2, h3, h4 {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        letter-spacing: -0.02em;
        color: #0F172A;
    }
</style>
""", unsafe_allow_html=True)

st.title("CALCULADORA DE INGENIERIA ELECTRICA: CONDUCTORES, CAIDA DE TENSION Y PROTECCIONES")
st.caption("Dimensionamiento de alimentadores y circuitos segun criterios de capacidad de transporte termico, regulacion de tension y coordinacion de protecciones (Normativa RIC SEC / IEC 60364).")

# --- BASE DE DATOS NORMATIVA DE CONDUCTORES Y PROTECCIONES ---

# Secciones normalizadas milimetricas (mm2) y capacidades base de corriente (A) a 30°C en ducto (Método B1/B2)
# Incluye PVC (70°C - ej. THHN/THWN-2 o EVA en régimen de 70°C) y XLPE/EPR (90°C - ej. RV-K / RZ1-K)
SECCIONES_MM2 = [1.5, 2.5, 4.0, 6.0, 10.0, 16.0, 25.0, 35.0, 50.0, 70.0, 95.0, 120.0, 150.0, 185.0, 240.0]

TABLA_AMPACIDAD = {
    "Cobre_70C":  [15.5, 21.0, 28.0, 36.0, 50.0, 68.0, 89.0, 110.0, 134.0, 171.0, 207.0, 239.0, 272.0, 310.0, 364.0],
    "Cobre_90C":  [19.5, 27.0, 36.0, 46.0, 63.0, 85.0, 112.0, 138.0, 168.0, 213.0, 258.0, 299.0, 344.0, 392.0, 461.0],
    "Aluminio_70C": [12.0, 16.5, 22.0, 28.0, 39.0, 53.0, 70.0, 86.0, 104.0, 133.0, 161.0, 186.0, 212.0, 241.0, 284.0],
    "Aluminio_90C": [15.0, 21.0, 28.0, 36.0, 49.0, 66.0, 83.0, 103.0, 125.0, 160.0, 194.0, 226.0, 260.0, 297.0, 350.0]
}

# Calibres comerciales de interruptores termomagneticos (MCB / MCCB) en Amperes
CALIBRES_ITM = [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630]

# Factores de correccion por temperatura ambiente (base 30°C)
def factor_temperatura(temp_amb, temp_aislacion):
    t_ref = 30.0
    t_max = 70.0 if "70" in temp_aislacion else 90.0
    if temp_amb >= t_max:
        return 0.1
    return np.sqrt((t_max - temp_amb) / (t_max - t_ref))

# Factores de correccion por agrupamiento de circuitos en el mismo ducto o bandeja
FACTORES_AGRUPAMIENTO = {
    1: 1.00,
    2: 0.80,
    3: 0.70,
    4: 0.65,
    5: 0.60,
    6: 0.57,
    7: 0.54,
    8: 0.52,
    9: 0.50
}

# --- FUNCIONES DE CALCULO ELECTRICO ---

def calcular_resistividad_operacion(material, temp_aislacion):
    """
    Calcula la resistividad electrica rho (Ohm * mm2 / m) corregida a la temperatura
    maxima de servicio del conductor para un diseño conservador.
    """
    rho_20 = 0.017241 if material == "Cobre" else 0.028264
    alpha_20 = 0.00393 if material == "Cobre" else 0.00403
    t_op = 70.0 if "70" in temp_aislacion else 90.0
    return rho_20 * (1.0 + alpha_20 * (t_op - 20.0))

def calcular_corriente_empleo(potencia_w, tension_v, cos_phi, rendimiento, sistema, factor_seguridad):
    """Calcula la corriente nominal de carga I_B y la corriente de diseño I_d."""
    p_absor = potencia_w / rendimiento
    if sistema == "Monofasico (220 V / Fase-Neutro)":
        ib = p_absor / (tension_v * cos_phi)
    else:
        ib = p_absor / (np.sqrt(3.0) * tension_v * cos_phi)
    id_diseno = ib * factor_seguridad
    return ib, id_diseno, p_absor

def calcular_caida_tension(seccion, longitud_m, corriente_a, tension_v, cos_phi, rho, reactancia_km, sistema):
    """
    Calcula la caida de tension exacta considerando resistencia activa R y reactancia inductiva X:
    dV = k * I * L * (R*cos(phi) + X*sin(phi))
    """
    sin_phi = np.sqrt(max(0.0, 1.0 - cos_phi**2))
    k_sist = 2.0 if "Monofasico" in sistema else np.sqrt(3.0)
    
    r_ohm_m = rho / seccion
    x_ohm_m = reactancia_km / 1000.0
    
    dv_volt = k_sist * corriente_a * longitud_m * (r_ohm_m * cos_phi + x_ohm_m * sin_phi)
    dv_pct = (dv_volt / tension_v) * 100.0
    
    # Perdida de potencia por efecto Joule en los conductores (W)
    n_cond_activos = 2.0 if "Monofasico" in sistema else 3.0
    p_joule_w = n_cond_activos * (corriente_a**2) * r_ohm_m * longitud_m
    
    return dv_volt, dv_pct, p_joule_w

def seleccionar_itm(ib_diseno):
    """Selecciona el calibre comercial inmediatamente superior a la corriente de diseño."""
    for cal in CALIBRES_ITM:
        if cal >= ib_diseno:
            return cal
    return CALIBRES_ITM[-1]

# --- PANEL LATERAL DE PARAMETROS DE ENTRADA ---
st.sidebar.header("PARAMETROS DEL CIRCUITO")

id_circuito = st.sidebar.text_input("Identificador de Circuito / Alimentador", value="ALIM-BOMBA-01")

sistema = st.sidebar.selectbox(
    "Configuracion del Sistema",
    ["Trifasico (380 V / 400 V)", "Monofasico (220 V / Fase-Neutro)"]
)

tension_def = 380.0 if "Trifasico" in sistema else 220.0
tension_v = st.sidebar.number_input("Tension Nominal de Servicio [V]", min_value=110.0, max_value=1000.0, value=tension_def, step=10.0)

tipo_carga = st.sidebar.selectbox(
    "Naturaleza de la Carga",
    ["Motor / Equipo Industrial (Factor 1.25)", "Alimentador General / Distribucion (Factor 1.00)", "Iluminacion / Calefaccion (Factor 1.00)"]
)
factor_seg = 1.25 if "Motor" in tipo_carga else 1.00

unidad_pot = st.sidebar.radio("Modo de Ingreso de Carga", ["Potencia Activa [kW]", "Potencia Mecanica [HP]", "Corriente Directa [A]"])

if unidad_pot == "Potencia Activa [kW]":
    kw_in = st.sidebar.number_input("Potencia Nominal [kW]", min_value=0.1, max_value=500.0, value=15.0, step=0.5)
    potencia_w = kw_in * 1000.0
elif unidad_pot == "Potencia Mecanica [HP]":
    hp_in = st.sidebar.number_input("Potencia Mecanica [HP]", min_value=0.25, max_value=600.0, value=20.0, step=0.5)
    potencia_w = hp_in * 745.7
else:
    i_directa = st.sidebar.number_input("Corriente Nominal Medida [A]", min_value=1.0, max_value=600.0, value=30.0, step=1.0)

cos_phi = st.sidebar.slider("Factor de Potencia (cos phi)", min_value=0.50, max_value=1.00, value=0.85, step=0.01)
rendimiento = st.sidebar.slider("Rendimiento del Equipo (eta)", min_value=0.60, max_value=1.00, value=0.92 if "Motor" in tipo_carga else 1.00, step=0.01)

st.sidebar.subheader("Trazado y Condiciones Ambientales")
longitud_m = st.sidebar.number_input("Longitud Simple de la Linea (L) [m]", min_value=1.0, max_value=2000.0, value=65.0, step=5.0)
dv_max_pct = st.sidebar.selectbox("Limite Normativo de Caida de Tension [%]", [3.0, 5.0, 2.0, 1.5], index=0, help="Segun RIC N°03 / N°04: 3% maximo en alimentadores o circuitos individuales, 5% total acumulado.")

material = st.sidebar.selectbox("Material del Conductor", ["Cobre", "Aluminio"])
temp_aislacion = st.sidebar.selectbox("Aislacion y Temperatura de Servicio", ["XLPE / EPR / RZ1-K (90°C)", "PVC / THHN / EVA (70°C)"])
temp_amb = st.sidebar.slider("Temperatura Ambiente de Diseño [°C]", min_value=10, max_value=60, value=35, step=5)
n_agrup = st.sidebar.selectbox("Circuitos Agrupados en el Mismo Ducto/Bandeja", list(FACTORES_AGRUPAMIENTO.keys()), index=0)
curva_itm = st.sidebar.selectbox("Curva de Disparo Proteccion Termomagnetica", ["Curva C (Cargas Generales / Mixtas: 5-10 In)", "Curva D (Motores / Alta Insercion: 10-20 In)", "Curva B (Lineas Largas / Resistivas: 3-5 In)"])

# --- MOTOR DE CALCULO Y EVALUACION DE TABLA COMPLETA ---
if unidad_pot == "Corriente Directa [A]":
    ib = i_directa
    id_diseno = ib * factor_seg
    k_pot = np.sqrt(3.0) if "Trifasico" in sistema else 1.0
    p_absor = k_pot * tension_v * ib * cos_phi
    potencia_w = p_absor * rendimiento
else:
    ib, id_diseno, p_absor = calcular_corriente_empleo(potencia_w, tension_v, cos_phi, rendimiento, sistema, factor_seg)

in_itm = seleccionar_itm(id_diseno)

f_t = factor_temperatura(temp_amb, temp_aislacion)
f_g = FACTORES_AGRUPAMIENTO[n_agrup]
f_total = f_t * f_g

clave_tabla = f"{material}_{'90C' if '90' in temp_aislacion else '70C'}"
ampacidades_base = TABLA_AMPACIDAD[clave_tabla]
rho_op = calcular_resistividad_operacion(material, temp_aislacion)
reactancia_km = 0.08  # Reactancia tipica de cables baja tension en ducto (Ohm/km)

registros_secciones = []
for idx, s_mm2 in enumerate(SECCIONES_MM2):
    iz_base = ampacidades_base[idx]
    iz_corr = iz_base * f_total
    dv_v, dv_pct, p_loss = calcular_caida_tension(s_mm2, longitud_m, ib, tension_v, cos_phi, rho_op, reactancia_km, sistema)
    
    # Condicion 1: Coordinacion termica y proteccion (I_d <= I_n <= I_Z')
    cumple_termico = (iz_corr >= in_itm) and (iz_corr >= id_diseno)
    # Condicion 2: Regulacion de tension (dV% <= dV_max%)
    cumple_tension = (dv_pct <= dv_max_pct)
    cumple_global = cumple_termico and cumple_tension
    
    registros_secciones.append({
        "Seccion [mm2]": s_mm2,
        "I_Z Base (30°C) [A]": iz_base,
        "I_Z' Corregida [A]": iz_corr,
        "Caida Tension [V]": dv_v,
        "Caida Tension [%]": dv_pct,
        "Perdida Joule [W]": p_loss,
        "Cumple Termico (I_Z' >= I_n)": "SI" if cumple_termico else "NO",
        "Cumple Reg. Tension": "SI" if cumple_tension else "NO",
        "Estado Normativo": "APROBADO" if cumple_global else "RECHAZADO"
    })

df_secciones = pd.DataFrame(registros_secciones)

# Identificar seccion minima por criterio termico, por caida de tension y definitiva
aprobados_term = df_secciones[df_secciones["Cumple Termico (I_Z' >= I_n)"] == "SI"]
s_min_termica = aprobados_term.iloc[0]["Seccion [mm2]"] if not aprobados_term.empty else SECCIONES_MM2[-1]

aprobados_tens = df_secciones[df_secciones["Cumple Reg. Tension"] == "SI"]
s_min_tension = aprobados_tens.iloc[0]["Seccion [mm2]"] if not aprobados_tens.empty else SECCIONES_MM2[-1]

aprobados_global = df_secciones[df_secciones["Estado Normativo"] == "APROBADO"]
if not aprobados_global.empty:
    fila_optima = aprobados_global.iloc[0]
    estado_proyecto = "CONFORME A NORMA"
else:
    fila_optima = df_secciones.iloc[-1]
    estado_proyecto = "EXCEDE CAPACIDAD UNIPOLAR (USAR CONDUCTORES EN PARALELO)"

s_optima = fila_optima["Seccion [mm2]"]
iz_optima = fila_optima["I_Z' Corregida [A]"]
dv_v_opt = fila_optima["Caida Tension [V]"]
dv_pct_opt = fila_optima["Caida Tension [%]"]
p_loss_opt = fila_optima["Perdida Joule [W]"]

# Plantilla comun de Plotly para Fondo Blanco Cientifico
LIGHT_LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    font=dict(family="Courier New, monospace", color="#0F172A", size=12),
    xaxis=dict(gridcolor="#E2E8F0", zerolinecolor="#94A3B8", showline=True, linecolor="#0F172A", mirror=True, ticks="outside"),
    yaxis=dict(gridcolor="#E2E8F0", zerolinecolor="#94A3B8", showline=True, linecolor="#0F172A", mirror=True, ticks="outside"),
    margin=dict(l=55, r=25, t=45, b=45)
)

# --- PESTAÑAS DE INGENIERIA ---
tab1, tab2, tab3 = st.tabs([
    "01 // RESULTADOS DE DIMENSIONAMIENTO Y CURVAS",
    "02 // COORDINACION DE PROTECCIONES Y CORTOCIRCUITO",
    "03 // ADQUISICION DE DATOS Y MEMORIA DE CALCULO"
])

# ==============================================================================
# TAB 1: RESULTADOS DE DIMENSIONAMIENTO Y GRAFICAS TECNICAS
# ==============================================================================
with tab1:
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("CORRIENTE NOMINAL (I_B)", f"{ib:.2f} A")
    m2.metric("PROTECCION SELECCIONADA (I_n)", f"{in_itm} A")
    m3.metric("SECCION RECOMENDADA", f"{s_optima} mm²")
    m4.metric("AMPACIDAD CORREGIDA (I_Z')", f"{iz_optima:.1f} A")
    m5.metric("CAIDA DE TENSION (dV%)", f"{dv_pct_opt:.2f} %")

    st.markdown(f"**Estado del Dimensionamiento (`{id_circuito}`):** `{estado_proyecto}` | **Criterio Dominante:** "
                f"`{'CAIDA DE TENSION' if s_min_tension > s_min_termica else 'CAPACIDAD TERMICA / PROTECCION'}` "
                f"(Seccion por corriente: `{s_min_termica} mm²` vs. Seccion por tension: `{s_min_tension} mm²`).")

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        # Curva de Caida de Tension en funcion de la distancia para la seccion seleccionada y vecinas
        dist_arr = np.linspace(1.0, max(longitud_m * 1.6, 50.0), 150)
        fig_dv = go.Figure()

        idx_opt = SECCIONES_MM2.index(s_optima)
        indices_plot = sorted(list(set([max(0, idx_opt - 1), idx_opt, min(len(SECCIONES_MM2) - 1, idx_opt + 1)])))
        colores_curvas = ["#94A3B8", "#1D4ED8", "#059669"]

        for c_i, s_idx in enumerate(indices_plot):
            sec_eval = SECCIONES_MM2[s_idx]
            _, dv_arr_pct, _ = calcular_caida_tension(sec_eval, dist_arr, ib, tension_v, cos_phi, rho_op, reactancia_km, sistema)
            es_opt = (sec_eval == s_optima)
            fig_dv.add_trace(go.Scatter(
                x=dist_arr,
                y=dv_arr_pct,
                mode="lines",
                line=dict(color="#1D4ED8" if es_opt else ("#DC2626" if sec_eval < s_optima else "#059669"), width=2.8 if es_opt else 1.5, dash="solid" if es_opt else "dot"),
                name=f"{sec_eval} mm² {'(Seleccionada)' if es_opt else ''}"
            ))

        # Linea horizontal de limite normativo
        fig_dv.add_hline(y=dv_max_pct, line_dash="dash", line_color="#DC2626", annotation_text=f"Limite Normativo ({dv_max_pct}%)", annotation_position="top left")
        # Punto de operacion del proyecto
        fig_dv.add_trace(go.Scatter(
            x=[longitud_m],
            y=[dv_pct_opt],
            mode="markers",
            marker=dict(size=10, color="#1D4ED8", line=dict(width=2, color="#0F172A")),
            name="Punto de Operacion"
        ))

        fig_dv.update_layout(**LIGHT_LAYOUT)
        fig_dv.update_layout(
            title="Perfil de Caida de Tension Porcentual vs. Longitud de Linea",
            xaxis_title="Longitud Simple de Linea L [m]",
            yaxis_title="Caida de Tension dV [%]",
            height=420,
            legend=dict(x=0.02, y=0.98, bgcolor="rgba(255,255,255,0.9)", bordercolor="#CBD5E1", borderwidth=1)
        )
        st.plotly_chart(fig_dv, use_container_width=True)

    with col_g2:
        # Comparativa de Caida de Tension y Ampacidad por Seccion Comercial
        df_sub = df_secciones.iloc[max(0, idx_opt - 3):min(len(SECCIONES_MM2), idx_opt + 4)]
        fig_sec = go.Figure()
        
        colores_bar = ["#1D4ED8" if s == s_optima else ("#CBD5E1" if est == "RECHAZADO" else "#93C5FD") 
                       for s, est in zip(df_sub["Seccion [mm2]"], df_sub["Estado Normativo"])]

        fig_sec.add_trace(go.Bar(
            x=[f"{s} mm²" for s in df_sub["Seccion [mm2]"]],
            y=df_sub["I_Z' Corregida [A]"],
            marker_color=colores_bar,
            marker_line_color="#0F172A",
            marker_line_width=1.2,
            name="Ampacidad Corregida I_Z' [A]"
        ))

        fig_sec.add_hline(y=in_itm, line_dash="dash", line_color="#DC2626", annotation_text=f"Proteccion I_n = {in_itm} A", annotation_position="top left")
        fig_sec.add_hline(y=ib, line_dash="dot", line_color="#0F172A", annotation_text=f"Corriente Carga I_B = {ib:.1f} A", annotation_position="bottom right")

        fig_sec.update_layout(**LIGHT_LAYOUT)
        fig_sec.update_layout(
            title="Verificacion Termica: Ampacidad Corregida (I_Z') vs. Proteccion (I_n)",
            xaxis_title="Seccion Nominal del Conductor [mm²]",
            yaxis_title="Corriente Admisible [A]",
            height=420,
            showlegend=False
        )
        st.plotly_chart(fig_sec, use_container_width=True)

    st.markdown("#### Matriz Evaluativa de Secciones Normalizadas")
    st.dataframe(
        df_secciones.style.format({
            "Seccion [mm2]": "{:.1f}",
            "I_Z Base (30°C) [A]": "{:.1f}",
            "I_Z' Corregida [A]": "{:.1f}",
            "Caida Tension [V]": "{:.2f}",
            "Caida Tension [%]": "{:.2f}",
            "Perdida Joule [W]": "{:.1f}"
        }),
        use_container_width=True,
        hide_index=True,
        height=300
    )

# ==============================================================================
# TAB 2: COORDINACION DE PROTECCIONES Y VERIFICACION DE CORTOCIRCUITO
# ==============================================================================
with tab2:
    col_p1, col_p2 = st.columns([1.1, 1.2])

    with col_p1:
        st.subheader("Verificacion de Reglas de Coordinacion Sobrecarga")
        st.latex(r"I_B \le I_n \le I_Z' \quad \text{y} \quad I_2 \le 1.45 \cdot I_Z'")

        # En interruptores termomagneticos IEC 60898 / 60947-2, la corriente convencional de disparo I_2 = 1.45 * I_n (o 1.30 * I_n)
        i2_disparo = 1.45 * in_itm
        limite_termico_cable = 1.45 * iz_optima
        cumple_coord = (ib <= in_itm) and (in_itm <= iz_optima) and (i2_disparo <= limite_termico_cable)

        df_coord = pd.DataFrame([
            {"Parametro": "Corriente de Empleo del Circuito (I_B)", "Valor [A]": f"{ib:.2f}", "Criterio": "Carga Nominal"},
            {"Parametro": "Corriente de Diseño con Factor de Servicio (I_d)", "Valor [A]": f"{id_diseno:.2f}", "Criterio": f"Factor = {factor_seg:.2f}"},
            {"Parametro": "Corriente Nominal de la Proteccion (I_n)", "Valor [A]": f"{in_itm:.2f}", "Criterio": f"I_n >= I_d ({'OK' if in_itm >= id_diseno else 'FALLA'})"},
            {"Parametro": "Capacidad de Transporte Corregida del Cable (I_Z')", "Valor [A]": f"{iz_optima:.2f}", "Criterio": f"I_Z' >= I_n ({'OK' if iz_optima >= in_itm else 'FALLA'})"},
            {"Parametro": "Corriente de Disparo Efectivo (I_2 = 1.45 I_n)", "Valor [A]": f"{i2_disparo:.2f}", "Criterio": f"I_2 <= 1.45 I_Z' ({limite_termico_cable:.1f} A)"}
        ])
        st.dataframe(df_coord, use_container_width=True, hide_index=True)

        st.subheader("Esfuerzo Termico de Cortocircuito (Ecuacion Adiabatica)")
        st.latex(r"I_{cc,\max} = \frac{k \cdot S}{\sqrt{t_{disparo}}}")
        t_disparo = st.slider("Tiempo de Despeje de Falla por Cortocircuito (t) [s]", min_value=0.01, max_value=1.00, value=0.10, step=0.01)
        # Constante k de calentamiento adiabatico (Cobre XLPE=143, Cobre PVC=115, Aluminio XLPE=94, Aluminio PVC=76)
        if material == "Cobre":
            k_adiab = 143.0 if "90" in temp_aislacion else 115.0
        else:
            k_adiab = 94.0 if "90" in temp_aislacion else 76.0

        icc_soportada_ka = (k_adiab * s_optima / np.sqrt(t_disparo)) / 1000.0
        st.metric("CORRIENTE DE CORTOCIRCUITO MAXIMA SOPORTADA POR EL CABLE", f"{icc_soportada_ka:.2f} kA", help=f"Calculado con constante k = {k_adiab} para t = {t_disparo} s.")

    with col_p2:
        # Grafica de escalonamiento de corrientes de coordinacion
        fig_coord = go.Figure()
        categorias = ["1. Carga (I_B)", "2. Diseño (I_d)", "3. Proteccion (I_n)", "4. Cable (I_Z')", "5. Disparo (I_2)", "6. Limite (1.45 I_Z')"]
        valores_corr = [ib, id_diseno, in_itm, iz_optima, i2_disparo, limite_termico_cable]
        colores_c = ["#475569", "#64748B", "#DC2626", "#1D4ED8", "#D97706", "#059669"]

        fig_coord.add_trace(go.Bar(
            x=categorias,
            y=valores_corr,
            text=[f"{v:.1f} A" for v in valores_corr],
            textposition="outside",
            marker_color=colores_c,
            marker_line_color="#0F172A",
            marker_line_width=1.2
        ))

        fig_coord.update_layout(**LIGHT_LAYOUT)
        fig_coord.update_layout(
            title="Diagrama de Escalonamiento de Coordinacion de Protecciones",
            xaxis_title="Magnitudes de Referencia Normativa",
            yaxis_title="Corriente [A]",
            yaxis=dict(range=[0, max(valores_corr) * 1.18], gridcolor="#E2E8F0", showline=True, linecolor="#0F172A", mirror=True),
            height=460
        )
        st.plotly_chart(fig_coord, use_container_width=True)

# ==============================================================================
# TAB 3: EXPORTACION DE DOCUMENTO TECNICO Y DATOS ADQUIRIDOS
# ==============================================================================
with tab3:
    st.subheader("Generacion de Memoria de Calculo y Exportacion de Tablas")
    st.markdown(
        "Descarga la **Memoria de Calculo Tecnica (.MD)** lista para adjuntar en informes de ingenieria "
        "o exporta la matriz completa de evaluacion de conductores en formato **CSV**."
    )

    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")

    memoria_md = rf"""# MEMORIA DE CALCULO ELECTRICO: DIMENSIONAMIENTO DE ALIMENTADOR Y PROTECCION
**Identificador del Circuito:** `{id_circuito}`  
**Fecha de Emision:** {fecha_actual}  
**Marco Normativo de Referencia:** Pliegos Tecnicos Normativos RIC N°03 y RIC N°04 (SEC) / IEC 60364-5-52  

---

## 1. Datos de Entrada y Condiciones de Operacion
- **Configuracion del Sistema:** {sistema}
- **Tension Nominal de Servicio ($U_n$):** `{tension_v:.1f} V`
- **Naturaleza de la Carga:** {tipo_carga}
- **Potencia Activa Nominal ($P$):** `{potencia_w / 1000.0:.2f} kW`
- **Factor de Potencia ($\cos\varphi$):** `{cos_phi:.2f}`
- **Rendimiento del Equipo ($\eta$):** `{rendimiento:.2f}`
- **Longitud Simple de la Linea ($L$):** `{longitud_m:.1f} m`
- **Material y Aislacion del Conductor:** {material} — {temp_aislacion}
- **Factores de Correccion Aplicados:** $f_T = {f_t:.3f}$ ({temp_amb} °C), $f_g = {f_g:.3f}$ ({n_agrup} circuitos) $\Rightarrow f_{{\text{{total}}}} = {f_total:.3f}$

---

## 2. Resultados del Calculo Electrico y Seleccion
| Parametro Calculado | Simbolo | Valor Obtenido | Criterio / Observacion |
| :--- | :---: | :---: | :--- |
| **Corriente de Empleo** | $I_B$ | `{ib:.2f} A` | Calculada a plena carga |
| **Corriente de Diseño** | $I_d$ | `{id_diseno:.2f} A` | Factor de servicio `{factor_seg:.2f}` |
| **Proteccion Termomagnetica** | $I_n$ | `{in_itm} A` | {curva_itm} |
| **Seccion Nominal Seleccionada** | $S$ | `{s_optima} mm²` | {estado_proyecto} |
| **Capacidad de Transporte Corregida** | $I_Z'$ | `{iz_optima:.2f} A` | Cumple $I_B \le I_n \le I_Z'$ |
| **Caida de Tension en Linea** | $\Delta V$ | `{dv_v_opt:.2f} V` (`{dv_pct_opt:.2f} %`) | Limite maximo admisible: `{dv_max_pct:.1f} %` |
| **Disipacion por Efecto Joule** | $P_{{\text{{Joule}}}}$ | `{p_loss_opt:.1f} W` | A temperatura maxima de servicio |
| **Soporte Termico Cortocircuito** | $I_{{cc,\max}}$ | `{icc_soportada_ka:.2f} kA` | Para tiempo de despeje $t = {t_disparo:.2f}\text{{ s}}$ ($k = {k_adiab:.0f}$) |

---

## 3. Formulacion Matematica Aplicada

1. **Resistividad a la Temperatura de Servicio ($\rho_T$):**
   $$\rho_T = \rho_{{20}} \left[ 1 + \alpha_{{20}} (T_{{\text{{op}}}} - 20) \right] = {rho_op:.5f} \, \Omega \cdot \text{{mm}}^2 / \text{{m}}$$

2. **Caida de Tension Considerando Impedancia de Linea ($R$ y $X$):**
   $$\Delta V = k \cdot I_B \cdot L \cdot \left( \frac{{\rho_T}}{{S}} \cos\varphi + X_L \sin\varphi \right)$$

3. **Coordinacion de Protecciones contra Sobrecargas:**
   $$I_B ({ib:.1f}\text{{ A}}) \le I_n ({in_itm}\text{{ A}}) \le I_Z' ({iz_optima:.1f}\text{{ A}})$$
"""

    c_dl1, c_dl2 = st.columns(2)

    csv_data = df_secciones.to_csv(index=False).encode("utf-8")
    c_dl1.download_button(
        label="DESCARGAR TABLA EVALUATIVA DE SECCIONES (.CSV)",
        data=csv_data,
        file_name=f"evaluacion_conductores_{id_circuito}.csv",
        mime="text/csv",
        use_container_width=True
    )

    c_dl2.download_button(
        label="EXPORTAR MEMORIA DE CALCULO TECNICA (.MD)",
        data=memoria_md.encode("utf-8"),
        file_name=f"memoria_calculo_{id_circuito}.md",
        mime="text/markdown",
        use_container_width=True
    )

    st.markdown("#### Vista Previa del Documento Tecnico Generado")
    with st.container(border=True):
        st.markdown(memoria_md)