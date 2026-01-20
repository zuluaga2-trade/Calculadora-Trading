import streamlit as st
import re
from datetime import datetime, date

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

# Variables principales inicializadas
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
            # Si hay datos válidos en TOS, los usamos como prioritarios
            datos = datos_tos
            
            if datos['tipo'] == "CALL":
                st.info("🔹 Detectado Covered Call: Ingresa tu costo de asignación.")
                capital_invertido = st.number_input(
                    "¿A qué precio compraste las acciones? (Cost Basis)", 
                    value=datos['strike'], 
                    step=0.5,
                    format="%.2f",
                    key="costo_tos"  # Llave única para evitar conflictos
                )
            else:
                capital_invertido = datos['strike']
            
            # Ajuste a total real (x100)
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

    # Input especial para Manual (SOLO VISUAL AQUÍ, cálculo abajo)
    costo_manual_input = 0.0
    if m_tipo == "CALL":
        costo_manual_input = st.number_input("Costo Base de tus Acciones", value=m_strike, step=0.5, key="m_cost")
    else:
        costo_manual_input = m_strike

    # LÓGICA DE ACTIVACIÓN MANUAL
    # Solo sobrescribimos 'datos' si el usuario llenó los campos manuales
    if m_simbolo and m_strike > 0:
        # Solo si NO hay datos de TOS activos o si el usuario quiere usar manual explícitamente
        # (Aquí damos prioridad a Manual si está lleno, o a TOS si Manual está vacío)
        
        # Para evitar confusiones: Si TOS está vacío, usamos Manual.
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
        
        # Mostrar Resumen
        # Dividimos capital por 100 para mostrar el precio base por acción en el texto
        base_accion = capital_invertido / 100
        
        st.info(f"**{estrategia}** | {datos['simbolo']} | Strike Contrato: **${datos['strike']}** | Capital Base: **${base_accion:.2f}**")

        # Fórmulas
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
            if datos['tipo'] == "CALL" and base_accion != datos['strike']:
                st.caption(f"Calculado sobre base de ${base_accion:.2f}")

        # --- VERIFICADOR ---
        st.markdown("---")
        with st.expander("🔎 Verificar Mercado", expanded=True):
            prima_mercado = st.number_input("¿Cuánto paga el mercado?", value=0.0, step=0.01, key="market_price")

            if prima_mercado > 0:
                credito_real = prima_mercado * 100
                if capital_invertido > 0:
                    retorno_real_absoluto = credito_real / capital_invertido
                    retorno_real_anual = retorno_real_absoluto * (365 / dias_a_expiracion) * 100
                else:
                    retorno_real_absoluto = 0
                    retorno_real_anual = 0

                col_res, col_det = st.columns([2,1])
                with col_res:
                    if retorno_real_anual >= target_annual:
                        st.success(f"✅ **¡EXCELENTE!**\n\nRetorno Anualizado: **{retorno_real_anual:.2f}%**")
                    else:
                        st.error(f"❌ **BAJO OBJETIVO**\n\nRetorno Anualizado: **{retorno_real_anual:.2f}%**")
                
                with col_det:
                    st.metric("Retorno Absoluto", f"{retorno_real_absoluto*100:.2f}%")
                    
                    if datos['tipo'] == "CALL":
                        diferencia_precio = datos['strike'] - base_accion
                        if diferencia_precio > 0:
                            st.caption(f"➕ Ganancia Capital Potencial: ${diferencia_precio:.2f}/acción")
                        elif diferencia_precio < 0:
                            st.caption(f"⚠️ Strike debajo del costo (${abs(diferencia_precio):.2f})")

else:
    st.info("👈 Ingresa datos para calcular.")
