import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox
# Importamos tus interfaces convertidas
from ui_Login import Ui_MainWindow as Ui_Login  
from ui_Dasboard import Ui_MainWindow as Ui_Dashboard
# Importamos la base de datos que creamos
from database import GestorBaseDatos  
from interfaces.Empleados import GestionEmpleados 
from interfaces.Usuario import GestionUsuarios
from interfaces.Clientes import GestionClientes
from interfaces.Productos import GestionProductos  # <--- Corregido: Importa GestionProductos
from interfaces.Pedidos import GestionPedidos

class VentanaLogin(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Login()
        self.ui.setupUi(self)
        
        self.db = GestorBaseDatos()
        
        self.ui.btnIngresar.clicked.connect(self.verificar_login)

    def verificar_login(self):
        # 1. Obtenemos el texto de los QLineEdit de tu login (ajusta si tus nombres son distintos)
        usuario_ingresado = self.ui.txtUsuario.text().strip()
        contrasena_ingresada = self.ui.txtContrasena.text().strip()

        if not usuario_ingresado or not contrasena_ingresada:
            QMessageBox.warning(self, "Campos vacíos", "Por favor ingrese usuario y contraseña.")
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                # 2. Realizamos el SELECT haciendo JOIN con empleados para traer los nombres y el rol
                cursor.execute("""
                    SELECT u.id, u.usuario, u.contrasena, u.rol, u.dni, e.nombres, e.apellidos 
                    FROM usuarios u 
                    LEFT JOIN empleados e ON u.dni = e.dni 
                    WHERE u.usuario = ? AND u.contrasena = ?
                """, (usuario_ingresado, contrasena_ingresada))
                
                resultado = cursor.fetchone()

            if resultado:
                rol_usuario = resultado[3]     # El rol para los permisos (Ej: 'Administrador')
                nombres_emp = resultado[5]     # Nombres del empleado
                apellidos_emp = resultado[6]   # Apellidos del empleado
                
                # Si es un usuario por defecto (como admin) que no tiene empleado asociado, usamos su nombre de usuario
                if not nombres_emp:
                    nombre_completo = resultado[1].capitalize()
                else:
                    nombre_completo = f"{nombres_emp} {apellidos_emp}"
                
                # 3. Abrimos el dashboard pasándole el rol y el nombre completo
                self.dashboard = VentanaDashboard(rol_usuario, nombre_completo)
                self.dashboard.show()
                self.close()
            else:
                QMessageBox.warning(self, "Error de Acceso", "Usuario o contraseña incorrectos.")
                
        except Exception as e:
            print(f"Error en el login: {e}")

class VentanaDashboard(QtWidgets.QMainWindow):
    def __init__(self, rol_usuario, nombre_usuario="Usuario"):
        super().__init__()
        self.ui = Ui_Dashboard()
        self.ui.setupUi(self)

        # 1. Declaramos el atributo para evitar el error de 'rol_actual'
        self.rol_actual = rol_usuario
        
        # 2. Mostramos el nombre real de la persona en lugar del rol
        self.ui.lblUsuario.setText(f"USUARIO: {nombre_usuario}")
        
        # Página de inicio por defecto
        self.ui.StackedWidget.setCurrentWidget(self.ui.pageInicio)

        self.ui.btnInicio.clicked.connect(lambda: self.ui.StackedWidget.setCurrentWidget(self.ui.pageInicio))
        self.ui.btnUsuario.clicked.connect(lambda: self.ui.StackedWidget.setCurrentWidget(self.ui.pageUsuario))
        self.ui.btnEmpleados.clicked.connect(lambda: self.ui.StackedWidget.setCurrentWidget(self.ui.pageEmpleados))
        self.ui.btnClientes.clicked.connect(lambda: self.ui.StackedWidget.setCurrentWidget(self.ui.pageClientes))
        self.ui.btnProductos.clicked.connect(lambda: self.ui.StackedWidget.setCurrentWidget(self.ui.pageProductos))
        self.ui.btnInsumos.clicked.connect(lambda: self.ui.StackedWidget.setCurrentWidget(self.ui.pageInsumos))
        self.ui.btnPedidos.clicked.connect(lambda: self.ui.StackedWidget.setCurrentWidget(self.ui.pagePedido))
        self.ui.btnReportes.clicked.connect(lambda: self.ui.StackedWidget.setCurrentWidget(self.ui.pageReportes))

        self.ui.btnCerrarsesion.clicked.connect(self.cerrar_sesion)

        # RESTRICCIONES SEGÚN EL ROL
        self.aplicar_permisos(rol_usuario)

        self.gestion_emp = GestionEmpleados(self.ui)
        self.gestion_usuarios = GestionUsuarios(self.ui)
        self.gestion_clientes = GestionClientes(self.ui)
        self.gestion_productos = GestionProductos(self.ui)
        self.gestor_pedidos = GestionPedidos(self.ui)

        if self.rol_actual == "Mozo":
            pass

    def aplicar_permisos(self, rol):
        if rol == "Mozo":
            self.ui.btnUsuario.setVisible(False)
            self.ui.btnEmpleados.setVisible(False)
            self.ui.btnReportes.setVisible(False)
            self.ui.btnProductos.setVisible(False)
            self.ui.btnInsumos.setVisible(False)
            self.ui.btnInicio.setVisible(False)
            self.ui.StackedWidget.setCurrentWidget(self.ui.pagePedido)
            
        elif rol == "Cajero":
            self.ui.btnUsuario.setVisible(False)
            self.ui.btnEmpleados.setVisible(False)
            self.ui.btnReportes.setVisible(False)
            self.ui.btnInsumos.setVisible(False)
            self.ui.btnInicio.setVisible(False)
            self.ui.StackedWidget.setCurrentWidget(self.ui.pageClientes)
            
        elif rol == "Administrador":
            self.ui.StackedWidget.setCurrentWidget(self.ui.pageInicio)

    def cerrar_sesion(self):
        from main import VentanaLogin 
        self.login = VentanaLogin()
        self.login.show()
        self.close()


    

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    # Iniciamos mostrando la ventana de Login
    login = VentanaLogin()
    login.show()
    
    sys.exit(app.exec())