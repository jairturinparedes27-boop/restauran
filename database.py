import sqlite3

class GestorBaseDatos:
    def __init__(self, nombre_db="restaurante.db"):
        self.nombre_db = nombre_db
        self.crear_tablas()
        self.insertar_datos_iniciales()
        self.insertar_clientes_iniciales()  
        self.insertar_categorias_iniciales()
        self.insertar_carta_inicial()
        self.insertar_empleados_iniciales()

    def conectar(self):
        conexion = sqlite3.connect(self.nombre_db)
        # 💡 Vital: Habilita el soporte de claves foráneas en SQLite
        conexion.execute("PRAGMA foreign_keys = ON;")
        return conexion

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

            # 5. Tabla Pedidos / Ventas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pedidos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mesa TEXT NOT NULL,
                    hora TEXT NOT NULL,
                    total REAL NOT NULL,
                    estado TEXT NOT NULL
                )
            """)

            # 6. Tabla Empleados
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

            # 7. Tabla Clientes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    documento TEXT UNIQUE NOT NULL,
                    nombre TEXT NOT NULL,
                    telefono TEXT,
                    direccion TEXT
                )
            """)

            conexion.commit()

    def obtener_estado_mesa(self, mesa):
        """Calcula el total real sumando el detalle de los productos pendientes de la mesa"""
        with self.conectar() as conexion:
            cursor = conexion.cursor()
            
            cursor.execute("""
                SELECT SUM(subtotal) 
                FROM detalle_pedidos 
                WHERE mesa = ? AND estado = 'PENDIENTE'
            """, (mesa,))
            resultado = cursor.fetchone()
            
            total = float(resultado[0]) if resultado and resultado[0] is not None else 0.0
            
            if total > 0:
                return "OCUPADA", total
                
            cursor.execute("""
                SELECT estado 
                FROM pedidos 
                WHERE mesa = ? AND estado != 'PAGADO'
            """, (mesa,))
            res_pedido = cursor.fetchone()
            
            if res_pedido:
                return "OCUPADA", 0.0
                
            return "LIBRE", 0.0

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

            for usuario in usuarios:
                cursor.execute("""
                    INSERT OR IGNORE INTO usuarios
                    (dni, usuario, contrasena, rol, estado)
                    VALUES (?, ?, ?, ?, ?)
                """, usuario)

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

            for empleado in empleados_data:
                cursor.execute("""
                    INSERT OR IGNORE INTO empleados
                    (dni, nombres, apellidos, telefono, cargo, fecha, estado)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, empleado)

            conexion.commit()