from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = "educaplus-secreto-2026"

# --- BASE DE DATOS EN MEMORIA ---
usuarios = {}
resultados = {}

# --- MATERIAS CON NOMBRES NUEVOS ---
materias = {
    'matematicas': {
        'nombre': 'Pensamiento Matemático',
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
            'Estadística y probabilidad',
        ]
    },
    'espanol': {
        'nombre': 'Lengua y Comunicación',
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
            'Ortografía y redacción',
        ]
    }
}

parejas = {
    'matematicas': [['2+2','4'],['5x3','15'],['10/2','5'],['7+8','15'],['9-4','5'],['3x3','9']],
    'espanol': [['Sinónimo de feliz','Alegre'],['Antónimo de alto','Bajo'],['Verbo','Cantar'],['Sustantivo','Casa'],['Adjetivo','Bonito'],['Signo ¿?','Pregunta']]
}

palabras_ahorcado = {
    'matematicas': [{'palabra':'ECUACION','pista':'Se resuelve con X'},{'palabra':'SUMA','pista':'2+2 es esto'},{'palabra':'RESTA','pista':'Quitar números'},{'palabra':'DIVISION','pista':'Repartir en partes'}],
    'espanol': [{'palabra':'VERBO','pista':'Acción en la oración'},{'palabra':'LIBRO','pista':'Se lee'},{'palabra':'PALABRA','pista':'Se forma con letras'},{'palabra':'ORACION','pista':'Tiene sujeto y predicado'}]
}

preguntas_vf = [
    {'pregunta':'2 + 2 = 4','respuesta': True},
    {'pregunta':'La Tierra es plana','respuesta': False},
    {'pregunta':'Un verbo es una acción','respuesta': True},
    {'pregunta':'La palabra "médico" lleva tilde','respuesta': True},
    {'pregunta':'10 - 4 = 5','respuesta': False},
]

def login_requerido():
    return 'correo' in session

def calcular_progreso(correo):
    mis = resultados.get(correo, [])
    mi_prom = {}
    grupo = {}
    tabla = {}
    for clave in ['matematicas','espanol']:
        mios = [r['calificacion'] for r in mis if r['materia'] == clave]
        mi_prom[clave] = sum(mios)/len(mios) if mios else None
        todos = []
        for c, lista in resultados.items():
            for r in lista:
                if r['materia'] == clave:
                    todos.append(r['calificacion'])
        grupo[clave] = sum(todos)/len(todos) if todos else None
        tabla[clave] = []
        for i, titulo in enumerate(materias[clave]['temas'], start=1):
            notas = [r['calificacion'] for r in mis if r['materia'] == clave and r['numero'] == i]
            tabla[clave].append({'numero': i, 'titulo': titulo, 'mejor': max(notas) if notas else None})
    ranking = []
    for c, lista in resultados.items():
        if lista and c in usuarios:
            prom = sum(r['calificacion'] for r in lista)/len(lista)
            ranking.append({'nombre': usuarios[c]['nombre'], 'temas': len(lista), 'prom': prom})
    ranking = sorted(ranking, key=lambda x: x['prom'], reverse=True)[:10]
    return mi_prom, grupo, tabla, ranking

def datos_racha(correo):
    mis = resultados.get(correo, [])
    racha = len(set((r['materia'], r['numero']) for r in mis))
    if racha == 0:
        racha = 1
    puntos = sum(r['calificacion'] for r in mis) if mis else 0
    if racha >= 10:
        estado = 'leyenda'
        mensaje = '¡ERES LEYENDA! 👑 Llegaste a 10 días, eres de las mejores.'
        nivel = 10
        nombre_nivel = 'LEYENDA'
        logros = ['🏆 Leyenda', '🔥 Racha 10', '⭐ Super Estudiante']
        progreso_racha = 100
    elif racha >= 3:
        estado = 'desbloqueada'
        mensaje = f'¡Vas súper bien! Ya llevas {racha} días, sigue así.'
        nivel = 3
        nombre_nivel = 'EXPERTO'
        logros = ['🔥 Racha 3', '⭐ En racha']
        progreso_racha = 100
    else:
        estado = 'bloqueada'
        mensaje = f'Veamos, llevas {racha} día(s). Haz 3 días seguidos para desbloquear tu racha dorada.'
        nivel = 1
        nombre_nivel = 'PRINCIPIANTE'
        logros = []
        progreso_racha = int(racha / 3 * 100)
    return estado, mensaje, racha, puntos, nivel, nombre_nivel, logros, progreso_racha

# --- RUTAS ---

@app.route('/')
def inicio():
    if login_requerido():
        return redirect(url_for('bienvenida'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo','').strip().lower()
        clave = request.form.get('clave','')
        u = usuarios.get(correo)
        if not u:
            flash('Ese correo no está registrado, crea una cuenta','error')
            return render_template('index.html', vista='login', correo=correo)
        if not check_password_hash(u['clave_hash'], clave):
            flash('Contraseña incorrecta','error')
            return render_template('index.html', vista='login', correo=correo)
        session['correo'] = correo
        session['nombre'] = u['nombre']
        return redirect(url_for('bienvenida'))
    return render_template('index.html', vista='login', correo='')

@app.route('/registro', methods=['GET','POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre','').strip()
        correo = request.form.get('correo','').strip().lower()
        edad = request.form.get('edad','')
        especialidad = request.form.get('especialidad','').strip()
        clave = request.form.get('clave','')
        clave2 = request.form.get('clave_confirmar','')

        if clave != clave2:
            flash('Las contraseñas no coinciden, escríbelas igual','error')
            return render_template('index.html', vista='registro', nombre=nombre, correo=correo, edad=edad, especialidad=especialidad)

        if len(clave) < 6:
            flash('La contraseña debe tener mínimo 6 caracteres','error')
            return render_template('index.html', vista='registro', nombre=nombre, correo=correo, edad=edad, especialidad=especialidad)

        if correo in usuarios:
            flash('Ese correo ya tiene cuenta, inicia sesión','error')
            return redirect(url_for('login'))

        usuarios[correo] = {
            'nombre': nombre,
            'correo': correo,
            'edad': edad,
            'especialidad': especialidad,
            'clave_hash': generate_password_hash(clave)
        }
        # AHORA YA NO ENTRA DIRECTO A LA PÁGINA PRINCIPAL
        # TE MANDA A INICIAR SESIÓN PRIMERO
        flash('¡Cuenta creada! Ahora inicia sesión con tu correo y contraseña','exito')
        return redirect(url_for('login'))

    return render_template('index.html', vista='registro', nombre='', correo='', edad='', especialidad='')

@app.route('/bienvenida')
def bienvenida():
    if not login_requerido():
        return redirect(url_for('login'))
    correo = session['correo']
    estado, mensaje, racha, puntos, nivel, nombre_nivel, logros, progreso_racha = datos_racha(correo)
    return render_template('index.html', vista='bienvenida', estado=estado, mensaje=mensaje, racha=racha, puntos=puntos, nivel=nivel, nombre_nivel=nombre_nivel, logros=logros, progreso_racha=progreso_racha)

@app.route('/materias', endpoint='materias')
def materias_view():
    if not login_requerido():
        return redirect(url_for('login'))
    return render_template('index.html', vista='materias', materias=materias)

@app.route('/materia/<clave>')
def materia(clave):
    if not login_requerido():
        return redirect(url_for('login'))
    if clave not in materias:
        return redirect(url_for('materias'))
    return render_template('index.html', vista='materia', materias=materias, materia=materias[clave], clave=clave, temas=materias[clave]['temas'])

@app.route('/tema/<clave>/<int:numero>')
def tema(clave, numero):
    if not login_requerido():
        return redirect(url_for('login'))
    if clave not in materias or numero < 1 or numero > 10:
        return redirect(url_for('materias'))
    return render_template('index.html', vista='tema', materias=materias, materia=materias[clave], clave=clave, numero=numero)

@app.route('/juegos')
def juegos():
    if not login_requerido():
        return redirect(url_for('login'))
    return render_template('index.html', vista='juegos', parejas=parejas, palabras_ahorcado=palabras_ahorcado, preguntas_vf=preguntas_vf)

@app.route('/progreso')
def progreso():
    if not login_requerido():
        return redirect(url_for('login'))
    correo = session['correo']
    mi_prom, grupo, tabla, ranking = calcular_progreso(correo)
    return render_template('index.html', vista='progreso', materias=materias, mi_prom=mi_prom, grupo=grupo, tabla=tabla, ranking=ranking)

@app.route('/guardar_resultado', methods=['POST'])
def guardar_resultado():
    if not login_requerido():
        return jsonify({'ok': False}), 401
    data = request.get_json() or {}
    correo = session['correo']
    if correo not in resultados:
        resultados[correo] = []
    for r in resultados[correo]:
        if r['materia'] == data.get('materia') and r['numero'] == data.get('numero'):
            if data.get('calificacion', 0) > r['calificacion']:
                r['calificacion'] = data.get('calificacion', 0)
            return jsonify({'ok': True})
    resultados[correo].append({
        'materia': data.get('materia'),
        'numero': data.get('numero'),
        'calificacion': data.get('calificacion', 0)
    })
    return jsonify({'ok': True})

@app.route('/logout', methods=['POST','GET'])
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
