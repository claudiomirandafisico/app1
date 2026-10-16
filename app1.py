import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import io

# Importaciones para generacion de PDF con formato de informe tecnico oficial
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(
    page_title="Informe Tecnico // Calculo y Verificacion Electrica",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS Empresarial / Tecnico Profesional
st.markdown("""
<style>
    .stApp {
        background-color: #FFFFFF;
        color: #0F172A;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-top: 3px solid #1E293B;
        padding: 12px 16px;
        border-radius: 2px;
    }
    div[data-testid="stMetricLabel"] {
        color: #475569;
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    div[data-testid="stMetricValue"] {
        color: #0F172A;
        font-family: 'Courier New', monospace;
        font-size: 1.25rem;
        font-weight: 700;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background-color: #F1F5F9;
        border-bottom: 2px solid #CBD5E1;
        border-radius: 4px 4px 0 0;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #F1F5F9;
        border: none;
        color: #475569;
        padding: 10px 24px;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF;
        color: #0F172A;
        border-top: 3px solid #1E293B;
    }
    h1, h2, h3, h4 {
        font-family: 'Inter', sans-serif;
        color: #0F172A;
        letter-spacing: -0.01em;
    }
    .autor-footer {
        margin-top: 30px;
        padding: 12px;
        background-color: #F8FAFC;
        border-left: 4px solid #1E293B;
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem;
        color: #334155;
    }
</style>
""", unsafe_allow_html=True)

st.title("INFORME TECNICO DE INGENIERIA ELECTRICA")
st.caption("Verificacion y dimensionamiento de alimentadores, caida de tension y protecciones (Normativa RIC SEC / IEC 60364).")

# --- BASE DE DATOS NORMATIVA ---
SECCIONES_MM2 = [1.5, 2.5, 4.0, 6.0, 10.0, 16.0, 25.0, 35.0, 50.0, 70.0, 95.0, 120.0, 150.0, 185.0, 240.0]

TABLA_AMPACIDAD = {
    "Cobre_70C":  [15.5, 21.0, 28.0, 36.0, 50.0, 68.0, 89.0, 110.0, 134.0, 171.0, 207.0, 239.0, 272.0, 310.0, 364.0],
    "Cobre_90C":  [19.5, 27.0, 36.0, 46.0, 63.0, 85.0, 112.0, 138.0, 168.0, 213.0, 258.0, 299.0, 344.0, 392.0, 461.0],
    "Aluminio_70C": [12.0, 16.5, 22.0, 28.0, 39.0, 53.0, 70.0, 86.0, 104.0, 133.0, 161.0, 186.0, 212.0, 241.0, 284.0],
    "Aluminio_90C": [15.0, 21.0, 28.0, 36.0, 49.0, 66.0, 83.0, 103.0, 125.0, 160.0, 194.0, 226.0, 260.0, 297.0, 350.0]
}

CALIBRES_ITM = [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630]
FACTORES_AGRUPAMIENTO = {1: 1.00, 2: 0.80, 3: 0.70, 4: 0.65, 5: 0.60, 6: 0.57, 7: 0.54, 8: 0.52, 9: 0.50}

def factor_temperatura(temp_amb, temp_aislacion):
    t_ref = 30.0
    t_max = 70.0 if "70" in temp_aislacion else 90.0
    if temp_amb >= t_max:
        return 0.1
    return np.sqrt((t_max - temp_amb) / (t_max - t_ref))

def calcular_resistividad_operacion(material, temp_aislacion):
    rho_20 = 0.017241 if material == "Cobre" else 0.028264
    alpha_20 = 0.00393 if material == "Cobre" else 0.00403
    t_op = 70.0 if "70" in temp_aislacion else 90.0
    return rho_20 * (1.0 + alpha_20 * (t_op - 20.0))

def calcular_corriente_empleo(potencia_w, tension_v, cos_phi, rendimiento, sistema, factor_seguridad):
    p_absor = potencia_w / rendimiento
    if sistema == "Monofasico (220 V / Fase-Neutro)":
        ib = p_absor / (tension_v * cos_phi)
    else:
        ib = p_absor / (np.sqrt(3.0) * tension_v * cos_phi)
    id_diseno = ib * factor_seguridad
    return ib, id_diseno, p_absor

def calcular_caida_tension(seccion, longitud_m, corriente_a, tension_v, cos_phi, rho, reactancia_km, sistema):
    sin_phi = np.sqrt(max(0.0, 1.0 - cos_phi**2))
    k_sist = 2.0 if "Monofasico" in sistema else np.sqrt(3.0)
    r_ohm_m = rho / seccion
    x_ohm_m = reactancia_km / 1000.0
    dv_volt = k_sist * corriente_a * longitud_m * (r_ohm_m * cos_phi + x_ohm_m * sin_phi)
    dv_pct = (dv_volt / tension_v) * 100.0
    n_cond_activos = 2.0 if "Monofasico" in sistema else 3.0
    p_joule_w = n_cond_activos * (corriente_a**2) * r_ohm_m * longitud_m
    return dv_volt, dv_pct, p_joule_w

def seleccionar_itm(ib_diseno):
    for cal in CALIBRES_ITM:
        if cal >= ib_diseno:
            return cal
    return CALIBRES_ITM[-1]

# --- PANEL LATERAL DE ENTRADA ---
st.sidebar.header("DATOS DEL CIRCUITO")
id_circuito = st.sidebar.text_input("Identificador de Tag / Instancia", value="ALIM-GENERAL-01")
sistema = st.sidebar.selectbox("Sistema Electrico", ["Trifasico (380 V / 400 V)", "Monofasico (220 V / Fase-Neutro)"])

tension_def = 380.0 if "Trifasico" in sistema else 220.0
tension_v = st.sidebar.number_input("Tension Nominal [V]", value=tension_def, step=10.0)

tipo_carga = st.sidebar.selectbox("Tipo de Carga", ["Motor / Carga Inductiva (Factor 1.25)", "Alimentador General (Factor 1.00)"])
factor_seg = 1.25 if "Motor" in tipo_carga else 1.00

unidad_pot = st.sidebar.radio("Unidad de Potencia", ["Potencia Activa [kW]", "Corriente Directa [A]"])
if unidad_pot == "Potencia Activa [kW]":
    kw_in = st.sidebar.number_input("Potencia [kW]", value=18.5, step=0.5)
    potencia_w = kw_in * 1000.0
else:
    i_directa = st.sidebar.number_input("Corriente [A]", value=35.0, step=1.0)

cos_phi = st.sidebar.slider("Factor de Potencia (cos phi)", 0.50, 1.00, 0.85, 0.01)
rendimiento = st.sidebar.slider("Rendimiento (eta)", 0.60, 1.00, 0.92 if "Motor" in tipo_carga else 1.00, 0.01)

st.sidebar.subheader("Condiciones de Instalacion")
longitud_m = st.sidebar.number_input("Longitud de Canalizacion [m]", value=55.0, step=5.0)
dv_max_pct = st.sidebar.selectbox("Maxima Caida Admisible [%]", [3.0, 5.0, 2.0], index=0)

material = st.sidebar.selectbox("Material Conductor", ["Cobre", "Aluminio"])
temp_aislacion = st.sidebar.selectbox("Aislacion", ["XLPE / EPR (90°C)", "PVC / THHN (70°C)"])
temp_amb = st.sidebar.slider("Temperatura Ambiente [°C]", 15, 55, 35, 5)
n_agrup = st.sidebar.selectbox("Circuitos Agrupados", list(FACTORES_AGRUPAMIENTO.keys()), index=0)
curva_itm = st.sidebar.selectbox("Curva Proteccion", ["Curva C (General)", "Curva D (Motores)"])

# --- COMPUTOS ---
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
reactancia_km = 0.08

registros_secciones = []
for idx, s_mm2 in enumerate(SECCIONES_MM2):
    iz_base = ampacidades_base[idx]
    iz_corr = iz_base * f_total
    dv_v, dv_pct, p_loss = calcular_caida_tension(s_mm2, longitud_m, ib, tension_v, cos_phi, rho_op, reactancia_km, sistema)
    
    cumple_termico = (iz_corr >= in_itm) and (iz_corr >= id_diseno)
    cumple_tension = (dv_pct <= dv_max_pct)
    cumple_global = cumple_termico and cumple_tension
    
    registros_secciones.append({
        "Seccion [mm2]": s_mm2,
        "I_Z Base [A]": iz_base,
        "I_Z' Corr [A]": iz_corr,
        "dV [V]": dv_v,
        "dV [%]": dv_pct,
        "Perdida [W]": p_loss,
        "Termico": "OK" if cumple_termico else "NO",
        "Tension": "OK" if cumple_tension else "NO",
        "Estado": "APROBADO" if cumple_global else "RECHAZADO"
    })

df_secciones = pd.DataFrame(registros_secciones)

aprobados_global = df_secciones[df_secciones["Estado"] == "APROBADO"]
if not aprobados_global.empty:
    fila_optima = aprobados_global.iloc[0]
    estado_proyecto = "CONFORME A NORMA"
else:
    fila_optima = df_secciones.iloc[-1]
    estado_proyecto = "REQUIERE SECCION SUPERIOR"

s_optima = fila_optima["Seccion [mm2]"]
iz_optima = fila_optima["I_Z' Corr [A]"]
dv_v_opt = fila_optima["dV [V]"]
dv_pct_opt = fila_optima["dV [%]"]
p_loss_opt = fila_optima["Perdida [W]"]

CORP_LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    font=dict(family="Inter, sans-serif", color="#0F172A", size=11),
    xaxis=dict(gridcolor="#E2E8F0", zerolinecolor="#CBD5E1", showline=True, linecolor="#0F172A", mirror=True),
    yaxis=dict(gridcolor="#E2E8F0", zerolinecolor="#CBD5E1", showline=True, linecolor="#0F172A", mirror=True),
    margin=dict(l=50, r=20, t=40, b=40)
)

# --- PESTAÑAS DE INGENIERIA ---
tab1, tab2 = st.tabs(["01 // ANALISIS Y DIMENSIONAMIENTO", "02 // INFORME TECNICO OFICIAL Y EXPORTACION PDF"])

with tab1:
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("CORRIENTE EMPLEO (I_B)", f"{ib:.1f} A")
    m2.metric("PROTECCION (I_n)", f"{in_itm} A")
    m3.metric("SECCION SELECCIONADA", f"{s_optima} mm²")
    m4.metric("AMPACIDAD CORREGIDA", f"{iz_optima:.1f} A")
    m5.metric("CAIDA TENSION", f"{dv_pct_opt:.2f} %")

    st.markdown(f"**Tag del Circuito:** `{id_circuito}` | **Estatus Normativo:** `{estado_proyecto}`")

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        dist_arr = np.linspace(1.0, max(longitud_m * 1.5, 40.0), 100)
        fig_dv = go.Figure()
        idx_opt = SECCIONES_MM2.index(s_optima)
        indices_plot = sorted(list(set([max(0, idx_opt - 1), idx_opt, min(len(SECCIONES_MM2) - 1, idx_opt + 1)])))
        colores_curvas = ["#D97706", "#1E293B", "#059669"] 
        
        for c_i, s_idx in enumerate(indices_plot):
            sec_eval = SECCIONES_MM2[s_idx]
            _, dv_arr_pct, _ = calcular_caida_tension(sec_eval, dist_arr, ib, tension_v, cos_phi, rho_op, reactancia_km, sistema)
            es_opt = (sec_eval == s_optima)
            fig_dv.add_trace(go.Scatter(
                x=dist_arr, y=dv_arr_pct, mode="lines+markers" if es_opt else "lines",
                line=dict(color=colores_curvas[c_i], width=3.0 if es_opt else 1.5, dash="solid" if es_opt else "dot"),
                name=f"Calibre {sec_eval} mm² {'(SELECCIONADO)' if es_opt else ''}"
            ))
            
        fig_dv.add_hline(y=dv_max_pct, line_dash="dash", line_color="#DC2626", annotation_text=f"Max Admisible ({dv_max_pct}%)", annotation_position="top left")
        fig_dv.update_layout(**CORP_LAYOUT)
        fig_dv.update_layout(title="<b>Regulacion de Tension vs. Longitud</b> (Analisis Comparativo)", xaxis_title="Distancia de Canalizacion [m]", yaxis_title="Caida de Tension dV [%]", height=380)
        st.plotly_chart(fig_dv, use_container_width=True)

    with col_g2:
        df_sub = df_secciones.iloc[max(0, idx_opt - 3):min(len(SECCIONES_MM2), idx_opt + 4)]
        fig_sec = go.Figure()
        colores_barras = ["#1E293B" if s == s_optima else ("#E11D48" if est == "RECHAZADO" else "#3B82F6") 
                          for s, est in zip(df_sub["Seccion [mm2]"], df_sub["Estado"])]

        fig_sec.add_trace(go.Bar(
            x=[f"{s} mm²" for s in df_sub["Seccion [mm2]"]],
            y=df_sub["I_Z' Corr [A]"],
            marker_color=colores_barras,
            marker_line_color="#0F172A", marker_line_width=1.2,
            text=[f"{val:.1f} A" for val in df_sub["I_Z' Corr [A]"]],
            textposition="auto"
        ))
        fig_sec.add_hline(y=in_itm, line_dash="dash", line_color="#DC2626", annotation_text=f"Proteccion I_n = {in_itm} A", annotation_position="top right")
        fig_sec.update_layout(**CORP_LAYOUT)
        fig_sec.update_layout(title="<b>Capacidad de Ampacidad Corregida (I_Z') por Calibre</b>", xaxis_title="Seccion Nominal", yaxis_title="Corriente Admisible [A]", height=380, showlegend=False)
        st.plotly_chart(fig_sec, use_container_width=True)

    st.markdown("#### Matriz de Verificacion Normativa")
    st.dataframe(df_secciones.style.format({"Seccion [mm2]": "{:.1f}", "I_Z Base [A]": "{:.1f}", "I_Z' Corr [A]": "{:.1f}", "dV [V]": "{:.2f}", "dV [%]": "{:.2f}", "Perdida [W]": "{:.1f}"}), use_container_width=True, hide_index=True, height=260)

with tab2:
    st.subheader("Generacion y Exportacion de Informe Tecnico Oficial en PDF")
    st.markdown("Genera un documento formal bajo estructura estricta de informe de ensayo e ingeniería institucional.")

    fecha_emision = datetime.now().strftime("%Y-%m-%d %H:%M")
    n_informe = f"IE-{datetime.now().strftime('%Y%m%d')}-01"
    codigo_verif = f"v{np.random.randint(100000, 999999)}x"

    def generar_pdf_informe_tecnico():
        buffer = io.BytesIO()
        
        def add_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 7.5)
            canvas.setFillColor(colors.HexColor('#475569'))
            footer_text = f"Para verificar este documento ingrese a sistema // Codigo de verificacion: {codigo_verif} — Página {doc.page} de 1"
            canvas.drawString(40, 25, footer_text)
            canvas.setStrokeColor(colors.HexColor('#CBD5E1'))
            canvas.setLineWidth(0.5)
            canvas.line(40, 37, 574, 37)
            canvas.restoreState()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40, leftMargin=40,
            topMargin=40, bottomMargin=50
        )
        
        styles = getSampleStyleSheet()
        
        style_header_title = ParagraphStyle('HeaderTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=13, textColor=colors.HexColor('#0F172A'), alignment=TA_LEFT)
        style_header_meta = ParagraphStyle('HeaderMeta', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#475569'), alignment=TA_RIGHT)
        style_section_title = ParagraphStyle('SecTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'), spaceBefore=6, spaceAfter=2)
        style_body = ParagraphStyle('DocBody', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10.5, textColor=colors.HexColor('#0F172A'))
        style_table_text = ParagraphStyle('TableText', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9.5, textColor=colors.HexColor('#0F172A'))
        style_table_header = ParagraphStyle('TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, textColor=colors.white, alignment=TA_CENTER)
        style_obs = ParagraphStyle('ObsText', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=10, textColor=colors.HexColor('#334155'))
        
        story = []
        
        # Cabecera formal tipo reporte técnico oficial
        header_data = [
            [Paragraph("<b>INFORME TECNICO DE VERIFICACION ELECTRICA</b>", style_header_title), 
             Paragraph(f"<b>N° de Informe:</b> {n_informe}<br/><b>Fecha Emision:</b> {fecha_emision}", style_header_meta)]
        ]
        t_header = Table(header_data, colWidths=[330, 204])
        t_header.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(t_header)
        story.append(Spacer(1, 2))
        story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor('#0F172A'), spaceBefore=2, spaceAfter=4))
        
        # Bloque de Identificación (Estilo tabla institucional de metadatos)
        story.append(Paragraph("IDENTIFICACION DEL SOLICITANTE Y PROYECTO", style_section_title))
        data_id = [
            [Paragraph("<b>Identificador / Tag:</b>", style_body), Paragraph(id_circuito, style_body), Paragraph("<b>Normativa Aplicada:</b>", style_body), Paragraph("RIC SEC / IEC 60364", style_body)],
            [Paragraph("<b>Especialista Responsable:</b>", style_body), Paragraph("Claudio Andrés Miranda Obreque", style_body), Paragraph("<b>Calificacion:</b>", style_body), Paragraph("Instalador SEC Clase D, Est. Física", style_body)],
        ]
        t_id = Table(data_id, colWidths=[120, 150, 110, 154])
        t_id.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
            ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ]))
        story.append(t_id)
        story.append(Spacer(1, 4))
        
        # Parámetros de Operación
        story.append(Paragraph("PARAMETROS DE DISEÑO Y OPERACION", style_section_title))
        data_params = [
            [Paragraph("<b>Sistema Electrico:</b>", style_body), Paragraph(sistema, style_body), Paragraph("<b>Tension Nominal:</b>", style_body), Paragraph(f"{tension_v:.1f} V", style_body)],
            [Paragraph("<b>Potencia / Carga:</b>", style_body), Paragraph(f"{potencia_w/1000.0:.2f} kW", style_body), Paragraph("<b>Factor de Potencia:</b>", style_body), Paragraph(f"{cos_phi:.2f}", style_body)],
            [Paragraph("<b>Corriente Empleo (I_B):</b>", style_body), Paragraph(f"{ib:.2f} A", style_body), Paragraph("<b>Corriente Diseño (I_d):</b>", style_body), Paragraph(f"{id_diseno:.2f} A", style_body)],
            [Paragraph("<b>Longitud Canalizacion:</b>", style_body), Paragraph(f"{longitud_m:.1f} m", style_body), Paragraph("<b>Material Conductor:</b>", style_body), Paragraph(f"{material} ({temp_aislacion})", style_body)],
        ]
        t_params = Table(data_params, colWidths=[120, 150, 110, 154])
        t_params.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
            ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ]))
        story.append(t_params)
        story.append(Spacer(1, 4))
        
        # Resultados de Verificación
        story.append(Paragraph("RESULTADOS DE VERIFICACION Y DIMENSIONAMIENTO TECNICO", style_section_title))
        data_results = [
            [Paragraph("<b>Parametro Tecnico Evaluado</b>", style_table_header), Paragraph("<b>Valor Obtenido</b>", style_table_header), Paragraph("<b>Criterio / Estatus Normativo</b>", style_table_header)],
            [Paragraph("Calibre de Proteccion (I_n)", style_table_text), Paragraph(f"{in_itm} A ({curva_itm})", style_table_text), Paragraph("Conforme (I_n >= I_d)", style_table_text)],
            [Paragraph("Seccion Nominal Conductor (S)", style_table_text), Paragraph(f"{s_optima} mm²", style_table_text), Paragraph(estado_proyecto, style_table_text)],
            [Paragraph("Ampacidad Corregida (I_Z')", style_table_text), Paragraph(f"{iz_optima:.2f} A", style_table_text), Paragraph("Conforme (I_Z' >= I_n)", style_table_text)],
            [Paragraph("Caida de Tension en Linea (dV)", style_table_text), Paragraph(f"{dv_v_opt:.2f} V ({dv_pct_opt:.2f} %)", style_table_text), Paragraph(f"Conforme (Max admisible {dv_max_pct}%)", style_table_text)],
            [Paragraph("Perdidas por Efecto Joule", style_table_text), Paragraph(f"{p_loss_opt:.1f} W", style_table_text), Paragraph("Regimen Permanente Admisible", style_table_text)]
        ]
        t_results = Table(data_results, colWidths=[180, 140, 214])
        t_results.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#0F172A')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(t_results)
        story.append(Spacer(1, 4))
        
        # Observaciones Asociadas
        story.append(Paragraph("OBSERVACIONES ASOCIADAS AL SERVICIO", style_section_title))
        obs_text = (
            "1. Los resultados expuestos son válidos exclusivamente para el circuito y los parámetros operacionales declarados.<br/>"
            "2. El dimensionamiento verifica estrictamente la capacidad térmica de transporte de corriente y la regulación de tensión máxima permitida en baja tensión.<br/>"
            "3. Estudio desarrollado bajo los estándares técnicos vigentes por especialista calificado."
        )
        t_obs = Table([[Paragraph(obs_text, style_obs)]], colWidths=[534])
        t_obs.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(t_obs)
        story.append(Spacer(1, 8))
        
        # Firmas y Responsable
        sig_data = [
            [Paragraph("<b>Especialista Responsable:</b><br/><br/><br/><b>Claudio Andrés Miranda Obreque</b><br/>Instalador SEC Clase D, Est. Física", style_body),
             Paragraph("<b>Aprobación / V° B°:</b><br/><br/><br/>___________________________________<br/>Firma y Timbre Autorizado", style_body)]
        ]
        t_sig = Table(sig_data, colWidths=[267, 267])
        t_sig.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(KeepTogether(t_sig))
        
        doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
        buffer.seek(0)
        return buffer.getvalue()

    pdf_bytes = generar_pdf_informe_tecnico()

    st.download_button(
        label="📥 DESCARGAR INFORME TECNICO OFICIAL EN PDF",
        data=pdf_bytes,
        file_name=f"Informe_Tecnico_{id_circuito}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

# --- FIRMA / AUTOR PERMANENTE ---
st.markdown(
    """
    <div class="autor-footer">
        <b>Estudio Desarrollado por:</b> Claudio Andrés Miranda Obreque<br>
        <b>Especialidad:</b> Instalador SEC Clase D, Est. Física
    </div>
    """,
    unsafe_allow_html=True
)
