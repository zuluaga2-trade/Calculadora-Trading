import streamlit as st
import re
from datetime import datetime, date
import urllib.parse # Nueva librería para crear el enlace de WhatsApp

# Configuración visual
st.set_page_config(page_title="Calculadora TOS Pro", layout="centered")

# --- FUNCIONES ---
def parsear_cadena_tos(cadena):
    cadena_limpia = cadena.strip().lstrip('.').strip()
    patron = r"^([A-Z]+)(\d{6})([PC])([\d\.]+)$"
    match = re.match(patron, cadena_limpia)
    
    if match:
        simbolo, fecha_str, tipo_letra, strike_str = match.groups()
        try:
            fecha_exp = datetime.strptime(fecha_str, "%y%m%d").date()
        except ValueError:
            return None, "Error en fecha"
            
        return {
            "simbolo": simbolo,
            "fecha_exp": fecha_exp,
            "tipo": "PUT" if tipo_letra == 'P' else "CALL",
            "strike": float(strike_str)
        }, None
    else:
        return None, "Formato no válido."

# --- INTERFAZ ---
st.title("🚀 Calculadora de Primas")

datos = None
capital_invertido = 0.0
error = None

# Pestañas
tab1, tab2 = st.tabs(["📋 Pegar desde TOS", "✍️ Entrada Manual"])

# --- PESTAÑA 1: T.O.S. ---
with tab1:
    tos_string = st.text_input("Pegar Contrato", placeholder=".NVDA260123P182.5", key="input_tos")
    
    if tos_string:
        datos_tos, error_tos = parsear_cadena_tos(tos_string)
        if datos_tos:
            datos = datos_tos
            if datos['tipo'] == "CALL":
                st.info("🔹 Detectado Covered Call: Ingresa tu costo de asignación.")
                capital_invertido = st.number_input(
                    "¿A qué precio compraste las acciones? (Cost Basis)", 
                    value=datos['strike'], 
                    step=0.5,
                    format="%.2f",
                    key="costo_tos"
                )
            else:
                capital_invertido = datos['strike']
            capital_invertido = capital_invertido * 100
        else:
            error = error_tos

# --- PESTAÑA 2: MANUAL ---
with tab2:
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        m_simbolo = st.text_input("Símbolo", placeholder="Ej: NVDA", key="m_sym").upper()
        m_fecha = st.date_input("Fecha Expiración", min_value=date.today(), key="m_date")
    with col_m2:
        m_tipo = st.selectbox("Tipo", ["PUT", "CALL"], key="m_type")
        m_strike = st.number_input("Strike del Contrato", min_value=0.0, step=0.5, key="m_strike")

    costo_manual_input = 0.0
    if m_tipo == "CALL":
        costo_manual_input = st.number_input("Costo Base de tus Acciones", value=m_strike, step=0.5, key="m_cost")
    else:
        costo_manual_input = m_strike

    if m_simbolo and m_strike > 0:
        if not tos_string: 
            datos = {
                "simbolo": m_simbolo,
                "fecha_exp": m_fecha,
                "tipo": m_tipo,
                "strike": float(m_strike)
            }
            capital_invertido = costo_manual_input * 100

# --- OBJETIVO GLOBAL ---
st.markdown("---")
target_annual = st.number_input("Objetivo Anual (%)", value=20.0, step=0.5, format="%.1f", key="global_target")

# --- MOTOR DE CÁLCULO ---
if error:
    st.error(f"❌ {error}")

elif datos:
    hoy = date.today()
    dias_a_expiracion = (datos['fecha_exp'] - hoy).days
    
    if dias_a_expiracion <= 0:
        st.warning(f"⚠️ El contrato expira hoy o ya expiró.")
    else:
        estrategia = "Cash Secured Put (CSP)" if datos['tipo'] == "PUT" else "Covered Call (CC)"
        base_accion = capital_invertido / 100
        
        st.info(f"**{estrategia}** | {datos['simbolo']} | Strike: **${datos['strike']}** | Base: **${base_accion:.2f}**")

        factor_tiempo = dias_a_expiracion / 365.0
        retorno_periodo_pct = (target_annual / 100.0) * factor_tiempo
        prima_total_obj = capital_invertido * retorno_periodo_pct
        prima_accion_obj = prima_total_obj / 100

        # --- RESULTADOS ---
        st.markdown("### 🎯 Objetivo")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Prima Mínima", f"${prima_accion_obj:.2f}")
        with c2:
            st.metric("Crédito Total", f"${prima_total_obj:.2f}")
        with c3:
            st.metric("Capital Invertido", f"${capital_invertido:,.0f}")

        # --- VERIFICADOR Y COMPARTIR ---
        st.markdown("---")
        
        # Variables para el mensaje de compartir (se llenarán abajo)
        mensaje_final = ""
        retorno_str = ""

        with st.expander("🔎 Verificar Mercado y Compartir", expanded=True):
            prima_mercado = st.number_input("¿Cuánto paga el mercado?", value=0.0, step=0.01, key="market_price")

            if prima_mercado > 0:
                credito_real = prima_mercado * 100
                if capital_invertido > 0:
                    retorno_real_absoluto = credito_real / capital_invertido
                    retorno_real_anual = retorno_real_absoluto * (365 / dias_a_expiracion) * 100
                else:
                    retorno_real_anual = 0

                if retorno_real_anual >= target_annual:
                    st.success(f"✅ **¡EXCELENTE!** Retorno Anualizado: **{retorno_real_anual:.2f}%**")
                    emoji_resultado = "✅"
                else:
                    st.error(f"❌ **BAJO OBJETIVO** Retorno Anualizado: **{retorno_real_anual:.2f}%**")
                    emoji_resultado = "⚠️"
                
                retorno_str = f"\n💰 Prima Mercado: ${prima_mercado}\n📈 Retorno Anualizado: {retorno_real_anual:.2f}% {emoji_resultado}"
            
            # --- GENERADOR DE TEXTO PARA COMPARTIR ---
            st.markdown("#### 📤 Compartir Análisis")
            
            # Construimos el mensaje
            texto_share = f"""
🚨 Trade Idea: {datos['simbolo']} ({estrategia})

📅 Expira: {datos['fecha_exp']} ({dias_a_expiracion} días)
🎯 Strike: ${datos['strike']}
💵 Capital Requerido: ${capital_invertido:,.0f}

🎯 Objetivo Personal: Buscar prima de ${prima_accion_obj:.2f}{retorno_str}
""".strip()

            # 1. Mostrar Bloque de Código (Tiene botón de copiar nativo)
            st.code(texto_share, language="text")
            
            # 2. Botón para enviar a WhatsApp
            texto_encoded = urllib.parse.quote(texto_share)
            whatsapp_url = f"https://wa.me/?text={texto_encoded}"
            
            st.link_button("📲 Enviar por WhatsApp", whatsapp_url)

else:
    st.info("👈 Ingresa datos para calcular.")
