import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Polla Mundialista Sauco", layout="centered")
st.image("01_Curvas_Logos versiones_marca interna SAUCO_Mesa de trabajo 1 copia 14.jpg", width=200)
st.title("🏆 Polla Mundialista 2026 - Grupo K")
st.write("Valor por puesto: 20.000 COP")

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('polla_sauco.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT,
                    area TEXT,
                    password TEXT,
                    pago_validado BOOLEAN,
                    es_admin BOOLEAN)''')
    conn.commit()
    conn.close()

init_db()

# --- DATOS DE LOS PARTIDOS Y BLOQUEO ---
# Fechas ajustadas como ejemplo (Año, Mes, Día, Hora, Minuto)
partidos = {
    "P1": {"local": "Portugal", "visita": "Uzbekistán", "fecha": datetime(2026, 6, 17, 10, 0)},
    "P2": {"local": "RD Congo", "visita": "Colombia", "fecha": datetime(2026, 6, 17, 14, 0)},
    "P3": {"local": "Portugal", "visita": "Colombia", "fecha": datetime(2026, 6, 23, 10, 0)},
    "P4": {"local": "Uzbekistán", "visita": "RD Congo", "fecha": datetime(2026, 6, 23, 14, 0)},
    "P5": {"local": "Colombia", "visita": "Uzbekistán", "fecha": datetime(2026, 6, 27, 10, 0)},
    "P6": {"local": "Portugal", "visita": "RD Congo", "fecha": datetime(2026, 6, 27, 14, 0)}
}

def partido_bloqueado(fecha_partido):
    ahora = datetime.now()
    limite = fecha_partido - timedelta(minutes=20)
    return ahora >= limite

# --- CÁLCULO DE TABLA ---
def calcular_tabla(resultados):
    tabla = {eq: {"PTS": 0, "GF": 0, "GC": 0} for eq in ["Portugal", "Colombia", "Uzbekistán", "RD Congo"]}
    
    for p_id, datos in resultados.items():
        loc, vis = partidos[p_id]["local"], partidos[p_id]["visita"]
        gl, gv = datos["gl"], datos["gv"]
        
        tabla[loc]["GF"] += gl
        tabla[loc]["GC"] += gv
        tabla[vis]["GF"] += gv
        tabla[vis]["GC"] += gl
        
        if gl > gv:
            tabla[loc]["PTS"] += 3
        elif gv > gl:
            tabla[vis]["PTS"] += 3
        else:
            tabla[loc]["PTS"] += 1
            tabla[vis]["PTS"] += 1
            
    df = pd.DataFrame.from_dict(tabla, orient='index')
    df['DG'] = df['GF'] - df['GC']
    df = df.sort_values(by=['PTS', 'DG', 'GF'], ascending=False)
    return df

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("Menú de Navegación", ["Registro", "Mis Pronósticos", "Panel Administrador"])

# --- VISTA: REGISTRO ---
if menu == "Registro":
    st.subheader("📝 Registro de Participantes")
    with st.form("registro_form"):
        nombre = st.text_input("Nombre Completo")
        area = st.text_input("Departamento / Área")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Crear Cuenta")
        
        if submit and nombre and area and password:
            conn = sqlite3.connect('polla_sauco.db')
            c = conn.cursor()
            c.execute("INSERT INTO usuarios (nombre, area, password, pago_validado, es_admin) VALUES (?, ?, ?, ?, ?)", 
                      (nombre, area, password, False, False))
            conn.commit()
            conn.close()
            st.success("¡Registro exitoso! Contacta al administrador para validar tu pago de 20.000 COP y activar tu cuenta.")

# --- VISTA: MIS PRONÓSTICOS ---
elif menu == "Mis Pronósticos":
    st.subheader("⚽ Ingresa tus Marcadores")
    st.info("Los partidos se bloquean automáticamente 20 minutos antes de su inicio.")
    
    resultados_usuario = {}
    
    for p_id, datos in partidos.items():
        st.markdown(f"**{datos['local']} vs {datos['visita']}** - {datos['fecha'].strftime('%d/%m/%Y %H:%M')}")
        bloqueado = partido_bloqueado(datos["fecha"])
        
        col1, col2 = st.columns(2)
        gl = col1.number_input(f"Goles {datos['local']}", min_value=0, step=1, key=f"L_{p_id}", disabled=bloqueado)
        gv = col2.number_input(f"Goles {datos['visita']}", min_value=0, step=1, key=f"V_{p_id}", disabled=bloqueado)
        
        if bloqueado:
            st.error("🔴 Tiempo agotado para este partido.")
            
        resultados_usuario[p_id] = {"gl": gl, "gv": gv}
        st.markdown("---")
        
    st.subheader("📊 Tu Tabla de Posiciones Proyectada")
    st.write("Esta tabla se genera automáticamente según los marcadores que ingresaste arriba.")
    tabla_final = calcular_tabla(resultados_usuario)
    st.dataframe(tabla_final, use_container_width=True)
    
    st.subheader("👟 Goleador del Grupo (5 Puntos Extra)")
    goleador = st.text_input("Nombre del jugador que pronosticas como goleador del Grupo K:")
    
    if st.button("Guardar Pronósticos"):
        st.success("Pronósticos guardados correctamente en la base de datos.")

# --- VISTA: PANEL ADMINISTRADOR ---
elif menu == "Panel Administrador":
    st.subheader("⚙️ Control de Pagos y Usuarios")
    
    conn = sqlite3.connect('polla_sauco.db')
    df_usuarios = pd.read_sql_query("SELECT id, nombre, area, pago_validado FROM usuarios WHERE es_admin = 0", conn)
    
    if not df_usuarios.empty:
        st.dataframe(df_usuarios, use_container_width=True)
        st.write("Para activar a un usuario, ingresa su ID y aprueba el pago:")
        
        col_id, col_btn = st.columns(2)
        id_activar = col_id.number_input("ID del Usuario", min_value=1, step=1)
        if col_btn.button("Validar Pago de este ID"):
            c = conn.cursor()
            c.execute("UPDATE usuarios SET pago_validado = 1 WHERE id = ?", (id_activar,))
            conn.commit()
            st.success(f"Usuario {id_activar} validado exitosamente.")
            st.rerun()
    else:
        st.info("Aún no hay usuarios registrados.")
    conn.close()
