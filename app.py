from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2 import sql, errors as pg_errors
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

# Configuración de la base de datos
DB_CONFIG = {
    'host': os.environ["DB_HOST"],
    'port': os.environ["DB_PORT"],
    'database': os.environ["DB_NAME"],
    'user': os.environ["DB_USER"],
    'password': os.environ["DB_PASSWORD"]
}

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            return "Por favor, ingrese su nombre de usuario y contraseña", 400
        
        if len(username) < 5 or len(password) < 8:
            return "El nombre de usuario debe tener al menos 5 caracteres y la contraseña al menos 8 caracteres", 400

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            # Buscar el usuario
            cur.execute("SELECT * FROM obtener_usuario_por_username(%s);", (username,))
            user = cur.fetchone()

        except Exception as e:
            print(f"Error al buscar el usuario: {e}")
            return "Error interno", 500

        finally:
            cur.close()
            conn.close()

        if user and check_password_hash(user[2], password):
            session['usuario_id'] = user[0]
            session['usuario'] = str(user[1]).upper()
            return redirect(url_for('listar_facturas'))
        else:
            flash('Nombre de usuario o contraseña incorrectos', 'error')
            # Si las credenciales son incorrectas, redirigir a la página de inicio de sesión
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['nombre']
        if not username:
            print("Nombre de usuario no proporcionado")
            flash("Por favor, ingrese su nombre de usuario", "error")
            return redirect(url_for('register'))
        email = request.form['email']
        if not email:
            print("Email no proporcionado")
            flash("Por favor, ingrese su email", "error")
            return redirect(url_for('register'))
        password = request.form['password']
        if not password:
            print("Contraseña no proporcionada")
            flash("Por favor, ingrese su contraseña", "error")
            return redirect(url_for('register'))
        key_secret = request.form['key_secret']
        if not key_secret:
            print("Clave secreta no proporcionada")
            flash("Por favor, ingrese la clave secreta", "error")
            return redirect(url_for('register'))

        key = os.environ["KEY_SECRET_ADMIN"]

        if key_secret != key:
            flash("Clave secreta incorrecta", "error")
            return redirect(url_for('register'))

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('CALL insertar_usuario(%s, %s, %s);',
                    (username, email, generate_password_hash(password)))
            conn.commit()
            flash('Usuario registrado exitosamente', 'success')
        except pg_errors.UniqueViolation:
            conn.rollback()
            flash('El usuario ya existe con ese nombre de usuario', 'error')
            return redirect(url_for('register'))
        except Exception as e:
            conn.rollback()
            flash('Error al registrar el usuario', 'error')
            return redirect(url_for('register'))
        finally:
            cur.close()
            conn.close()

        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()  # Borra todos los datos de sesión
    return redirect(url_for('login'))

@app.route('/facturas')
def listar_facturas():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM obtener_facturas();')
    facturas = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('factura.html', facturas=facturas)

@app.route('/factura/nueva', methods=['GET', 'POST'])
def nueva_factura():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder.', 'error')
        return redirect(url_for('login'))
    if request.method == 'POST':
        # Obtener datos del formulario
        cliente_id = request.form['cliente_id']
        items = []
        total = 0

        # CAMBIO 8 
        # 🛡️ Validación: verificar si el cliente existe
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM clientes WHERE id = %s;", (cliente_id,))
            cliente_existe = cur.fetchone()[0] > 0
            cur.close()
            conn.close()

            if not cliente_existe:
                flash("El cliente no existe.", "error")
                return redirect(url_for('nueva_factura'))
        except Exception as e:
            print(f"Error al verificar cliente: {e}")
            flash("Error al verificar el cliente.", "error")
            return redirect(url_for('nueva_factura'))

        # Procesar items
        for i in range(1, 6):  # Máximo 5 items por factura
            producto_id = request.form.get(f'producto_id_{i}')
            cantidad = request.form.get(f'cantidad_{i}')
            try:
                if producto_id and cantidad:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    # CAMBIO 8
                    cur.execute('SELECT * FROM obtener_precio_producto(%s);', (producto_id,))
                    # precio = cur.fetchone()[0]
                    precio_result = cur.fetchone()
                    if not precio_result or precio_result[0] is None:
                        flash(f"El producto con ID {producto_id} no existe o no tiene precio.", "error")
                        cur.close()
                        conn.close()
                        return redirect(url_for('nueva_factura'))
                    precio = precio_result[0]

                    subtotal = float(precio) * float(cantidad)
                    items.append({
                        'producto_id': producto_id,
                        'cantidad': cantidad,
                        'precio': precio,
                        'subtotal': subtotal
                    })
                    total += subtotal
            except Exception as e:
                print(f"Error al procesar el item: {e}")
                flash('Error al procesar el item.', 'error')
                return redirect(url_for('nueva_factura'))
            finally:
                cur.close()
                conn.close()
        
        # --- VALIDACIÓN CRÍTICA ---
        if not items:
            flash('Error: Una factura debe tener al menos un producto.', 'error')
            return redirect(url_for('nueva_factura'))  # Redirige de vuelta al formulario

        try:
            # Insertar factura con número generado
            conn = get_db_connection()
            cur = conn.cursor()

            # Obtener el próximo número de factura de la secuencia
            cur.execute("SELECT * FROM obtener_siguiente_numero_factura()")
            numero_factura = f"FACT-{cur.fetchone()[0]}"

            cur.execute(
                'SELECT insertar_factura(%s, %s, %s);', (numero_factura, cliente_id, total)
                )
            factura_id = cur.fetchone()[0]
            conn.commit()

            # Insertar items de factura
            for item in items:
                cur.execute(
                    'CALL insertar_factura_item(%s, %s, %s, %s, %s);',
                    (factura_id, item['producto_id'], item['cantidad'], item['precio'], item['subtotal'])
                )

            conn.commit()
        except Exception as e:
            print(f"Error al insertar la factura: {e}")
            conn.rollback()
            flash('Error al insertar la factura.', 'error')
            return redirect(url_for('nueva_factura'))
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('ver_factura', id=factura_id))
    else:
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # Obtener clientes
            cur.execute('SELECT * FROM obtener_clientes();')
            clientes = cur.fetchall()

            # Obtener productos
            cur.execute('SELECT * FROM obtener_productos();')
            productos = cur.fetchall()

        except Exception as e:
            print(f"Error al obtener clientes o productos: {e}")
            flash('Error al cargar los datos.', 'error')
            return redirect(url_for('listar_facturas'))
        finally:
            cur.close()
            conn.close()
        return render_template('nueva_factura.html', clientes=clientes, productos=productos)

@app.route('/factura/<int:id>', methods=['GET'])
def ver_factura(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Obtener factura
    cur.execute('''SELECT * FROM obtener_factura_por_id(%s);''', (id,))
    factura = cur.fetchone()
    #Cambio 9
    # Validación: si no existe la factura, redirigir con mensaje
    if not factura:
        cur.close()
        conn.close()
        flash("La factura no existe o ha sido eliminada.", "error")
        return redirect(url_for('listar_facturas'))

    # Obtener items
    cur.execute('''SELECT * FROM obtener_items_factura(%s);''', (id,))
    items = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('ver_factura.html', factura=factura, items=items)

@app.route('/factura/borrar/<int:id>')
def borrar_factura(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Borrar items de la factura
        cur.execute('CALL borrar_items_factura(%s);', (id,))
        conn.commit()
        # Borrar la factura
        cur.execute('CALL borrar_factura(%s);', (id,))
        conn.commit()
        flash("Factura eliminada exitosamente.", "success")
    except Exception as e:
            print(f"Error al eliminar la factura: {e}")
            conn.rollback()
            flash("Error al eliminar la factura.", "error")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('listar_facturas'))

@app.route('/factura/registrar_cliente', methods=['POST', 'GET'])
def registrar_cliente():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        ruc = request.form.get('ruc')
        if not ruc:
            print("RUC no proporcionado")
            flash("El RUC es obligatorio.", "error")
            return redirect(url_for('nueva_factura'))
        nombre = request.form.get('nombre').upper()
        if not nombre:
            print("Nombre no proporcionado")
            flash("El nombre es obligatorio.", "error")
            return redirect(url_for('nueva_factura'))
        email = request.form.get('email').lower()
        if not email:
            print("Email no proporcionado")
            flash("El email es obligatorio.", "error")
            return redirect(url_for('nueva_factura'))
        telefono = request.form.get('telefono')
        if len(telefono) < 9:
            print("Teléfono inválido")
            flash("El teléfono debe tener al menos 9 dígitos.", "error")
            return redirect(url_for('nueva_factura'))
        direccion = request.form.get('direccion').upper()
        if not direccion:
            print("Dirección no proporcionada")
            flash("La dirección es obligatoria.", "error")
            return redirect(url_for('nueva_factura'))

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute('CALL insertar_cliente(%s, %s, %s, %s, %s);', (ruc, nombre, direccion, telefono, email))
            conn.commit()
            flash("Cliente registrado exitosamente.", "success")
        except pg_errors.UniqueViolation:
            conn.rollback()
            flash("El cliente ya existe con ese RUC.", "error")
        except Exception as e:
            print(f"Error al registrar el cliente: {e}")
            conn.rollback()
            flash("Error al registrar el cliente.", "error")
        finally:
            cur.close()
            conn.close()
    
    return render_template('registrar_cliente.html')

if __name__ == '__main__':
    app.run(debug=True)