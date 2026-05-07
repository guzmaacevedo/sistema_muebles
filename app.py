from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from datetime import datetime

import pytz


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///muebles.db'
app.config['SECRET_KEY'] = 'clave_secreta'
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# MODELOS
class Insumo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    unidad = db.Column(db.String(20))
    stock = db.Column(db.Float)
    stock_minimo = db.Column(db.Float)


class Receta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'))
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumo.id'))
    cantidad = db.Column(db.Float)

    producto= db.relationship('Producto', backref='recetas')
    insumo = db.relationship('Insumo', backref='recetas')

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'))
    cantidad = db.Column(db.Integer)
    fecha_hora = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.timezone('America/Bogota')))

    producto = db.relationship('Producto', backref='ventas')

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, default=0)
    
class PlanTrabajo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)

    producto = db.relationship('Producto', backref='planes_trabajo')



# RUTAS PRINCIPALES
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/insumos')
def ver_insumos():
    insumos = Insumo.query.all()
    return render_template('listar_insumos.html', insumos=insumos)

@app.route('/insumos')
def listar_insumos():
    insumos = Insumo.query.all()
    return render_template('listar_insumos.html', insumos=insumos)

@app.route('/productos')
def ver_productos():
    productos = Producto.query.all()
    return render_template('productos.html', productos=productos)

@app.route('/agregar_insumo', methods=['GET', 'POST'])
def agregar_insumo():
    if request.method == 'POST':
        nombre = request.form['nombre']
        unidad = request.form['unidad']
        stock = int(request.form['stock'])
        stock_minimo = int(request.form['stock_minimo'])

        nuevo_insumo = Insumo(
            nombre=nombre,
            unidad=unidad,
            stock=stock,
            stock_minimo=stock_minimo
        )
        db.session.add(nuevo_insumo)
        db.session.commit()

        return redirect('/insumos')

    return render_template('agregar_insumo.html')

@app.route('/agregar_producto', methods=['GET', 'POST'])
def agregar_producto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        nuevo_producto = Producto(nombre=nombre, stock=0)
        db.session.add(nuevo_producto)
        db.session.commit()
        flash(f'Producto "{nombre}" agregado. Ahora asigna sus insumos.', 'success')
        return redirect('/productos')
    
    return render_template('agregar_producto.html')

@app.route('/fabricar_producto', methods=['GET', 'POST'])
def fabricar_producto():
    productos = Producto.query.all()

    if request.method == 'POST':
        producto_id = int(request.form['producto_id'])
        cantidad_fabricar = int(request.form['cantidad'])

        producto = Producto.query.get(producto_id)
        recetas = Receta.query.filter_by(producto_id=producto_id).all()

        # Verificar si hay suficiente stock de cada insumo
        for receta in recetas:
            total_necesario = receta.cantidad * cantidad_fabricar
            if receta.insumo.stock < total_necesario:
                flash(f"❌ No hay suficiente '{receta.insumo.nombre}'. Se necesita {total_necesario}, pero hay {receta.insumo.stock}.", 'danger')
                return redirect('/fabricar_producto')

        # Descontar insumos y aumentar stock del producto
        for receta in recetas:
            total_necesario = receta.cantidad * cantidad_fabricar
            receta.insumo.stock -= total_necesario
            db.session.add(receta.insumo)

            # Verificar si quedó por debajo del stock mínimo
            if receta.insumo.stock < receta.insumo.stock_minimo:
                flash(f"⚠️ Alerta: El insumo '{receta.insumo.nombre}' bajó del mínimo ({receta.insumo.stock} < {receta.insumo.stock_minimo}).", 'warning')

        producto.stock += cantidad_fabricar
        db.session.add(producto)
        db.session.commit()

        flash(f"✅ {cantidad_fabricar} unidad(es) de '{producto.nombre}' fabricadas exitosamente.", 'success')
        return redirect('/productos')

    return render_template('fabricar_producto.html', productos=productos)

@app.route('/registrar_venta', methods=['GET', 'POST'])
def registrar_venta():
    productos = Producto.query.all()

    if request.method == 'POST':
        producto_id = int(request.form['producto_id'])
        cantidad = int(request.form['cantidad'])

        producto = Producto.query.get(producto_id)

        # Verificar si hay suficiente stock del producto terminado
        if producto.stock < cantidad:
            flash(f"No hay suficiente stock de {producto.nombre}. Disponible: {producto.stock}", 'danger')
            return redirect('/registrar_venta')

        # Registrar la venta y reducir el stock del producto
        venta = Venta(producto_id=producto_id, cantidad=cantidad)
        producto.stock -= cantidad
        db.session.add(venta)
        db.session.commit()

        flash(f"Venta registrada: {cantidad} unidad(es) de {producto.nombre}.", 'success')
        return redirect('/productos')

    return render_template('registrar_venta.html', productos=productos)

@app.route('/historial_ventas')
def historial_ventas():
    ventas = Venta.query.order_by(Venta.fecha_hora.desc()).all()
    return render_template('historial_ventas.html', ventas=ventas)


@app.route('/producto/<int:producto_id>/receta', methods=['GET', 'POST'])
def definir_receta(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    insumos = Insumo.query.all()

    if request.method == 'POST':
        insumo_id = int(request.form['insumo_id'])
        cantidad = float(request.form['cantidad'])

        nueva_receta = Receta(
            producto_id=producto.id,
            insumo_id=insumo_id,
            cantidad=cantidad
        )
        db.session.add(nueva_receta)
        db.session.commit()
        flash('Insumo agregado a la receta', 'success')

    receta_actual = Receta.query.filter_by(producto_id=producto.id).all()
    return render_template('definir_receta.html', producto=producto, insumos=insumos, receta=receta_actual)

@app.route('/asignar_insumos/<int:producto_id>', methods=['GET', 'POST'])
def asignar_insumos(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    insumos = Insumo.query.all()

    if request.method == 'POST':
        for insumo in insumos:
            cantidad = request.form.get(f'insumo_{insumo.id}')
            if cantidad and float(cantidad) > 0:
                relacion = Receta(
                    producto_id=producto.id,
                    insumo_id=insumo.id,
                    cantidad=float(cantidad)
                )
                db.session.add(relacion)

        db.session.commit()
        flash('Receta asignada correctamente.', 'success')
        return redirect('/productos')

    return render_template('asignar_insumos.html', producto=producto, insumos=insumos)

@app.route('/editar_insumo/<int:insumo_id>', methods=['GET', 'POST'])
def editar_insumo(insumo_id):
    insumo = Insumo.query.get_or_404(insumo_id)

    if request.method == 'POST':
        try:
            cantidad_nueva = float(request.form['cantidad'])
            insumo.stock += cantidad_nueva
            db.session.commit()
            flash(f'Se han agregado {cantidad_nueva} unidades a {insumo.nombre}. Nuevo stock: {insumo.stock}', 'success')
            return redirect('/insumos')
        except ValueError:
            flash('Cantidad inválida.', 'danger')

    return render_template('editar_insumo.html', insumo=insumo)


@app.route('/eliminar_insumo/<int:insumo_id>', methods=['POST'])
def eliminar_insumo(insumo_id):
    insumo = Insumo.query.get_or_404(insumo_id)

    # Validar que no esté asociado a recetas
    if insumo.recetas:
        flash(f"No puedes eliminar el insumo '{insumo.nombre}' porque está en uso en una receta.", 'danger')
        return redirect('/insumos')

    db.session.delete(insumo)
    db.session.commit()
    flash(f"Insumo '{insumo.nombre}' eliminado correctamente.", 'success')
    return redirect('/insumos')

@app.route('/editar_receta/<int:producto_id>', methods=['GET', 'POST'])
def editar_receta(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    insumos = Insumo.query.all()
    receta_actual = {r.insumo_id: r for r in producto.recetas}

    if request.method == 'GET':
        # Captura la URL anterior (de donde vino el usuario)
        volver_a = request.referrer or url_for('index')
        return render_template('editar_receta.html', producto=producto, insumos=insumos, receta=receta_actual, volver_a=volver_a)

    if request.method == 'POST':
        # Actualizar cantidades existentes
        for insumo_id_str, receta in receta_actual.items():
            key = f'cantidad_{insumo_id_str}'
            if key in request.form:
                try:
                    nueva_cantidad = float(request.form[key])
                    receta.cantidad = nueva_cantidad
                except ValueError:
                    flash('Cantidad inválida para insumo existente.', 'danger')

        # Eliminar insumos de receta
        eliminar_ids = request.form.getlist('eliminar_insumo')
        for insumo_id in eliminar_ids:
            receta = receta_actual.get(int(insumo_id))
            if receta:
                db.session.delete(receta)

        # Agregar nuevos insumos
        nuevo_insumo_id = request.form.get('nuevo_insumo')
        nueva_cantidad = request.form.get('nueva_cantidad')
        if nuevo_insumo_id and nueva_cantidad:
            try:
                nuevo_id = int(nuevo_insumo_id)
                cantidad = float(nueva_cantidad)
                if nuevo_id not in receta_actual:
                    nueva_receta = Receta(producto_id=producto.id, insumo_id=nuevo_id, cantidad=cantidad)
                    db.session.add(nueva_receta)
            except ValueError:
                flash('Datos inválidos al agregar nuevo insumo.', 'danger')

        db.session.commit()
        flash('Receta actualizada correctamente', 'success')
        volver_a = session.pop('volver_a', url_for('index'))
        return redirect(volver_a)
    
    

@app.route('/eliminar_producto/<int:producto_id>', methods=['POST'])
def eliminar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    Receta.query.filter_by(producto_id=producto.id).delete()
    db.session.delete(producto)
    db.session.commit()
    flash('Producto eliminado correctamente', 'success')
    return redirect(url_for('index'))


@app.route('/plan_trabajo', methods=['GET', 'POST'])
def plan_trabajo():
    productos = Producto.query.all()
    resultado = None

    if request.method == 'POST':
        plan = []
        for producto in productos:
            cantidad_str = request.form.get(f'cantidad_{producto.id}')
            if cantidad_str:
                try:
                    cantidad = int(cantidad_str)
                    if cantidad > 0:
                        plan.append((producto, cantidad))
                except ValueError:
                    flash(f'Cantidad inválida para {producto.nombre}', 'danger')

        if plan:
            resultado = verificar_plan(plan)
            faltantes = []
            for nombre, (disponible, necesaria) in resultado['faltantes'].items():
                faltantes.append({
                    'nombre': nombre,
                    'disponible': disponible,
                    'necesaria': necesaria
                })

            fecha = datetime.today().strftime('%d-%m-%Y')

            return render_template('verificar_plan.html', faltantes=faltantes, fecha=fecha)

    return render_template('plan_trabajo.html', productos=productos, resultado=resultado)


def verificar_plan(plan):
    """
    plan = lista de tuplas (producto, cantidad_deseada)
    Devuelve diccionario con insumos necesarios y si hay stock suficiente
    """
    # Calcular insumos totales requeridos para el plan
    insumos_requeridos = {}

    for producto, cant_producto in plan:
        for receta in producto.recetas:
            total_cantidad = receta.cantidad * cant_producto
            insumos_requeridos[receta.insumo_id] = insumos_requeridos.get(receta.insumo_id, 0) + total_cantidad

    # Verificar stock disponible
    faltantes = {}
    for insumo_id, cantidad_necesaria in insumos_requeridos.items():
        insumo = Insumo.query.get(insumo_id)
        if insumo.stock < cantidad_necesaria:
            faltantes[insumo.nombre] = (insumo.stock, cantidad_necesaria)

    puede_cumplir = len(faltantes) == 0

    return {
        'insumos_requeridos': insumos_requeridos,
        'faltantes': faltantes,
        'puede_cumplir': puede_cumplir
    }



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
