import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Configuración inicial de la página
st.set_page_config(page_title="Fondo Común - Google Sheets", layout="wide")

st.title("💰 Control de Fondo Común")
st.write("Sincronizado permanentemente con Google Sheets.")

# Tu URL de Google Sheets
URL_HOJA = "AQUÍ_VA_TU_URL_COMPLETA_DE_GOOGLE_SHEETS"

# --- CONEXIÓN A GOOGLE SHEETS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Error al conectar con Google Sheets. Verifica los Secrets en Streamlit.")
    st.stop()

# --- FUNCIONES PARA LEER Y ESCRIBIR ---
def cargar_datos():
    columnas_aportes = ["Fecha", "Persona", "Monto"]
    columnas_gastos = ["Fecha", "Descripción", "Monto", "Pagado Con"]
    
    try:
        # Forzamos la lectura limpia
        df_a = conn.read(spreadsheet=URL_HOJA, worksheet="Aportes", ttl="0d")
        if df_a is None or df_a.empty or "Fecha" not in df_a.columns:
            df_a = pd.DataFrame(columns=columnas_aportes)
    except Exception:
        df_a = pd.DataFrame(columns=columnas_aportes)
        
    try:
        df_g = conn.read(spreadsheet=URL_HOJA, worksheet="Gastos", ttl="0d")
        if df_g is None or df_g.empty or "Fecha" not in df_g.columns:
            df_g = pd.DataFrame(columns=columnas_gastos)
    except Exception:
        df_g = pd.DataFrame(columns=columnas_gastos)
        
    # Limpieza estricta de nombres de columnas y eliminación de filas completamente vacías
    df_a.columns = df_a.columns.str.strip()
    df_g.columns = df_g.columns.str.strip()
    df_a = df_a.dropna(how="all")
    df_g = df_g.dropna(how="all")
    
    return df_a, df_g

df_aportes, df_gastos = cargar_datos()

# Asegurar tipos de datos correctos
df_aportes["Monto"] = pd.to_numeric(df_aportes["Monto"], errors='coerce').fillna(0.0)
df_gastos["Monto"] = pd.to_numeric(df_gastos["Monto"], errors='coerce').fillna(0.0)

# Re-ordenar y asegurar que los DataFrames tengan la estructura exacta de columnas
df_aportes = df_aportes[["Fecha", "Persona", "Monto"]].astype(str)
df_gastos = df_gastos[["Fecha", "Descripción", "Monto", "Pagado Con"]].astype(str)

# --- CÁLCULOS CENTRALES ---
total_aportado = pd.to_numeric(df_aportes["Monto"]).sum()
total_gastado = pd.to_numeric(df_gastos["Monto"]).sum()
saldo_actual = total_aportado - total_gastado

# --- PANEL DE CONTROL ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Total Recogido (Bolsa)", value=f"${total_aportado:,.2f}")
with col2:
    st.metric(label="Total Gastado", value=f"${total_gastado:,.2f}")
with col3:
    st.metric(label="Saldo Disponible", value=f"${saldo_actual:,.2f}", 
              delta=f"${saldo_actual:,.2f}", delta_color="normal" if saldo_actual >= 0 else "inverse")

st.markdown("---")

# --- ENTRADA DE DATOS ---
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("➕ Registrar Aporte")
    with st.form("form_aporte", clear_on_submit=True):
        persona = st.text_input("Nombre de la persona").strip()
        monto_aporte = st.number_input("Monto aportado", min_value=0.0, step=1000.0)
        submit_aporte = st.form_submit_button("Guardar Aporte")
        
        if submit_aporte:
            if persona and monto_aporte > 0:
                fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                # Crear nuevo registro
                nuevo_aporte = pd.DataFrame([[fecha_str, persona, str(float(monto_aporte))]], columns=["Fecha", "Persona", "Monto"])
                df_actualizado = pd.concat([df_aportes, nuevo_aporte], ignore_index=True)
                
                # CRUCIAL: Añadimos 'clear=True' para que limpie la hoja antes de reescribir y evitar el error
                conn.update(spreadsheet=URL_HOJA, worksheet="Aportes", data=df_actualizado, clear=True)
                st.success(f"Aporte de {persona} guardado con éxito.")
                st.rerun()
            else:
                st.error("Por favor, ingresa un nombre válido y un monto mayor a cero.")

with col_der:
    st.subheader("💸 Registrar Gasto")
    with st.form("form_gasto", clear_on_submit=True):
        descripcion = st.text_input("Concepto o descripción del gasto").strip()
        monto_gasto = st.number_input("Monto del gasto", min_value=0.0, step=1000.0)
        origen_pago = st.selectbox("¿Cómo se pagó?", ["Fondo Común", "Reembolsar a alguien (Aportado individualmente)"])
        quien_pago = ""
        if origen_pago == "Reembolsar a alguien (Aportado individualmente)":
            quien_pago = st.text_input("¿Quién lo pagó de su bolsillo?").strip()

        submit_gasto = st.form_submit_button("Guardar Gasto")
        
        if submit_gasto:
            if descripcion and monto_gasto > 0:
                fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                if origen_pago == "Fondo Común":
                    nuevo_gasto = pd.DataFrame([[fecha_str, descripcion, str(float(monto_gasto)), "Fondo Común"]], columns=["Fecha", "Descripción", "Monto", "Pagado Com"])
                    df_gastos_act = pd.concat([df_gastos, nuevo_gasto], ignore_index=True)
                    conn.update(spreadsheet=URL_HOJA, worksheet="Gastos", data=df_gastos_act, clear=True)
                else:
                    if quien_pago:
                        nuevo_aporte = pd.DataFrame([[fecha_str, quien_pago, str(float(monto_gasto))]], columns=["Fecha", "Persona", "Monto"])
                        nuevo_gasto = pd.DataFrame([[fecha_str, f"{descripcion} (Por {quien_pago})", str(float(monto_gasto)), quien_pago]], columns=["Fecha", "Descripción", "Monto", "Pagado Con"])
                        
                        df_aportes_act = pd.concat([df_aportes, nuevo_aporte], ignore_index=True)
                        df_gastos_act = pd.concat([df_gastos, nuevo_gasto], ignore_index=True)
                        
                        conn.update(spreadsheet=URL_HOJA, worksheet="Aportes", data=df_aportes_act, clear=True)
                        conn.update(spreadsheet=URL_HOJA, worksheet="Gastos", data=df_gastos_act, clear=True)
                    else:
                        st.error("Debes especificar quién pagó el gasto.")
                        st.stop()
                
                st.success("Gasto guardado con éxito.")
                st.rerun()
            else:
                st.error("Por favor, ingresa una descripción y un monto mayor a cero.")

st.markdown("---")

# --- VISUALIZACIÓN DE HISTORIALES ---
st.subheader("📋 Resumen de Movimientos")
tab1, tab2, tab3 = st.tabs(["Historial de Gastos", "Detalle de Aportes por Persona", "Ver Todo"])

with tab1:
    if not df_gastos.empty and total_gastado > 0:
        st.dataframe(df_gastos, use_container_width=True)
    else:
        st.info("No hay gastos registrados todavía.")

with tab2:
    if not df_aportes.empty and total_aportado > 0:
        # Convertir temporalmente a numérico para agrupar en la vista
        df_ver_aportes = df_aportes.copy()
        df_ver_aportes["Monto"] = pd.to_numeric(df_ver_aportes["Monto"])
        resumen_personas = df_ver_aportes.groupby("Persona")["Monto"].sum().reset_index()
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
