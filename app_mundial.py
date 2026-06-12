import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Polla Mundialista Sauco", page_icon="🏆", layout="centered")

# Manejo robusto del logo corporativo
try:
    st.image("logo.jpg", width=200)
except:
    st.warning("⚠️ Archivo 'logo.jpg' no detectado en el repositorio. La app continuará ejecutándose.")

st.title("🏆 Polla Mundialista 2026 - Grupo K")
st.write("**Valor por puesto:** $20.000 COP")
st.markdown("---")

# --- 2. BASE DE DATOS E INICIALIZACIÓN ---
def init_db():
    conn = sqlite3.connect('polla_sauco.db')
    c = conn.cursor()
    # Tabla de usuarios
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE,
                    area TEXT,
                    password TEXT,
                    pago_validado BOOLEAN,
                    es_admin BOOLEAN)''')
    # Tabla de pronósticos de usuarios
    c.execute('''CREATE TABLE IF NOT EXISTS pronosticos (
                    usuario_id INTEGER,
                    partido_id TEXT,
                    goles_local INTEGER,
                    goles_visita INTEGER,
                    PRIMARY KEY (usuario_id, partido_id))''')
    # Tabla de goleadores pronosticados
    c.execute('''CREATE TABLE IF NOT EXISTS goleadores_pronosticos (
                    usuario_id INTEGER PRIMARY KEY,
                    goleador TEXT)''')
    # Tabla de resultados reales (Cargados por Admin)
    c.execute('''CREATE TABLE IF NOT EXISTS resultados_reales (
                    partido_id TEXT PRIMARY KEY,
                    goles_local INTEGER,
                    goles_visita INTEGER,
                    jugado BOOLEAN)''')
    # Creación automática del Administrador por defecto si no existe
    c.execute("SELECT * FROM usuarios WHERE nombre='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO usuarios (nombre, area, password, pago_validado, es_admin) VALUES (?, ?, ?, ?, ?)",
                  ('admin', 'Gerencia', 'SaucoAdmin2026*', True, True))
    conn.commit()
    conn.close()

init_db()

# --- 3. CONFIGURACIÓN DE PARTIDOS Y LOGICA DE TIEMPO ---
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

# --- 4. MOTOR INTERNO DE CÁLCULO (TABLA GRUPO K) ---
def generar_tabla_posiciones(diccionario_resultados):
    tabla = {eq: {"PTS": 0, "GF": 0, "GC": 0} for eq in ["Portugal", "Colombia", "Uzbekistán", "RD Congo"]}
    for p_id, datos in diccionario_resultados.items():
        if datos.get("gl") is None or datos.get("gv") is None:
            continue
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

# --- 5. SISTEMA DE GESTIÓN DE SESIONES (AUTH) ---
if 'usuario_autenticado' not in st.session_state:
    st.session_state['usuario_autenticado'] = False
    st.session_state['user_id'] = None
    st.session_state['user_nombre'] = ""
    st.session_state['es_admin'] = False

if not st.session_state['usuario_autenticado']:
    tab1, tab2 = st.tabs(["🔐 Iniciar Sesión", "📝 Registrarse"])
    
    with tab1:
        st.subheader("Acceso al Sistema")
        login_nombre = st.text_input("Usuario (Nombre Completo)", key="login_nom")
        login_pass = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Ingresar", use_container_width=True):
            conn = sqlite3.connect('polla_sauco.db')
            c = conn.cursor()
            c.execute("SELECT id, nombre, password, pago_validado, es_admin FROM usuarios WHERE nombre=?", (login_nombre,))
            user = c.fetchone()
            conn.close()
            
            if user and user[2] == login_pass:
                if not user[3]:
                    st.error("🔒 Tu cuenta está registrada pero aún no ha sido activada. Por favor realiza el pago de $20.000 con el administrador.")
                else:
                    st.session_state['usuario_autenticado'] = True
                    st.session_state['user_id'] = user[0]
                    st.session_state['user_nombre'] = user[1]
                    st.session_state['es_admin'] = bool(user[4])
                    st.success(f"Bienvenido {user[1]}")
                    st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
                
    with tab2:
        st.subheader("Formulario de Inscripción")
        reg_nombre = st.text_input("Nombre Completo (Ej: Daniel Rodríguez)", key="reg_nom")
        reg_area = st.text_input("Área / Departamento Corporativo", key="reg_area")
        reg_pass = st.text_input("Crea una Contraseña", type="password", key="reg_pass")
        if st.button("Enviar Registro", use_container_width=True):
            if reg_nombre and reg_area and reg_pass:
                conn = sqlite3.connect('polla_sauco.db')
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO usuarios (nombre, area, password, pago_validado, es_admin) VALUES (?, ?, ?, ?, ?)", 
                              (reg_nombre, reg_area, reg_pass, False, False))
                    conn.commit()
                    st.success("¡Registro completado! Tu cuenta se activará cuando el administrador verifique el pago.")
                except sqlite3.IntegrityError:
                    st.error("Este nombre ya se encuentra registrado.")
                conn.close()
            else:
                st.error("Todos los campos son obligatorios.")
    st.stop()

# --- 6. INTERFAZ PARA USUARIOS AUTENTICADOS ---
st.sidebar.markdown(f"👤 **Usuario:** {st.session_state['user_nombre']}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state['usuario_autenticado'] = False
    st.rerun()

# Definición de opciones del menú según el rol
opciones_menu = ["🏆 Tabla de Posiciones Usuarios", "⚽ Mis Pronósticos"]
if st.session_state['es_admin']:
    opciones_menu.append("⚙️ Panel de Administrador")

menu = st.sidebar.radio("Navegación", opciones_menu)

# --- VISTA 1: TABLA DE POSICIONES DE PARTICIPANTES (LEADERBOARD) ---
if menu == "🏆 Tabla de Posiciones Usuarios":
    st.subheader("📊 Clasificación General de la Polla")
    
    # Cargar datos reales
    conn = sqlite3.connect('polla_sauco.db')
    c = conn.cursor()
    c.execute("SELECT partido_id, goles_local, goles_visita FROM resultados_reales WHERE jugado=1")
    reales_raw = c.fetchall()
    dict_reales = {r[0]: {"gl": r[1], "gv": r[2]} for r in reales_raw}
    tabla_real = generar_tabla_posiciones(dict_reales)
    
    # Cargar todos los usuarios que pagaron
    c.execute("SELECT id, nombre, area FROM usuarios WHERE es_admin=0 AND pago_validado=1")
    usuarios_validos = c.fetchall()
    
    ranking_data = []
    
    for u_id, u_nombre, u_area in usuarios_validos:
        puntos_usuario = 0
        goles_exactos_totales = 0
        
        # Evaluar partidos individuales
        c.execute("SELECT partido_id, goles_local, goles_visita FROM pronosticos WHERE usuario_id=?", (u_id,))
        pronos_user = {p[0]: {"gl": p[1], "gv": p[2]} for p in c.fetchall()}
        tabla_usuario = generar_tabla_posiciones(pronos_user)
        
        for p_id, r_real in dict_reales.items():
            if p_id in pronos_user:
                r_user = pronos_user[p_id]
                # Marcador exacto (3 pts)
                if r_user["gl"] == r_real["gl"] and r_user["gv"] == r_real["gv"]:
                    puntos_usuario += 3
                    goles_exactos_totales += 1
                # Solo resultado V/E/D (1 pt)
                elif (r_user["gl"] > r_user["gv"] and r_real["gl"] > r_real["gv"]) or \
                     (r_user["gl"] < r_user["gv"] and r_real["gl"] < r_real["gv"]) or \
                     (r_user["gl"] == r_user["gv"] and r_real["gl"] == r_real["gv"]):
                    puntos_usuario += 1
                    
        # Evaluar posiciones de la tabla si el torneo ha concluído o tiene avances
        if len(dict_reales) >= 6:
            for idx, (equipo, fila_real) in enumerate(tabla_real.iterrows()):
                if equipo in tabla_usuario.index:
                    idx_user = tabla_usuario.index.get_loc(equipo)
                    # Posición exacta (3 pts)
                    if idx == idx_user:
                        puntos_usuario += 3
                    # Zona de clasificación 1º o 2º lugar (1 pt)
                    if idx in [0, 1] and idx_user in [0, 1]:
                        puntos_usuario += 1
                    # Variables exactas (PTS, GF, GC)
                    fila_user = tabla_usuario.loc[equipo]
                    if fila_user["PTS"] == fila_real["PTS"]: puntos_usuario += 1
                    if fila_user["GF"] == fila_real["GF"]: puntos_usuario += 1
                    if fila_user["GC"] == fila_real["GC"]: puntos_usuario += 1
                    
        ranking_data.append({
            "Participante": u_nombre,
            "Área": u_area,
            "Puntos Totales": puntos_usuario,
            "Marcadores Exactos Acertados": goles_exactos_totales
        })
        
    conn.close()
    
    if ranking_data:
        df_ranking = pd.DataFrame(ranking_data)
        # Criterio de desempate automático según reglas
        df_ranking = df_ranking.sort_values(by=["Puntos Totales", "Marcadores Exactos Acertados"], ascending=False)
        st.dataframe(df_ranking, use_container_width=True)
    else:
        st.info("La tabla se activará cuando los participantes confirmados comiencen a puntuar.")

# --- VISTA 2: FORMULARIO DE PRONÓSTICOS DE USUARIOS ---
elif menu == "⚽ Mis Pronósticos":
    st.subheader("Registra o Edita tus Marcadores")
    st.info("🕒 Cierre automático del formulario: 20 minutos antes de cada partido.")
    
    conn = sqlite3.connect('polla_sauco.db')
    c = conn.cursor()
    
    # Cargar pronósticos previos si existen
    c.execute("SELECT partido_id, goles_local, goles_visita FROM pronosticos WHERE usuario_id=?", (st.session_state['user_id'],))
    pronos_existentes = {row[0]: (row[1], row[2]) for row in c.fetchall()}
    
    resultados_usuario = {}
    
    with st.form("form_pronosticos"):
        for p_id, datos in partidos.items():
            st.markdown(f"**{datos['local']} vs {datos['visita']}**")
            st.caption(f"📅 Fecha programada: {datos['fecha'].strftime('%d/%m/%Y %H:%M')}")
            
            bloqueado = partido_bloqueado(datos["fecha"])
            val_l, val_v = pronos_existentes.get(p_id, (0, 0))
            
            col1, col2 = st.columns(2)
            gl = col1.number_input(f"Goles {datos['local']}", min_value=0, step=1, value=val_l, key=f"L_{p_id}", disabled=bloqueado)
            gv = col2.number_input(f"Goles {datos['visita']}", min_value=0, step=1, value=val_v, key=f"V_{p_id}", disabled=bloqueado)
            
            if bloqueado:
                st.error("🔴 Bloqueado de manera definitiva.")
                
            resultados_usuario[p_id] = {"gl": gl, "gv": gv}
            st.markdown("---")
            
        st.subheader("📊 Tabla de Posiciones Proyectada Automáticamente")
        tabla_final = generar_tabla_posiciones(resultados_usuario)
        st.dataframe(tabla_final, use_container_width=True)
        
        # Goleador
        c.execute("SELECT goleador FROM goleadores_pronosticos WHERE usuario_id=?", (st.session_state['user_id'],))
        gol_row = c.fetchone()
        val_gol = gol_row[0] if gol_row else ""
        goleador = st.text_input("👟 Proyección Goleador del Grupo K (+5 puntos):", value=val_gol)
        
        guardar = st.form_submit_button("💾 Guardar y Actualizar Pronósticos")
        
        if guardar:
            for p_id, goles in resultados_usuario.items():
                if not partido_bloqueado(partidos[p_id]["fecha"]):
                    c.execute('''INSERT INTO pronosticos (usuario_id, partido_id, goles_local, goles_visita)
                                 VALUES (?, ?, ?, ?) ON CONFLICT(usuario_id, partido_id) 
                                 DO UPDATE SET goles_local=excluded.goles_local, goles_visita=excluded.goles_visita''',
                              (st.session_state['user_id'], p_id, goles["gl"], goles["gv"]))
            if goleador:
                c.execute('''INSERT INTO goleadores_pronosticos (usuario_id, goleador) VALUES (?, ?)
                             ON CONFLICT(usuario_id) DO UPDATE SET goleador=excluded.goleador''', 
                          (st.session_state['user_id'], goleador))
            conn.commit()
            st.success("¡Tus marcadores y proyecciones han sido guardados de manera segura!")
            st.rerun()
            
    conn.close()

# --- VISTA 3: PANEL EXCLUSIVO DEL ADMINISTRADOR ---
elif menu == "⚙️ Panel de Administrador" and st.session_state['es_admin']:
    st.subheader("Administración General de Usuarios y Resultados")
    
    tab_pago, tab_res = st.tabs(["💵 Validar Recaudos ($20.000)", "⚽ Cargar Resultados Reales"])
    
    conn = sqlite3.connect('polla_sauco.db')
    c = conn.cursor()
    
    with tab_pago:
        df_usuarios = pd.read_sql_query("SELECT id, nombre, area, pago_validado FROM usuarios WHERE es_admin = 0", conn)
        if not df_usuarios.empty:
            st.dataframe(df_usuarios, use_container_width=True)
            id_activar = st.number_input("Ingresa el ID del usuario a activar:", min_value=1, step=1)
            if st.button("✅ Habilitar Participante"):
                c.execute("UPDATE usuarios SET pago_validado = 1 WHERE id = ?", (id_activar,))
                conn.commit()
                st.success(f"Usuario con ID {id_activar} habilitado para jugar.")
                st.rerun()
        else:
            st.info("No se registran participantes en la base de datos.")
            
    with tab_res:
        st.write("Registra los marcadores oficiales de los partidos de la FIFA:")
        c.execute("SELECT partido_id, goles_local, goles_visita, jugado FROM resultados_reales")
        reales_guardados = {row[0]: (row[1], row[2], row[3]) for row in c.fetchall()}
        
        for p_id, datos in partidos.items():
            st.markdown(f"**{datos['local']} vs {datos['visita']}**")
            g_l_prev, g_v_prev, jugado_prev = reales_guardados.get(p_id, (0, 0, False))
            
            col1, col2, col3 = st.columns(3)
            gl_real = col1.number_input(f"Goles Reales {datos['local']}", min_value=0, step=1, value=g_l_prev, key=f"R_L_{p_id}")
            gv_real = col2.number_input(f"Goles Reales {datos['visita']}", min_value=0, step=1, value=g_v_prev, key=f"R_V_{p_id}")
            marcar_jugado = col3.checkbox("¿Partido Concluido?", value=jugado_prev, key=f"J_{p_id}")
            
            if st.button(f"Guardar Resultado {p_id}"):
                c.execute('''INSERT INTO resultados_reales (partido_id, goles_local, goles_visita, jugado)
                             VALUES (?, ?, ?, ?) ON CONFLICT(partido_id)
                             DO UPDATE SET goles_local=excluded.goles_local, goles_visita=excluded.goles_visita, jugado=excluded.jugado''',
                          (p_id, gl_real, gv_real, marcar_jugado))
                conn.commit()
                st.success("Resultado oficial cargado y base de puntuación actualizada.")
                st.rerun()
                
    conn.close()
