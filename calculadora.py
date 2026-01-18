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
    # 1. Limpieza: Quitamos espacios y el punto inicial si existe
    cadena_limpia = cadena.strip().lstrip('.').strip()
    
    # 2. Regex: Busca Letras + 6 Dígitos + P/C + Número (incluyendo decimales)
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
st.title("🚀 Calculadora de Primas TOS")

# Contenedor superior para entradas
with st.container():
    col1, col2 = st.columns([2, 1])
    with col1:
        tos_string = st.text_input("Pegar Contrato (con o sin punto)", placeholder=".NVDA260123P182.5")
    with col2:
        target_annual = st.number_input("Objetivo Anual (%)", value=20.0, step=0.5, format="%.1f")

if tos_string:
    datos, error = parsear_cadena_tos(tos_string)
    
    if error:
        st.error(f"❌ {error}")
    else:
        # Cálculos de Tiempo
        hoy = date.today()
        dias_a_expiracion = (datos['fecha_exp'] - hoy).days
        
        if dias_a_expiracion <= 0:
            st.warning(f"⚠️ Este contrato expira hoy o ya expiró ({dias_a_expiracion} días).")
        else:
            # --- LÓGICA AUTOMÁTICA DE ESTRATEGIA ---
            # Si es PUT -> Cash Secured Put. Si es CALL -> Covered Call.
            # En ambos casos, para simplificar el cálculo rápido, usamos Strike * 100 como base de capital.
            estrategia = "Cash Secured Put (CSP)" if datos['tipo'] == "PUT" else "Covered Call (CC)"
            icono_estrategia = "🛡️" if datos['tipo'] == "PUT" else "📈"
            
            colateral = datos['strike'] * 100

            # Mostrar datos detectados
            st.info(f"{icono_estrategia} **Estrategia Detectada:** {estrategia} | **{datos['simbolo']}** | Strike ${datos['strike']} | Expira en {dias_a_expiracion} días")

            # --- CÁLCULOS OBJETIVO ---
            factor_tiempo = dias_a_expiracion / 365.0
            retorno_periodo_pct = (target_annual / 100.0) * factor_tiempo
            prima_total_obj = colateral * retorno_periodo_pct
            prima_accion_obj = prima_total_obj / 100

            # --- RESULTADOS PRINCIPALES ---
            st.markdown("### 🎯 Objetivo")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Prima Mínima (Limit)", f"${prima_accion_obj:.2f}")
            with c2:
                st.metric("Crédito Total", f"${prima_total_obj:.2f}")
            with c3:
                st.metric("Colateral Requerido", f"${colateral:,.0f}")

            st.caption(f"Necesitas un {retorno_periodo_pct*100:.2f}% de retorno en estos {dias_a_expiracion} días para lograr tu {target_annual}% anual.")

            # --- VERIFICADOR DE MERCADO (SEMÁFORO) ---
            st.markdown("---")
            st.markdown("### 🔎 Verificar Mercado")
            
            prima_mercado = st.number_input("¿Cuánto paga el mercado (Mid/Mark)?", value=0.0, step=0.01)

            if prima_mercado > 0:
                # Cálculos Reales
                credito_real = prima_mercado * 100
                retorno_real_absoluto = credito_real / colateral # Decimal (ej 0.005)
                retorno_real_anual = retorno_real_absoluto * (365 / dias_a_expiracion) * 100 # Porcentaje (ej 25.5)

                # Comparación visual
                col_res, col_det = st.columns([2,1])
                
                with col_res:
                    if retorno_real_anual >= target_annual:
                        st.success(f"✅ **¡BUENA OPERACIÓN!**\n\nEl retorno anualizado es **{retorno_real_anual:.2f}%**, superando tu meta de {target_annual}%.")
                    else:
                        st.error(f"❌ **NO CUMPLE OBJETIVO**\n\nEl retorno anualizado es **{retorno_real_anual:.2f}%**, por debajo de tu meta de {target_annual}%.")
                
                with col_det:
                    st.write(f"**Retorno Real en {dias_a_expiracion} días:**")
                    st.write(f"{retorno_real_absoluto*100:.2f}%")

else:
    st.write("waiting for data...")