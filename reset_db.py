from app import app, db, Insumo, Producto, Receta, Venta

def resetear_base_de_datos():
    with app.app_context():
        print("🚨 Borrando datos existentes...")

        # Borrar en orden debido a relaciones entre tablas
        Venta.query.delete()
        Receta.query.delete()
        Producto.query.delete()
        Insumo.query.delete()

        db.session.commit()
        print("✅ Base de datos limpiada exitosamente.")

if __name__ == "__main__":
    resetear_base_de_datos()
