from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_mail import Mail, Message
from dotenv import load_dotenv
import os
import mysql.connector
from mysql.connector import Error
from datetime import date, datetime, time, timedelta
from urllib.parse import urlparse

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', '123')

# Obtener la URL de conexión desde la variable de entorno
db_url = make_url(os.getenv("MYSQL_URL"))
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
db_url = os.getenv("MYSQL_URL")

# Parsear la URL para separar los datos
parsed = urlparse(db_url)

db_config = {
    'host': parsed.hostname,
    'user': parsed.username,
    'password': parsed.password,
    'database': parsed.path[1:],
    'port': parsed.port
}

try:
    conexion = mysql.connector.connect(**db_config)
    cursor = conexion.cursor(dictionary=True)
    print("✅ Conexión a la base de datos establecida")
except Error as e:
    print(f"❌ Error al conectar a MySQL: {e}")
    conexion = None
    cursor = None

# Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)

# ✅ Conexión a MySQL
try:
    conexion = mysql.connector.connect(**db_config)
    cursor = conexion.cursor(dictionary=True)
    print("✅ Conexión a la base de datos establecida")
except Error as e:
    print(f"❌ Error al conectar a MySQL: {e}")
    conexion = None
    cursor = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registro')
def registro():
    return render_template('registro.html')

@app.route('/consulta')
def ver_registro():
    return render_template('consulta.html')

# Ajuste: aceptar filtro por fecha
@app.route('/api/consultas')
def api_consultas():
    try:
        if not conexion.is_connected():
            conexion.reconnect()
        fecha_query = request.args.get('fecha')
        cursor = conexion.cursor(dictionary=True)
        if fecha_query:
            cursor.execute("""
                SELECT fecha, hora, nombre, telefono, direccion, correo
                FROM consultas
                WHERE fecha = %s
                ORDER BY hora ASC
            """, (fecha_query,))
        else:
            cursor.execute("""
                SELECT fecha, hora, nombre, telefono, direccion, correo
                FROM consultas
                ORDER BY fecha DESC
            """)
        filas = cursor.fetchall()
        cursor.close()

        resultado = []
        for c in filas:
            fecha_str = c['fecha'].strftime('%Y-%m-%d') if isinstance(c['fecha'], date) else str(c['fecha'])
            resultado.append({
                'fecha': fecha_str,
                'hora': str(c['hora'])[:5],
                'nombre': c['nombre'],
                'telefono': c['telefono'],
                'direccion': c['direccion'],
                'correo': c['correo']
            })
        return jsonify(resultado)
    except Error as e:
        print("ERROR API:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/registrar_consulta', methods=['POST'])
def registrar_consulta():
    try:
        # Limpieza de registros antiguos (>7 días)
        if not conexion.is_connected():
            conexion.reconnect()
        cur_clean = conexion.cursor()
        siete_dias_atras = (date.today() - timedelta(days=7)).isoformat()
        cur_clean.execute("DELETE FROM consultas WHERE fecha < %s", (siete_dias_atras,))
        conexion.commit()
        cur_clean.close()

        # Datos del formulario
        fecha = request.form['fecha']
        hora = request.form['hora']
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        correo = request.form['correo']

        # Validar campos obligatorios
        if not all([fecha, hora, nombre, telefono, correo]):
            flash("Por favor complete todos los campos obligatorios", "danger")
            return redirect(url_for('registro'))

        # Validar horario permitido
        hora_obj = datetime.strptime(hora, '%H:%M').time()
        if hora_obj < time(12,0) or hora_obj > time(17,0):
            flash("Horario fuera de atención (12:00-17:00)", "warning")
            return redirect(url_for('registro'))

        # Revisar duplicados y cupo diario
        cursor2 = conexion.cursor()
        cursor2.execute("SELECT COUNT(*) FROM consultas WHERE fecha = %s AND hora = %s", (fecha, hora))
        if cursor2.fetchone()[0] > 0:
            cursor2.close()
            flash("Ese horario ya está ocupado", "danger")
            return redirect(url_for('registro'))

        cursor2.execute("SELECT COUNT(*) FROM consultas WHERE fecha = %s", (fecha,))
        if cursor2.fetchone()[0] >= 5:
            cursor2.close()
            flash("Cupo diario completo. Intenta otra fecha", "warning")
            return redirect(url_for('registro'))

        # Insertar
        cursor2.execute("""
            INSERT INTO consultas (fecha, hora, nombre, telefono, direccion, correo) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (fecha, hora, nombre, telefono, direccion, correo))
        conexion.commit()
        cursor2.close()

        # Enviar correo de confirmación
        if correo:
            try:
                msg = Message(
                    subject='Confirmación de consulta',
                    recipients=[correo],
                    body=f"Hola {nombre},\n\nTu consulta para el {fecha} a las {hora} ha sido registrada con éxito.\n\nGracias por confiar en nosotros."
                )
                mail.send(msg)
            except Exception as email_error:
                print(f"⚠️ Error al enviar correo: {email_error}")

        flash("Consulta registrada correctamente.", "success")
        return redirect(url_for('index'))

    except mysql.connector.Error as db_err:
        print("❌ Error BD:", db_err)
        flash("Hubo un error al guardar la consulta.", "danger")
        return redirect(url_for('registro'))
    except Exception as e:
        print("❌ Error general:", e)
        flash("Ocurrió un error inesperado.", "danger")
        return redirect(url_for('registro'))

@app.route('/send_email', methods=['POST'])
def send_email():
    try:
        nombre = request.form.get('nombre')
        correo = request.form.get('correo')
        mensaje = request.form.get('mensaje')
        if not all([nombre, correo, mensaje]):
            flash("Por favor complete todos los campos", "danger")
            return redirect(url_for('index'))

        msg = Message(
            subject=f'Mensaje de contacto de {nombre}',
            recipients=[app.config['MAIL_USERNAME']],
            body=f"Nombre: {nombre}\nCorreo: {correo}\nMensaje: {mensaje}"
        )
        mail.send(msg)
        flash("Mensaje enviado correctamente.", "success")
    except Exception as e:
        print(f"❌ Error al enviar email: {e}")
        flash("Ocurrió un error al enviar el mensaje. Intenta de nuevo más tarde.", "danger")
    return redirect(url_for('index'))

@app.teardown_appcontext
def close_db(exception=None):
    try:
        if 'cursor' in globals() and cursor:
            cursor.close()
        if 'conexion' in globals() and conexion and conexion.is_connected():
            conexion.close()
    except Exception as e:
        print(f"⚠️ Error al cerrar conexión: {e}")

#if __name__ == "__main__":
 #   app.run(debug=True, port=5000)