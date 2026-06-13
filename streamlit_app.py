import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# Configuración inicial de la página
st.set_page_config(page_title="Fondo Común", layout="wide")

st.title("💰 Control de Fondo Común")
st.write("Sincronizado directamente con Google Sheets de forma nativa.")

# Coloca aquí tu URL real de Google Sheets
URL_HOJA = "https://docs.google.com/spreadsheets/d/1-DcC9ooqdSy5YZxPvhdpyYfhfuAvVXLdkgl9p1ZJkLg/edit"

# --- CONEXIÓN PLANA RECONSTRUYENDO EL DICCIONARIO ---
try:
    info_credenciales = {
        "type": st.secrets["gserviceaccount"]["type"],
        "project_id": st.secrets["gserviceaccount"]["project_id"],
        "private_key_id": st.secrets["gserviceaccount"]["private_key_id"],
        # Forzamos la interpretación correcta de los saltos de línea de la llave RSA
        "private_key": st.secrets["gserviceaccount"]["private_key"].replace("\\n", "\n"),
        "client_email": st.secrets["gserviceaccount"]["client_email"],
        "client_id": st.secrets["gserviceaccount"]["client_id"],
        "auth_uri": st.secrets["gserviceaccount"]["auth_uri"],
        "token_uri": st.secrets["gserviceaccount"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gserviceaccount"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gserviceaccount"]["client_x509_cert_url"],
        "universe_domain": st.secrets["gserviceaccount"]["universe_domain"]
    }
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    credenciales = Credentials.from_service_account_info(info_credenciales, scopes=scopes)
    client = gspread.authorize(credenciales)
    sh = client.open_by_url(URL_HOJA)
except Exception as e:
    st.error(f"Error crítico de autenticación con Google: {e}")
    st.stop()

# --- LECTURA SEGURA DE DATOS ---
def cargar_datos_nativos():
    columnas_aportes = ["Fecha", "Persona", "Monto"]
    columnas_gastos = ["Fecha", "Descripción", "Monto", "Pagado Con"]
    
    try:
        ws_aportes = sh.worksheet("Aportes")
        datos_a = ws_aportes.get_all_records()
        df_a = pd.DataFrame(datos_a) if datos_a else pd.DataFrame(columns=columnas_aportes)
    except Exception:
        df_a = pd.DataFrame(columns=columnas_aportes)
        
    try:
        ws_gastos = sh.worksheet("Gastos")
        datos_g = ws_gastos.get_all_records()
        df_g = pd.DataFrame(datos_g) if datos_g else pd.DataFrame(columns=columnas_gastos)
    except Exception:
        df_g = pd.DataFrame(columns=columnas_gastos)
    
    if df_a.empty or "Fecha" not in df_a.columns:
        df_a = pd.DataFrame(columns=columnas_aportes)
    if df_g.empty or "Fecha" not in df_g.columns:
        df_g = pd.DataFrame(columns=columnas_gastos)
        
    return df_a, df_g

df_aportes, df_gastos = cargar_datos_nativos()

# Convertir tipos numéricos para la interfaz
df_aportes["Monto"] = pd.to_numeric(df_aportes["Monto"], errors='coerce').fillna(0.0)
df_gastos["Monto"] = pd.to_numeric(df_gastos["Monto"], errors='coerce').fillna(0.0)

# --- CÁLCULOS CENTRALES ---
total_aportado = df_aportes["Monto"].sum()
total_gastado = df_gastos["Monto"].sum()
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

# --- ENTRADA DE DATOS (ESCRITURA NATIVA) ---
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
                
                # Inyección directa atómica a la hoja de Google
                ws_aportes = sh.worksheet("Aportes")
                ws_aportes.append_row([fecha_str, persona, float(monto_aporte)])
                
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
                ws_gastos = sh.worksheet("Gastos")
                
                if origen_pago == "Fondo Común":
                    ws_gastos.append_row([fecha_str, descripcion, float(monto_gasto), "Fondo Común"])
                else:
                    if quien_pago:
                        ws_aportes = sh.worksheet("Aportes")
                        ws_aportes.append_row([fecha_str, quien_pago, float(monto_gasto)])
                        ws_gastos.append_row([fecha_str, f"{descripcion} (Por {quien_pago})", float(monto_gasto), quien_pago])
                    else:
                        st.error("Debes especificar quién pagó el gasto.")
                        st.stop()
                
                st.success("Gasto guardado con éxito.")
                st.rerun()
            else:
                st.error("Por favor, ingresa una descripción y un monto mayor a cero.")

st.markdown("---")

# --- VISUALIZACIÓN ---
st.subheader("📋 Resumen de Movimientos")
tab1, tab2, tab3 = st.tabs(["Historial de Gastos", "Detalle de Aportes por Persona", "Ver Todo"])

with tab1:
    if not df_gastos.empty:
        st.dataframe(df_gastos, use_container_width=True)
    else:
        st.info("No hay gastos registrados todavía.")

with tab2:
    if not df_aportes.empty:
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
