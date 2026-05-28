import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Agente Comercial Vuelos", layout="wide")

# =============================
# 🎯 SIDEBAR - LOW FACTOR
# =============================
st.sidebar.title("⚙️ Configuración")

low_factor_pct = st.sidebar.slider(
    "Low Factor (%)",
    min_value=50.0,
    max_value=100.0,
    value=78.6,
    step=0.1
)

LOW_FACTOR = low_factor_pct / 100

st.sidebar.write(f"Pasajeros = Sillas × {round(LOW_FACTOR,3)}")

# =============================
# 🔄 ACTUALIZAR MODELO
# =============================
def actualizar_modelo(it_file, vt_file, LOW_FACTOR):

    # --- CARGAR ARCHIVOS ---
    it = pd.read_excel(it_file)
    vt = pd.read_excel(vt_file, sheet_name=1)

    # --- LIMPIAR ITINERARIO ---
    it = it[['Fecha Inicio','hhmmss','Compañía','Vuelo','ORI','DES','Sillas']].copy()
    it.columns = ['FECHA','HORA','AEROLINEA','VUELO','ORIGEN','DESTINO','SILLAS']

    # ✅ SOLUCIÓN ERROR FECHA
    if pd.api.types.is_numeric_dtype(it['FECHA']):
        it['FECHA'] = pd.to_datetime('1899-12-30') + pd.to_timedelta(it['FECHA'], 'D')
    else:
        it['FECHA'] = pd.to_datetime(it['FECHA'], errors='coerce')

    # --- LIMPIAR VENTAS ---
    vt = vt[['FECHA','HORA','AEROLINEA','VUELO','DESTINO','TOTAL','FOLIO']].copy()
    vt['FECHA'] = pd.to_datetime(vt['FECHA'], errors='coerce')

    # ✅ AGRUPACIÓN CORRECTA (CLAVE)
    ventas = vt.groupby(['FECHA','AEROLINEA','VUELO']).agg(
        VENTAS=('TOTAL','sum'),
        TRX=('FOLIO','nunique')
    ).reset_index()

    # --- CRUCE ---
    df = it.merge(ventas, on=['FECHA','AEROLINEA','VUELO'], how='left')

    # --- MÉTRICAS ---
    df['PASAJEROS'] = df['SILLAS'] * LOW_FACTOR
    df['SPP'] = df['VENTAS'] / df['PASAJEROS']
    df['EFECTIVIDAD'] = df['TRX'] / df['PASAJEROS']

    df.fillna(0, inplace=True)

    # --- GUARDAR ---
    df.to_excel("modelo_actualizado.xlsx", index=False)

    return df   # ✅ (IMPORTANTE: DENTRO DE LA FUNCIÓN)

# =============================
# 🤖 AGENTE DE CONSULTAS
# =============================
def consultar(df, query):

    q = query.lower()
    data = df.copy()

    # --- FILTRO DESTINO ---
    for d in df['DESTINO'].unique():
        if str(d).lower() in q:
            data = data[data['DESTINO'] == d]

    # --- FILTRO VUELO ---
    if "vuelo" in q:
        num = ''.join(filter(str.isdigit, q))
        if num:
            data = data[data['VUELO'] == int(num)]

    ventas = data['VENTAS'].sum()
    pasajeros = data['PASAJEROS'].sum()
    trx = data['TRX'].sum()

    spp = ventas / pasajeros if pasajeros else 0
    eff = trx / pasajeros if pasajeros else 0

    # --- RESPUESTAS ---
    if "spp" in q:
        return f"💰 SPP: ${round(spp,2)} USD por pasajero"

    if "efectividad" in q:
        return f"📊 Efectividad: {round(eff*100,2)}%"

    if "ventas" in q:
        return f"💵 Ventas: ${round(ventas,2)} USD"

    if "trx" in q:
        return f"🧾 Transacciones: {int(trx)}"

    if "top" in q or "mejor" in q:
        top = df.sort_values("SPP", ascending=False).head(5)
        return top[['DESTINO','VUELO','SPP']]

    return f"""
📊 Resultado:

💵 Ventas: ${round(ventas,2)}
🧍 Pasajeros: {int(pasajeros)}
🧾 TRX: {int(trx)}

💰 SPP: ${round(spp,2)}
📊 Efectividad: {round(eff*100,2)}%
"""

# =============================
# 🌐 INTERFAZ
# =============================
st.title("✈️🤖 Agente Comercial Inteligente")

st.markdown("Carga archivos, ajusta el factor y consulta como ChatGPT")

# --- CARGA ARCHIVOS ---
it_file = st.file_uploader("📂 Subir Itinerario", type=["xlsx"])
vt_file = st.file_uploader("📂 Subir Ventas", type=["xlsx"])

# --- BOTÓN ACTUALIZAR ---
if it_file and vt_file:
    if st.button("🔄 Actualizar modelo"):
        df = actualizar_modelo(it_file, vt_file, LOW_FACTOR)
        st.success("✅ Modelo actualizado correctamente")

# =============================
# 📊 DASHBOARD + CHAT
# =============================
try:
    df = pd.read_excel("modelo_actualizado.xlsx")

    baja_efectividad = df[df['EFECTIVIDAD'] < 0.01]

    st.divider()

    # DASHBOARD
    st.subheader("📊 Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        ventas_destino = df.groupby("DESTINO")['VENTAS'].sum().reset_index()
        fig1 = px.bar(ventas_destino, x="DESTINO", y="VENTAS",
                      title="Ventas por destino")
        st.plotly_chart(fig1)

    with col2:
        efecto_destino = df.groupby("DESTINO")['EFECTIVIDAD'].mean().reset_index()
        fig2 = px.bar(efecto_destino, x="DESTINO", y="EFECTIVIDAD",
                      title="Efectividad por destino")
        st.plotly_chart(fig2)

    # ALERTAS
    st.subheader("🚨 Alertas")

     if not baja_efectividad.empty:
        st.warning(f"⚠️ {len(baja_efectividad)} vuelos con baja conversión")
    else:
        st.success("✅ No hay alertas críticas")

    # CHAT
    st.subheader("💬 Chat Inteligente")

    query = st.text_input("Escribe tu consulta:")

    if query:
        respuesta = consultar(df, query)

        if isinstance(respuesta, pd.DataFrame):
            st.dataframe(respuesta)
        else:
            st.write(respuesta)

# ✅ ESTE BLOQUE FALTABA
except:
    st.info("👆 Carga archivos y haz clic en 'Actualizar modelo'")


    # ----------------
    # ALERTAS
    # ----------------
    st.subheader("🚨 Alertas")

    baja_efectividad = df[df['EFECTIVIDAD'] < 0.01]

    if not baja_efectividad.empty:
        st.warning(f"⚠️ {len(baja_efectividad)} vuelos con baja conversión")
    else:
        st.success("✅ No hay alertas críticas")

    # ----------------
    # CHAT
    # ----------------
    st.subheader("💬 Chat Inteligente")

    query = st.text_input("Escribe tu consulta:")

    if query:
        respuesta = consultar(df, query)

if isinstance(respuesta, pd.DataFrame):
    st.dataframe(respuesta)
