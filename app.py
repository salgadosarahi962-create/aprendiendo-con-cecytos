from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'educaplus-secreto-2026'

DB = 'educaplus.db'

MATERIAS = {
    'matematicas': {
        'nombre': 'Matemáticas',
        'descripcion': 'Números, álgebra, geometría y probabilidad.',
        'temas': [
            'Números reales y sus operaciones',
            'Fracciones, decimales y porcentajes',
            'Jerarquía de operaciones',
            'Razones y proporciones',
            'Lenguaje algebraico',
            'Expresiones algebraicas',
            'Ecuaciones de primer grado',
            'Sistemas de ecuaciones',
            'Geometría y cálculo de áreas',
            'Estadística y probabilidad'
        ]
    },
    'espanol': {
        'nombre': 'Español',
        'descripcion': 'Lectura, escritura, gramática y ortografía.',
        'temas': [
            'Comunicación y elementos del proceso comunicativo',
            'Funciones del lenguaje',
            'Tipos de textos',
            'Reglas de acentuación',
            'Signos de puntuación',
            'Categorías gramaticales',
            'Oraciones simples y compuestas',
            'Comprensión lectora',
            'Textos argumentativos',
            'Ortografía y redacción'
        ]
    }
}

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            correo TEXT UNIQUE NOT NULL,
            edad INTEGER,
            especialidad TEXT,
            clave TEXT NOT NULL,
            puntos INTEGER DEFAULT 0,
            racha INTEGER DEFAULT 0,
            ultima_actividad TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            correo TEXT NOT NULL,
            nombre TEXT NOT NULL,
            materia TEXT NOT NULL,
            numero INTEGER NOT NULL,
            calificacion REAL NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS logros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            correo TEXT NOT NULL,
            logro TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def calcular_racha(correo):
    from datetime import date, timedelta
    conn = get_db()
    dias = conn.execute(
        'SELECT DISTINCT DATE(fecha) as dia FROM resultados WHERE correo = ? ORDER BY dia DESC',
        (correo,)
    ).fetchall()
    conn.close()
    if not dias:
        return {'racha': 0, 'puntos': 0, 'nivel': 1, 'nombre_nivel': '🌱 Principiante', 'logros': [], 'dias_totales': 0, 'estado': 'bloqueada', 'mensaje': 'Haz tu primer quiz para empezar tu racha 🔒', 'progreso_racha': 0}
    hoy = date.today()
    dias_set = set([d['dia'] for d in dias])
    racha = 0
    dia_actual = hoy
    if dia_actual.isoformat() not in dias_set:
        dia_actual = hoy - timedelta(days=1)
    while dia_actual.isoformat() in dias_set:
        racha += 1
        dia_actual -= timedelta(days=1)
    conn = get_db()
    total = conn.execute(
        'SELECT COALESCE(SUM(calificacion),0) as total FROM resultados WHERE correo = ?',
        (correo,)
    ).fetchone()
    bonus = 100 if racha >= 10 else (50 if racha >= 3 else 0)
    puntos = int(total['total'] / 10) + (racha * 20) + bonus
    conn.close()
    if puntos < 100:
        nivel, nombre = 1, '🌱 Principiante'
    elif puntos < 300:
        nivel, nombre = 2, '🔥 Aprendiz'
    elif puntos < 600:
        nivel, nombre = 3, '⭐ Experto'
    elif puntos < 1000:
        nivel, nombre = 4, '💎 Maestro'
    else:
        nivel, nombre = 5, '👑 Leyenda EducaPlus'
    logros = []
    if racha >= 3:
        logros.append('🔥 3 días seguidos')
    if racha >= 7:
        logros.append('🏆 Una semana de racha')
    if racha >= 10:
        logros.append('🌈 ¡10 DÍAS! Medalla Leyenda +100 XP')
    if puntos >= 100:
        logros.append('⭐ 100 puntos')
    if len(dias) >= 5:
        logros.append('📚 5 días aprendiendo')
    if racha < 3:
        estado = 'bloqueada'
        mensaje = f'¡Ya vas! Te faltan {3 - racha} día(s) para desbloquear tu racha 🔒'
        progreso = int(racha / 3 * 100)
    elif racha >= 3 and racha < 10:
        estado = 'desbloqueada'
        mensaje = f'¡Llevas {racha} días seguidos! Se mantiene dorada hasta el día 10 🔥'
        progreso = 100
    else:
        estado = 'leyenda'
        mensaje = f'🌈 ¡INCREÍBLE! {racha} días, eres LEYENDA EducaPlus 👑'
        progreso = 100
    return {'racha': racha, 'puntos': puntos, 'nivel': nivel, 'nombre_nivel': nombre, 'logros': logros, 'dias_totales': len(dias), 'estado': estado, 'mensaje': mensaje, 'progreso_racha': progreso}

@app.route('/')
def inicio():
    if 'correo' in session:
        return redirect(url_for('bienvenida'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip().lower()
        clave = request.form.get('clave', '')
        conn = get_db()
        user = conn.execute('SELECT * FROM usuarios WHERE correo = ?', (correo,)).fetchone()
        conn.close()
        if user and check_password_hash(user['clave'], clave):
            session['correo'] = correo
            session['nombre'] = user['nombre']
            return redirect(url_for('bienvenida'))
        flash('Correo o contraseña incorrectos', 'danger')
        return render_template('index.html', vista='login', correo=correo)
    return render_template('index.html', vista='login', correo='')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        correo = request.form.get('correo', '').strip().lower()
        edad = request.form.get('edad', '')
        especialidad = request.form.get('especialidad', '').strip()
        clave = request.form.get('clave', '')
        conn = get_db()
        existe = conn.execute('SELECT * FROM usuarios WHERE correo = ?', (correo,)).fetchone()
        if existe:
            conn.close()
            flash('Ese correo ya tiene cuenta, inicia sesión', 'danger')
            return render_template('index.html', vista='registro', nombre=nombre, correo=correo, edad=edad, especialidad=especialidad)
        conn.execute(
            'INSERT INTO usuarios (nombre, correo, edad, especialidad, clave) VALUES (?, ?, ?, ?, ?)',
            (nombre, correo, edad, especialidad, generate_password_hash(clave))
        )
        conn.commit()
        conn.close()
        session['correo'] = correo
        session['nombre'] = nombre
        flash('¡Cuenta creada! Bienvenido a EducaPlus', 'success')
        return redirect(url_for('bienvenida'))
    return render_template('index.html', vista='registro', nombre='', correo='', edad='', especialidad='')

@app.route('/bienvenida')
def bienvenida():
    if 'correo' not in session:
        return redirect(url_for('login'))
    d = calcular_racha(session['correo'])
    return render_template('index.html', vista='bienvenida', racha=d['racha'], puntos=d['puntos'], nivel=d['nivel'], nombre_nivel=d['nombre_nivel'], logros=d['logros'], dias_totales=d['dias_totales'], estado=d['estado'], mensaje=d['mensaje'], progreso_racha=d['progreso_racha'])

@app.route('/materias')
def materias():
    if 'correo' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', vista='materias', materias=MATERIAS)

@app.route('/materia/<clave>')
def materia(clave):
    if 'correo' not in session:
        return redirect(url_for('login'))
    if clave not in MATERIAS:
        return redirect(url_for('materias'))
    temas = MATERIAS[clave]['temas']
    return render_template('index.html', vista='materia', materias=MATERIAS, materia=MATERIAS[clave], clave=clave, temas=temas)

@app.route('/tema/<clave>/<int:numero>')
def tema(clave, numero):
    if 'correo' not in session:
        return redirect(url_for('login'))
    if clave not in MATERIAS or numero < 1 or numero > 10:
        return redirect(url_for('materias'))
    return render_template('index.html', vista='tema', materias=MATERIAS, materia=MATERIAS[clave], clave=clave, numero=numero)

@app.route('/juegos')
def juegos():
    if 'correo' not in session:
        return redirect(url_for('login'))
    parejas = {
        'matematicas': [['2+2', '4'], ['5x3', '15'], ['10/2', '5'], ['7+8', '15'], ['9-4', '5'], ['3x3', '9']],
        'espanol': [['Sinónimo de feliz', 'Alegre'], ['Antónimo de alto', 'Bajo'], ['Verbo', 'Cantar'], ['Sustantivo', 'Casa'], ['Adjetivo', 'Bonito'], ['Signo ¿?', 'Pregunta']]
    }
    palabras_ahorcado = {
        'matematicas': [
            {'palabra': 'ECUACION', 'pista': 'Se resuelve con X'},
            {'palabra': 'SUMA', 'pista': '2+2 es esto'},
            {'palabra': 'NUMERO', 'pista': '1,2,3...'}
        ],
        'espanol': [
            {'palabra': 'VERBO', 'pista': 'Acción en la oración'},
            {'palabra': 'LIBRO', 'pista': 'Se lee'},
            {'palabra': 'LETRA', 'pista': 'Forma el abecedario'}
        ]
    }
    preguntas_vf = [
        {'pregunta': '2 + 2 = 4', 'respuesta': True},
        {'pregunta': 'La Tierra es plana', 'respuesta': False},
        {'pregunta': 'Un verbo es una acción', 'respuesta': True},
        {'pregunta': '5 x 5 = 20', 'respuesta': False},
        {'pregunta': 'México está en América', 'respuesta': True}
    ]
    return render_template('index.html', vista='juegos', materias=MATERIAS, parejas=parejas, palabras_ahorcado=palabras_ahorcado, preguntas_vf=preguntas_vf)

@app.route('/guardar_resultado', methods=['POST'])
def guardar_resultado():
    if 'correo' not in session:
        return jsonify({'ok': False}), 401
    data = request.get_json() or {}
    conn = get_db()
    conn.execute(
        'INSERT INTO resultados (correo, nombre, materia, numero, calificacion) VALUES (?, ?, ?, ?, ?)',
        (session['correo'], session.get('nombre', 'Estudiante'), data.get('materia'), data.get('numero'), data.get('calificacion', 0))
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/progreso')
def progreso():
    if 'correo' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    mi_prom = {}
    grupo = {}
    tabla = {}
    for clave, m in MATERIAS.items():
        fila_mia = conn.execute('SELECT AVG(calificacion) as prom FROM resultados WHERE correo = ? AND materia = ?', (session['correo'], clave)).fetchone()
        mi_prom[clave] = fila_mia['prom'] if fila_mia and fila_mia['prom'] is not None else None
        fila_grupo = conn.execute('SELECT AVG(calificacion) as prom FROM resultados WHERE materia = ?', (clave,)).fetchone()
        grupo[clave] = fila_grupo['prom'] if fila_grupo and fila_grupo['prom'] is not None else None
        filas = []
        for i, titulo in enumerate(m['temas'], start=1):
            fila_tema = conn.execute('SELECT MAX(calificacion) as mejor FROM resultados WHERE correo = ? AND materia = ? AND numero = ?', (session['correo'], clave, i)).fetchone()
            mejor = fila_tema['mejor'] if fila_tema and fila_tema['mejor'] is not None else None
            filas.append({'numero': i, 'titulo': titulo, 'mejor': mejor})
        tabla[clave] = filas
    filas_ranking = conn.execute('SELECT nombre, COUNT(*) as temas, AVG(calificacion) as prom FROM resultados GROUP BY correo ORDER BY prom DESC').fetchall()
    ranking = [{'nombre': r['nombre'], 'temas': r['temas'], 'prom': r['prom']} for r in filas_ranking]
    conn.close()
    return render_template('index.html', vista='progreso', materias=MATERIAS, mi_prom=mi_prom, grupo=grupo, tabla=tabla, ranking=ranking)

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)