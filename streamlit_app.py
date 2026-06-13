import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración inicial de la página
st.set_page_config(page_title="Control de Fondo Común", layout="wide")

st.title("💰 Control de Fondo Común y Gastos Compartidos")
st.write("Gestiona la bolsa de dinero de tu grupo, registra aportes y controla los gastos.")

# Inicializar el estado de la aplicación si no existe
if "aportes" not in st.session_state:
    st.session_state.aportes = []
if "gastos" not in st.session_state:
    st.session_state.gastos = []

# --- CÁLCULOS CENTRALES ---
df_aportes = pd.DataFrame(st.session_state.aportes, columns=["Fecha", "Persona", "Monto"])
df_gastos = pd.DataFrame(st.session_state.gastos, columns=["Fecha", "Descripción", "Monto", "Pagado Con"])

total_aportado = df_aportes["Monto"].sum() if not df_aportes.empty else 0.0
total_gastado = df_gastos["Monto"].sum() if not df_gastos.empty else 0.0
saldo_actual = total_aportado - total_gastado

# --- PANEL DE CONTROL (MÉTRICAS) ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Total Recogido (Bolsa)", value=f"${total_aportado:,.2f}")
with col2:
    st.metric(label="Total Gastado", value=f"${total_gastado:,.2f}")
with col3:
    # Cambia a color de alerta si el saldo es negativo
    st.metric(label="Saldo Disponible", value=f"${saldo_actual:,.2f}", 
              delta=f"${saldo_actual:,.2f}", delta_color="normal" if saldo_actual >= 0 else "inverse")

st.markdown("---")

# --- ENTRADA DE DATOS ---
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("➕ Registrar Aporte")
    with st.form("form_aporte", clear_on_submit=True):
        persona = st.text_input("Nombre de la persona").strip()
        monto_aporte = st.number_input("Monto aportado", min_value=0.0, step=5000.0)
        submit_aporte = st.form_submit_button("Guardar Aporte")
        
        if submit_aporte:
            if persona and monto_aporte > 0:
                fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.session_state.aportes.append([fecha_str, persona, monto_aporte])
                st.success(f"Aporte de {persona} registrado con éxito.")
                st.rerun()
            else:
                st.error("Por favor, ingresa un nombre válido y un monto mayor a cero.")

with col_der:
    st.subheader("💸 Registrar Gasto")
    with st.form("form_gasto", clear_on_submit=True):
        descripcion = st.text_input("Concepto o descripción del gasto").strip()
        monto_gasto = st.number_input("Monto del gasto", min_value=0.0, step=5000.0)
        
        # Opciones para definir de dónde sale el dinero
        origen_pago = st.selectbox("¿Cómo se pagó?", ["Fondo Común", "Reembolsar a alguien (Aportado individualmente)"])
        quien_pago = ""
        if origen_pago == "Reembolsar a alguien (Aportado individualmente)":
            quien_pago = st.text_input("¿Quién lo pagó de su bolsillo?").strip()

        submit_gasto = st.form_submit_button("Guardar Gasto")
        
        if submit_gasto:
            if descripcion and monto_gasto > 0:
                fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                if origen_pago == "Fondo Común":
                    # El gasto se resta directamente de la bolsa común
                    st.session_state.gastos.append([fecha_str, descripcion, monto_gasto, "Fondo Común"])
                    st.success(f"Gasto '{descripcion}' registrado contra el Fondo Común.")
                else:
                    if quien_pago:
                        # Si alguien lo pagó de su bolsillo, equivale a que hizo un aporte y luego se generó el gasto
                        st.session_state.aportes.append([fecha_str, quien_pago, monto_gasto])
                        st.session_state.gastos.append([fecha_str, f"{descripcion} (Por {quien_pago})", monto_gasto, quien_pago])
                        st.success(f"Gasto registrado. Se añadió un aporte automático a favor de {quien_pago}.")
                    else:
                        st.error("Debes especificar quién pagó el gasto para poder reembolsarle.")
                        st.stop()
                st.rerun()
            else:
                st.error("Por favor, ingresa una descripción y un monto mayor a cero.")

st.markdown("---")

# --- VISUALIZACIÓN DE HISTORIALES ---
st.subheader("📋 Resumen de Movimientos")
tab1, tab2, tab3 = st.tabs(["Historial de Gastos", "Detalle de Aportes por Persona", "Ver Todo"])

with tab1:
    if not df_gastos.empty:
        st.dataframe(df_gastos, use_container_width=True)
    else:
        st.info("No hay gastos registrados todavía.")

with tab2:
    if not df_aportes.empty:
        # Agrupar para ver cuánto ha puesto cada persona en total
        resumen_personas = df_aportes.groupby("Persona")["Monto"].sum().reset_index()
        resumen_personas = resumen_personas.sort_values(by="Monto", ascending=False)
        st.dataframe(resumen_personas, use_container_width=True)
    else:
        st.info("No hay aportes registrados todavía.")

with tab3:
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.write("**Todos los Aportes**")
        st.dataframe(df_aportes, use_container_width=True)
    with col_t2:
        st.write("**Todos los Gastos**")
        st.dataframe(df_gastos, use_container_width=True)
