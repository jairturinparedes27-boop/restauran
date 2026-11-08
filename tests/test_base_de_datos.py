import database


def reiniciar_app():
    """Simula volver a abrir la aplicación sobre la misma base de datos."""
    database.GestorBaseDatos._inicializadas.clear()
    database.GestorBaseDatos()


def test_bd_nueva_se_llena_con_datos_de_ejemplo(bd):
    database.GestorBaseDatos()
    assert bd.q("SELECT COUNT(*) FROM usuarios") == [(8,)]
    assert bd.q("SELECT COUNT(*) FROM productos") == [(16,)]


def test_lo_borrado_o_renombrado_no_reaparece(bd):
    database.GestorBaseDatos()
    bd.x("DELETE FROM usuarios WHERE usuario = 'mozo'")
    bd.x("DELETE FROM productos WHERE codigo = 'P16'")
    bd.x("UPDATE categorias SET nombre_categoria = 'Bebidas frias' WHERE nombre_categoria = 'Bebidas'")

    reiniciar_app()

    assert not bd.q("SELECT 1 FROM usuarios WHERE usuario = 'mozo'")
    assert not bd.q("SELECT 1 FROM productos WHERE codigo = 'P16'")
    assert not bd.q("SELECT 1 FROM categorias WHERE nombre_categoria = 'Bebidas'")


def test_tabla_ventas_antigua_recibe_la_columna_usuario(bd):
    bd.x("""CREATE TABLE ventas (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL, mesa TEXT NOT NULL,
            tipo_comprobante TEXT NOT NULL, serie TEXT NOT NULL, numero INTEGER NOT NULL, cliente_documento TEXT,
            cliente_nombre TEXT, metodo_pago TEXT NOT NULL, total REAL NOT NULL, monto_recibido REAL NOT NULL,
            vuelto REAL NOT NULL, UNIQUE (serie, numero))""")
    database.GestorBaseDatos()
    assert "usuario" in [c[1] for c in bd.q("PRAGMA table_info(ventas)")]
