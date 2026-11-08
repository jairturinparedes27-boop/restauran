import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager

# Roles que pueden iniciar sesión. Cualquier otro cargo (p. ej. "Personal de limpieza") no tiene acceso.
ROLES_CON_ACCESO = ("Administrador", "Cajero", "Mozo")

_ALGORITMO = "pbkdf2_sha256"
_ITERACIONES = 200_000


def hashear_contrasena(contrasena):
    """Devuelve 'pbkdf2_sha256$iteraciones$sal$hash' para guardar en la BD."""
    sal = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), bytes.fromhex(sal), _ITERACIONES)
    return f"{_ALGORITMO}${_ITERACIONES}${sal}${digest.hex()}"


def verificar_contrasena(contrasena, guardada):
    try:
        algoritmo, iteraciones, sal, esperado = (guardada or "").split("$")
        if algoritmo != _ALGORITMO:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), bytes.fromhex(sal), int(iteraciones))
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), esperado)


def es_hash(valor):
    return (valor or "").startswith(_ALGORITMO + "$")


class GestorBaseDatos:
    # Rutas de BD ya preparadas en este proceso: las tablas y los datos iniciales
    # se revisan una sola vez, aunque cada módulo cree su propio GestorBaseDatos.
    _inicializadas = set()

    def __init__(self, nombre_db="restaurante.db"):
        self.nombre_db = nombre_db
        clave = os.path.abspath(nombre_db)
        if clave in GestorBaseDatos._inicializadas:
            return
        self.crear_tablas()
        self.insertar_datos_iniciales()
        self.insertar_clientes_iniciales()
        self.insertar_categorias_iniciales()
        self.insertar_carta_inicial()
        self.insertar_empleados_iniciales()
        self.migrar_contrasenas()
        GestorBaseDatos._inicializadas.add(clave)

    @contextmanager
    def conectar(self):
        """Uso: `with self.db.conectar() as conexion:`. Hace commit si todo sale bien,
        rollback si hay un error, y siempre cierra la conexión (sqlite3 por sí solo no la cierra)."""
        conexion = sqlite3.connect(self.nombre_db)
        try:
            # Vital: habilita el soporte de claves foráneas en SQLite
            conexion.execute("PRAGMA foreign_keys = ON;")
            with conexion:
                yield conexion
        finally:
            conexion.close()

    def crear_tablas(self):
        with self.conectar() as conexion:
            cursor = conexion.cursor()

            # 1. Tabla Usuarios (Para el Login y roles)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dni TEXT,
                    usuario TEXT NOT NULL UNIQUE,
                    contrasena TEXT NOT NULL,
                    rol TEXT NOT NULL,
                    estado TEXT
                )
            """)

            # 2. Tabla Categorías
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre_categoria TEXT UNIQUE NOT NULL
                )
            """)

            # 3. Tabla Productos / Platos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE NOT NULL,
                    nombre TEXT NOT NULL,
                    id_categoria INTEGER,
                    precio_compra REAL NOT NULL,
                    precio_venta REAL NOT NULL,
                    stock INTEGER,
                    FOREIGN KEY (id_categoria) REFERENCES categorias(id) ON DELETE SET NULL
                )
            """)

            # 4. Tabla Insumos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS insumos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    stock_actual REAL NOT NULL,
                    unidad_medida TEXT NOT NULL,
                    stock_minimo REAL NOT NULL
                )
            """)

            # 5. Tabla Pedidos: mesas abiertas (la venta cobrada queda en 'ventas')
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pedidos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mesa TEXT NOT NULL,
                    hora TEXT NOT NULL,
                    total REAL NOT NULL,
                    estado TEXT NOT NULL
                )
            """)

            # 6. Detalle de los pedidos abiertos de cada mesa
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detalle_pedidos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mesa TEXT NOT NULL,
                    codigo TEXT NOT NULL,
                    producto TEXT NOT NULL,
                    cantidad INTEGER NOT NULL,
                    precio_unitario REAL NOT NULL,
                    subtotal REAL NOT NULL,
                    estado TEXT DEFAULT 'PENDIENTE'
                )
            """)

            # 7. Tabla Empleados
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS empleados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dni TEXT UNIQUE NOT NULL,
                    nombres TEXT NOT NULL,
                    apellidos TEXT NOT NULL,
                    telefono TEXT,
                    cargo TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    estado TEXT NOT NULL
                )
            """)

            # 8. Tabla Clientes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    documento TEXT UNIQUE NOT NULL,
                    nombre TEXT NOT NULL,
                    telefono TEXT,
                    direccion TEXT
                )
            """)

            # 9. Ventas cobradas (historial para reportes) y su detalle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT NOT NULL,
                    mesa TEXT NOT NULL,
                    tipo_comprobante TEXT NOT NULL,
                    serie TEXT NOT NULL,
                    numero INTEGER NOT NULL,
                    cliente_documento TEXT,
                    cliente_nombre TEXT,
                    metodo_pago TEXT NOT NULL,
                    total REAL NOT NULL,
                    monto_recibido REAL NOT NULL,
                    vuelto REAL NOT NULL,
                    usuario TEXT,
                    UNIQUE (serie, numero)
                )
            """)
            # Bases creadas antes de registrar quién cobra cada venta
            cursor.execute("PRAGMA table_info(ventas)")
            if "usuario" not in [columna[1] for columna in cursor.fetchall()]:
                cursor.execute("ALTER TABLE ventas ADD COLUMN usuario TEXT")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas (fecha)")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detalle_ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_venta INTEGER NOT NULL,
                    codigo TEXT,
                    producto TEXT NOT NULL,
                    cantidad INTEGER NOT NULL,
                    precio_unitario REAL NOT NULL,
                    subtotal REAL NOT NULL,
                    FOREIGN KEY (id_venta) REFERENCES ventas(id) ON DELETE CASCADE
                )
            """)

            conexion.commit()

    def tabla_vacia(self, cursor, tabla):
        """Los datos de ejemplo solo se cargan en una BD nueva, para que lo que el
        usuario borre o renombre no vuelva a aparecer al reiniciar la app."""
        cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
        return cursor.fetchone()[0] == 0

    def migrar_contrasenas(self):
        """Convierte a hash las contraseñas guardadas en texto plano por versiones anteriores."""
        with self.conectar() as conexion:
            cursor = conexion.cursor()
            cursor.execute("SELECT id, contrasena FROM usuarios")
            for id_usuario, contrasena in cursor.fetchall():
                if not es_hash(contrasena):
                    cursor.execute("UPDATE usuarios SET contrasena = ? WHERE id = ?",
                                   (hashear_contrasena(contrasena or ""), id_usuario))
            conexion.commit()

    def insertar_datos_iniciales(self):
        usuarios = [
            (None, 'admin', '1234', 'Administrador', 'Activo'),
            (None, 'cajero', '1234', 'Cajero', 'Activo'),
            (None, 'mozo', '1234', 'Mozo', 'Activo'),

            ('76594387', 'jmonteza', '1234', 'Administrador', 'Activo'),
            ('76303491', 'gyagami', '1234', 'Administrador', 'Activo'),
            ('73740822', 'lvasquez', '1234', 'Administrador', 'Activo'),
            ('70904405', 'jturin', '1234', 'Administrador', 'Activo'),
            ('73353129', 'jmunoz', '1234', 'Administrador', 'Activo')
        ]

        with self.conectar() as conexion:
            cursor = conexion.cursor()
            if not self.tabla_vacia(cursor, "usuarios"):
                return

            for dni, usuario, contrasena, rol, estado in usuarios:
                cursor.execute("""
                    INSERT OR IGNORE INTO usuarios
                    (dni, usuario, contrasena, rol, estado)
                    VALUES (?, ?, ?, ?, ?)
                """, (dni, usuario, hashear_contrasena(contrasena), rol, estado))

            conexion.commit()

    def insertar_clientes_iniciales(self):
        """Inserta los clientes (DNI) y empresas (RUC) predeterminados"""
        clientes_data = [
            ('76594387', 'José Luis Monteza Milian', '912345678', 'Av. Los Gorriones 123, Lima'),
            ('73353129', 'Jimi Alexander Muñoz Tamaya', '900222024', 'Av. Los crustaceos 123, Lima'),
            ('76303491', 'Gonzalo Yagami Mullisaca Mamani', '900222021', 'Av. Los sauces 123, Lima'),
            ('73740822', 'Leandro Cesar Vasquez larrauri', '994851042', 'Av. Los pinos 123, Lima'),
            ('70904405', 'Jair Hans Turin Paredes', '977673940', 'Santa Rosa 123, Lima'),
            ('70000001', 'Carlos Alberto Ramirez Soto', '900111001', 'Av. Los Olivos 123, Lima'),
            ('70000002', 'Maria Fernanda Torres Diaz', '900111002', 'Jr. Las Flores 245, Lima'),
            ('70000003', 'Jose Luis Mendoza Perez', '900111003', 'Av. Primavera 456, Surco'),
            ('70000004', 'Ana Sofia Castillo Ruiz', '900111004', 'Jr. Los Pinos 321, Chorrillos'),
            ('70000005', 'Miguel Angel Vargas Rojas', '900111005', 'Av. Grau 789, Barranco'),
            ('70000006', 'Lucia Isabel Flores Castro', '900111006', 'Jr. Union 654, Miraflores'),
            ('70000007', 'Pedro Antonio Herrera Leon', '900111007', 'Av. Brasil 147, Jesus Maria'),
            ('70000008', 'Valeria Nicole Ramos Silva', '900111008', 'Jr. Lima 258, San Miguel'),
            ('70000009', 'Diego Alejandro Chavez Morales', '900111009', 'Av. San Juan 369, San Juan de Miraflores'),
            ('70000010', 'Camila Andrea Medina Cruz', '900111010', 'Jr. Libertad 852, Villa Maria del Triunfo'),
            ('20000000001', 'Comercial Los Andes S.A.C.', '901222001', 'Av. Industrial 100, Lima'),
            ('20000000002', 'Distribuidora El Sol S.R.L.', '901222002', 'Av. Argentina 200, Callao'),
            ('20000000003', 'Inversiones San Pedro S.A.C.', '901222003', 'Jr. Comercio 300, Lima'),
            ('20000000004', 'Restaurantes del Pacifico S.A.C.', '901222004', 'Av. La Marina 400, San Miguel'),
            ('20000000005', 'Servicios Generales Lima E.I.R.L.', '901222005', 'Av. Arequipa 500, Lima'),
            ('20000000006', 'Corporacion Santa Rosa S.A.C.', '901222006', 'Av. Benavides 600, Miraflores'),
            ('20000000007', 'Importaciones del Norte S.R.L.', '901222007', 'Av. Mexico 700, La Victoria'),
            ('20000000008', 'Comercializadora San Martin S.A.C.', '901222008', 'Jr. Amazonas 800, Lima'),
            ('20000000009', 'Grupo Empresarial Los Reyes S.A.C.', '901222009', 'Av. Universitaria 900, San Miguel'),
            ('20000000010', 'Soluciones Integrales del Peru S.A.C.', '901222010', 'Av. Progreso 1000, Chorrillos')
        ]

        with self.conectar() as conexion:
            cursor = conexion.cursor()
            if not self.tabla_vacia(cursor, "clientes"):
                return
            for doc, nombre, telf, dir_cli in clientes_data:
                cursor.execute("""
                    INSERT OR IGNORE INTO clientes (documento, nombre, telefono, direccion)
                    VALUES (?, ?, ?, ?)
                """, (doc, nombre, telf, dir_cli))
            conexion.commit()

    def insertar_categorias_iniciales(self):
        """Inserta las categorías principales"""
        categorias = [
            "Anticuchos",
            "Brochetas de Pollo",
            "Chorizo",
            "Carnes",
            "Acompañamientos",
            "Bebidas"
        ]

        with self.conectar() as conexion:
            cursor = conexion.cursor()
            if not self.tabla_vacia(cursor, "categorias"):
                return
            for categoria in categorias:
                cursor.execute("""
                    INSERT OR IGNORE INTO categorias (nombre_categoria)
                    VALUES (?)
                """, (categoria,))
            conexion.commit()

    def insertar_carta_inicial(self):
        """Registra los productos iniciales de la carta vinculados a sus categorías"""
        productos = [
            ("P01", "Anticuchos", "Anticuchos (1 Palito)", 4.00, 9.00, 100),
            ("P02", "Anticuchos", "Anticuchos (2 Palitos)", 7.00, 15.00, 100),
            ("P03", "Anticuchos", "Anticuchos (3 Palitos)", 10.00, 21.00, 100),
            ("P04", "Anticuchos", "Anticuchos (5 Palitos)", 15.00, 30.00, 100),
            ("P05", "Brochetas de Pollo", "Brocheta de Pollo (1 Palito)", 4.50, 10.00, 100),
            ("P06", "Brochetas de Pollo", "Brocheta de Pollo (2 Palitos)", 8.00, 17.00, 100),
            ("P07", "Brochetas de Pollo", "Brocheta de Pollo (3 Palitos)", 11.50, 24.00, 100),
            ("P08", "Brochetas de Pollo", "Brocheta de Pollo (5 Palitos)", 17.00, 36.00, 100),
            ("P09", "Chorizo", "Chorizo (1 Unidad)", 3.00, 6.00, 100),
            ("P10", "Chorizo", "Chorizo (2 Unidades)", 5.00, 10.00, 100),
            ("P11", "Carnes", "Churrasco (200g aprox.)", 10.00, 18.00, 100),
            ("P12", "Carnes", "Chancho al Horno (200g aprox.)", 16.00, 28.00, 100),
            ("P13", "Acompañamientos", "Choclo con Queso", 2.50, 5.00, 100),
            ("P14", "Bebidas", "Inca Kola", 2.00, 4.00, 100),
            ("P15", "Bebidas", "Coca-Cola", 2.00, 4.00, 100),
            ("P16", "Bebidas", "Agua", 1.20, 3.00, 100),
        ]

        with self.conectar() as conexion:
            cursor = conexion.cursor()
            if not self.tabla_vacia(cursor, "productos"):
                return
            for codigo, categoria, nombre, compra, venta, stock in productos:
                cursor.execute("SELECT id FROM categorias WHERE nombre_categoria = ?", (categoria,))
                resultado = cursor.fetchone()

                if resultado:
                    id_categoria = resultado[0]
                    cursor.execute("""
                        INSERT OR IGNORE INTO productos
                        (codigo, nombre, id_categoria, precio_compra, precio_venta, stock)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (codigo, nombre, id_categoria, compra, venta, stock))
            conexion.commit()

    def insertar_empleados_iniciales(self):

        empleados_data = [
            ('76594387', 'José Luis', 'Monteza Milian', '912345678', 'Cajero', '2026-11-07', 'Activo'),
            ('76303491', 'Gonzalo Yagami', 'Mullisaca Mamani', '900222021', 'Cajero', '2026-11-07', 'Activo'),
            ('73740822', 'Leandro Cesar', 'Vasquez Larrauri', '994851042', 'Cajero', '2026-11-07', 'Activo'),
            ('70904405', 'Jair Hans', 'Turin Paredes', '977673940', 'Administrador', '2026-11-07', 'Activo'),
            ('73353129', 'Jimi Alexander', 'Muñoz Tamaya','900222024', 'Administrador', '2026-11-07', 'Activo')
        ]

        with self.conectar() as conexion:
            cursor = conexion.cursor()
            if not self.tabla_vacia(cursor, "empleados"):
                return

            for empleado in empleados_data:
                cursor.execute("""
                    INSERT OR IGNORE INTO empleados
                    (dni, nombres, apellidos, telefono, cargo, fecha, estado)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, empleado)

            conexion.commit()
