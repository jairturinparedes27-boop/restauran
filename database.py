import sqlite3

class GestorBaseDatos:
    def __init__(self, nombre_db="restaurante.db"):
        self.nombre_db = nombre_db
        self.crear_tablas()
        self.insertar_datos_iniciales()

    def conectar(self):
        return sqlite3.connect(self.nombre_db)

    def crear_tablas(self):
        conexion = self.conectar()
        cursor = conexion.cursor()

        # Tabla Usuarios 
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

        #  Tabla Empleados gestión de personal
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
        conexion.close()

    def insertar_datos_iniciales(self):
        """Inserta usuarios iniciales especificando claramente cada columna"""
        with self.conectar() as conexion:
            cursor = conexion.cursor()
            cursor.execute("SELECT * FROM usuarios WHERE usuario = 'admin'")
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO usuarios (dni, usuario, contrasena, rol, estado)
                    VALUES 
                    (NULL, 'admin', '1234', 'Administrador', 'Activo'),
                    (NULL, 'cajero', '1234', 'Cajero', 'Activo'),
                    (NULL, 'mozo', '1234', 'Mozo', 'Activo')
                """)
                conexion.commit()