import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Agente Comercial Vuelos", layout="wide")

# =============================
# SIDEBAR
# =============================
st.sidebar.title("⚙️ Configuración")

low_factor_pct = st.sidebar.slider(
    "Low Factor (%)",
    50.0, 100.0, 78.6, 0.1
)

LOW_FACTOR = low_factor_pct / 100

st.sidebar.write(f"Pasajeros = Sillas × {round(LOW_FACTOR,3)}")

# =============================
# ACTUALIZAR MODELO
# =============================
def actualizar_modelo(it_file, vt_file, LOW_FACTOR):

    it = pd.read_excel(it_file)
    vt = pd.read_excel(vt_file, sheet_name=1)

    it = it[['Fecha Inicio','hhmmss','Compañía','Vuelo','ORI','DES','Sillas']]
    it.columns = ['FECHA','HORA','AEROLINEA','VUELO','ORIGEN','DESTINO','SILLAS']

    # detectar si viene como número o fecha
if pd.api.types.is_numeric_dtype(it['FECHA']):
    it['FECHA'] = pd.to_datetime('1899-12-30') + pd.to_timedelta(it['FECHA'], 'D')
else:
    it['FECHA'] = pd.to_datetime(it['FECHA'], errors='coerce')


    vt = vt[['FECHA','HORA','AEROLINEA','VUELO','DESTINO','TOTAL','FOLIO']]
    vt['FECHA'] = pd.to_datetime(vt['FECHA'])

    ventas = vt.groupby(['FECHA','AEROLINEA','VUELO']).agg(
        VENTAS=('TOTAL','sum'),
        TRX=('FOLIO','nunique')
    ).reset_index()

    df = it.merge(ventas, on=['FECHA','AEROLINEA','VUELO'], how='left')

    df['PASAJEROS'] = df['SILLAS'] * LOW_FACTOR
    df['SPP'] = df['VENTAS'] / df['PASAJEROS']
    df['EFECTIVIDAD'] = df['TRX'] / df['PASAJEROS']

    df.fillna(0, inplace=True)

    df.to_excel("modelo_actualizado.xlsx", index=False)

    return df

# =============================
# AGENTE CHAT
# =============================
def consultar(df, query):

    q = query.lower()
    data = df.copy()

    for d in df['DESTINO'].unique():
        if d.lower() in q:
            data = data[data['DESTINO'] == d]

    if "vuelo" in q:
        num = ''.join(filter(str.isdigit, q))
        if num:
            data = data[data['VUELO'] == int(num)]

    ventas = data['VENTAS'].sum()
    pax = data['PASAJEROS'].sum()
    trx = data['TRX'].sum()

    spp = ventas / pax if pax else 0
    eff = trx / pax if pax else 0

    if "spp" in q:
        return f"💰 SPP: ${round(spp,2)}"

    if "efectividad" in q:
        return f"📊 Efectividad: {round(eff*100,2)}%"

    if "top" in q or "mejor" in q:
        top = df.sort_values("SPP", ascending=False).head(5)
        return top[['DESTINO','VUELO','SPP']]

    return f"""
Ventas: ${round(ventas,2)}
Pasajeros: {int(pax)}
TRX: {int(trx)}

SPP: ${round(spp,2)}
Efectividad: {round(eff*100,2)}%
"""

# =============================
# INTERFAZ
# =============================
st.title("✈️🤖 Agente Comercial Inteligente")

it_file = st.file_uploader("Subir Itinerario")
vt_file = st.file_uploader("Subir Ventas")

if it_file and vt_file:

    if st.button("Actualizar modelo"):
        df = actualizar_modelo(it_file, vt_file, LOW_FACTOR)
        st.success("✅ Modelo actualizado")

# =============================
# DASHBOARD + CHAT
# =============================
try:
    df = pd.read_excel("modelo_actualizado.xlsx")

    st.divider()
    st.subheader("📊 Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(df.groupby("DESTINO")['VENTAS'].sum().reset_index(),
                     x="DESTINO", y="VENTAS", title="Ventas por destino")
        st.plotly_chart(fig)

    with col2:
        fig2 = px.bar(df.groupby("DESTINO")['EFECTIVIDAD'].mean().reset_index(),
                      x="DESTINO", y="EFECTIVIDAD", title="Efectividad")
        st.plotly_chart(fig2)

    # ALERTAS
    st.subheader("🚨 Alertas")

    low_eff = df[df['EFECTIVIDAD'] < 0.01]

    if not low_eff.empty:
        st.warning(f"{len(low_eff)} vuelos con baja conversión")

    # CHAT
    st.subheader("💬 Chat Inteligente")

    query = st.text_input("Pregunta:")

    if query:
        resp = consultar(df, query)

        if isinstance(resp, pd.DataFrame):
            st.dataframe(resp)
        else:
            st.write(resp)

except:
    st.info("Carga archivos para iniciar")
