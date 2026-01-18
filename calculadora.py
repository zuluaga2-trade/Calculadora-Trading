import streamlit as st
import re
from datetime import datetime, date

# Configuración visual de la página
st.set_page_config(page_title="Calculadora TOS", layout="centered")

# --- FUNCIONES ---
def parsear_cadena_tos(cadena):
    """
    Limpia el punto inicial y analiza la cadena de TOS.
    """
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
        return None, "Formato no válido. Asegúrate de copiar desde TOS (Ej: .NVDA...)"

# --- INTERFAZ ---
st.title("🚀 Calculadora de Primas")

# Variable donde guardaremos los datos (vengan de donde vengan)
datos = None
error = None

# Creamos dos pestañas para elegir el método de entrada
tab1, tab2 = st.tabs(["📋 Pegar desde TOS", "✍️ Entrada Manual"])

# --- PESTAÑA 1: COPIAR Y PEGAR ---
with tab1:
    tos_string = st.text_input("Pegar Contrato", placeholder=".NVDA260123P182.5", help="Copia el código directamente desde la plataforma Thinkorswim")
    if tos_string:
        datos, error = parsear_cadena_tos(tos_string)

# --- PESTAÑA 2: MANUAL ---
with tab2:
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        m_simbolo = st.text_input("Símbolo", placeholder="Ej: NVDA").upper()
        m_fecha = st.date_input("Fecha Expiración", min_value=date.today())
    with col_m2:
        m_tipo = st.selectbox("Tipo", ["PUT", "CALL"])
        m_strike = st.number_input("Strike Price ($)", min_value=0.0, step=0.5)
    
    # Validar que tengamos datos mínimos para calcular
    if m_simbolo and m_strike > 0:
        datos = {
            "simbolo": m_simbolo,
            "fecha_exp": m_fecha,
            "tipo": m_tipo,
            "strike": float(m_strike)
        }

# --- CONFIGURACIÓN DE OBJETIVO ---
st.markdown("---")
target_annual = st.number_input("Objetivo Anual (%)", value=20.0, step=0.5, format="%.1f")

# --- LÓGICA PRINCIPAL (Se ejecuta si hay datos válidos) ---
if error:
    st.error(f"❌ {error}")

elif datos:
    # Cálculos de Tiempo
    hoy = date.today()
    dias_a_expiracion = (datos['fecha_exp'] - hoy).days
    
    if dias_a_expiracion <= 0:
        st.warning(f"⚠️ El contrato para {datos['simbolo']} expira hoy o ya expiró.")
    else:
        # Detectar Estrategia
        estrategia = "Cash Secured Put (CSP)" if datos['tipo'] == "PUT" else "Covered Call (CC)"
        icono_estrategia = "🛡️" if datos['tipo'] == "PUT" else "📈"
        
        colateral = datos['strike'] * 100

        # Mostrar Resumen del Contrato
        st.info(f"{icono_estrategia} **{estrategia}** | **{datos['simbolo']}** | Strike ${datos['strike']} | Expira: {datos['fecha_exp']} ({dias_a_expiracion} DTE)")

        # --- CÁLCULOS OBJETIVO ---
        factor_tiempo = dias_a_expiracion / 365.0
        retorno_periodo_pct = (target_annual / 100.0) * factor_tiempo
        prima_total_obj = colateral * retorno_periodo_pct
        prima_accion_obj = prima_total_obj / 100

        # --- RESULTADOS ---
        st.markdown("### 🎯 Objetivo")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Prima Mínima (Limit)", f"${prima_accion_obj:.2f}")
        with c2:
            st.metric("Crédito Total", f"${prima_total_obj:.2f}")
        with c3:
            st.metric("Colateral", f"${colateral:,.0f}")

        st.caption(f"Meta: {target_annual}% Anual → Necesitas {retorno_periodo_pct*100:.2f}% en estos {dias_a_expiracion} días.")

        # --- VERIFICADOR DE MERCADO ---
        st.markdown("---")
        with st.expander("🔎 Verificar Mercado (Comparar Precio Real)", expanded=True):
            prima_mercado = st.number_input("¿Cuánto paga el mercado actualmente?", value=0.0, step=0.01)

            if prima_mercado > 0:
                credito_real = prima_mercado * 100
                retorno_real_absoluto = credito_real / colateral
                retorno_real_anual = retorno_real_absoluto * (365 / dias_a_expiracion) * 100

                col_res, col_det = st.columns([2,1])
                with col_res:
                    if retorno_real_anual >= target_annual:
                        st.success(f"✅ **¡BUENA OPERACIÓN!**\n\nRetorno Anualizado: **{retorno_real_anual:.2f}%**")
                    else:
                        st.error(f"❌ **NO CUMPLE OBJETIVO**\n\nRetorno Anualizado: **{retorno_real_anual:.2f}%**")
                
                with col_det:
                    st.metric("Retorno Absoluto", f"{retorno_real_absoluto*100:.2f}%")

else:
    st.info("👈 Ingresa los datos del contrato arriba para comenzar.")
