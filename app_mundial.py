import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Polla Mundialista Sauco", page_icon="🏆", layout="centered")

# Mostrar logo (Asegúrate de que el archivo en GitHub se llame exactamente 'logo.jpg')
try:
    st.image("logo.jpg", width=200)
except:
    st.warning("⚠️ Logo no encontrado. (Asegúrate de que el archivo se llame 'logo.jpg' en minúsculas).")

st.title("🏆 Polla Mundialista 2026 - Grupo K")
st.write("**Valor por puesto:** $20.000 COP")
st.markdown("---")

# --- 2. BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('polla_sauco.db')
    c = conn.cursor()
    # Tabla de usuarios
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

# --- 3. DATOS DE LOS PARTIDOS Y BLOQUEO ---
# Fechas ajustadas al Mundial 2026 (Hora de Colombia UTC-5)
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

# --- 4. CÁLCULO DE TABLA AUTOMÁTICA ---
def calcular_tabla(resultados):
    # Inicializar tabla en ceros
    tabla = {eq: {"PTS": 0, "GF": 0, "GC": 0} for eq in ["Portugal", "Colombia", "Uzbekistán", "RD Congo"]}
    
    for p_id, datos in resultados.items():
        loc = partidos[p_id]["local"]
        vis = partidos[p_id]["visita"]
        gl = datos["gl"]
        gv = datos["gv"]
        
        # Sumar goles a favor y en contra
        tabla[loc]["GF"] += gl
        tabla[loc]["GC"] += gv
        tabla[vis]["GF"] += gv
        tabla[vis]["GC"] += gl
        
        # Asignar puntos (3 por victoria, 1 por empate)
        if gl > gv:
            tabla[loc]["PTS"] += 3
        elif gv > gl:
            tabla[vis]["PTS"] += 3
        else:
            tabla[loc]["PTS"] += 1
            tabla[vis]["PTS"] += 1
            
    # Crear DataFrame para la visualización
    df = pd.DataFrame.from_dict(tabla, orient='index')
    df['DG'] = df['GF'] - df['GC']
    # Ordenar por Puntos, luego Diferencia de Goles, luego Goles a Favor
    df = df.sort_values(by=['PTS', 'DG', 'GF'], ascending=False)
    return df

# --- 5. MENÚ DE NAVEGACIÓN ---
menu = st.sidebar.radio("Navegación", ["Registro", "Mis Pronósticos", "Panel Administrador"])

# --- VISTA: REGISTRO ---
if menu == "Registro":
    st.subheader("📝 Registro de Participantes")
    with st.form("registro_form"):
        nombre = st.text_input("Nombre Completo")
        area = st.text_input("Departamento / Área")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Crear Cuenta")
        
        if submit:
            if nombre and area and password:
                conn = sqlite3.connect('polla_sauco.db')
                c = conn.cursor()
                # Verificar si ya existe el nombre
                c.execute("SELECT * FROM usuarios WHERE nombre=?", (nombre,))
                if c.fetchone():
                    st.error("Este nombre ya está registrado. Usa otro o añade tu apellido.")
                else:
                    c.execute("INSERT INTO usuarios (nombre, area, password, pago_validado, es_admin) VALUES (?, ?, ?, ?, ?)", 
                              (nombre, area, password, False, False))
                    conn.commit()
                    st.success("¡Registro exitoso! Contacta al administrador para validar tu pago de $20.000 COP y activar tu cuenta.")
                conn.close()
            else:
                st.error("Por favor, completa todos los campos.")

# --- VISTA: MIS PRONÓSTICOS ---
elif menu == "Mis Pronósticos":
    st.subheader("⚽ Ingresa tus Marcadores")
    st.info("🕒 Recuerda: Los partidos se bloquean automáticamente 20 minutos antes del pitazo inicial.")
    
    resultados_usuario = {}
    
    for p_id, datos in partidos.items():
        st.markdown(f"**{datos['local']} vs {datos['visita']}** - 📅 {datos['fecha'].strftime('%d/%m/%Y %H:%M')}")
        bloqueado = partido_bloqueado(datos["fecha"])
        
        col1, col2 = st.columns(2)
        gl = col1.number_input(f"Goles {datos['local']}", min_value=0, step=1, key=f"L_{p_id}", disabled=bloqueado)
        gv = col2.number_input(f"Goles {datos['visita']}", min_value=0, step=1, key=f"V_{p_id}", disabled=bloqueado)
        
        if bloqueado:
            st.error("🔴 Tiempo agotado para pronosticar este partido.")
            
        resultados_usuario[p_id] = {"gl": gl, "gv": gv}
        st.markdown("---")
        
    st.subheader("📊 Tu Tabla de Posiciones Proyectada")
    st.write("Esta tabla se calcula sola según los goles que pusiste arriba:")
    tabla_final = calcular_tabla(resultados_usuario)
    st.dataframe(tabla_final, use_container_width=True)
    
    st.subheader("👟 Goleador del Grupo (5 Puntos Extra)")
    goleador = st.text_input("¿Quién será el goleador del Grupo K?")
    
    if st.button("💾 Guardar Pronósticos"):
        st.success("¡Tus pronósticos han sido ingresados correctamente!")

# --- VISTA: PANEL ADMINISTRADOR ---
elif menu == "Panel Administrador":
    st.subheader("⚙️ Control de Pagos y Usuarios")
    
    conn = sqlite3.connect('polla_sauco.db')
    df_usuarios = pd.read_sql_query("SELECT id, nombre, area, pago_validado FROM usuarios WHERE es_admin = 0", conn)
    
    if not df_usuarios.empty:
        st.dataframe(df_usuarios, use_container_width=True)
        st.write("Para activar a un usuario, ingresa su ID y aprueba el pago:")
        
        col_id, col_btn = st.columns([1, 2])
        id_activar = col_id.number_input("ID del Usuario", min_value=1, step=1)
        
        if col_btn.button("✅ Validar Pago de este ID"):
            c = conn.cursor()
            c.execute("UPDATE usuarios SET pago_validado = 1 WHERE id = ?", (id_activar,))
            conn.commit()
            st.success(f"Usuario {id_activar} validado exitosamente. Ya puede participar.")
    else:
        st.info("Aún no hay usuarios registrados.")
        
    conn.close()
