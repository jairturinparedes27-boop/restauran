import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox
# Importamos tus interfaces convertidas
from ui_Login import Ui_MainWindow as Ui_Login
from ui_Dasboard import Ui_MainWindow as Ui_Dashboard
# Importamos la base de datos que creamos
from database import GestorBaseDatos, ROLES_CON_ACCESO, verificar_contrasena
from Dasboard.Empleados import GestionEmpleados
from Dasboard.Usuario import GestionUsuarios
from Dasboard.Clientes import GestionClientes
from Dasboard.Productos import GestionProductos
from Dasboard.Pedidos import GestionPedidos

# Botones del menú lateral
MODULOS = ["btnInicio", "btnUsuario", "btnEmpleados", "btnClientes",
           "btnProductos", "btnInsumos", "btnPedidos", "btnReportes"]

# Qué módulos ve cada rol y en qué página empieza. Un rol que no esté aquí no ve ningún módulo.
PERMISOS = {
    "Administrador": (MODULOS, "pageInicio"),
    "Cajero": (["btnClientes", "btnProductos", "btnPedidos"], "pageClientes"),
    "Mozo": (["btnClientes", "btnPedidos"], "pagePedido"),
}


class VentanaLogin(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Login()
        self.ui.setupUi(self)

        self.db = GestorBaseDatos()

        self.ui.btnIngresar.clicked.connect(self.verificar_login)

    def verificar_login(self):
        usuario_ingresado = self.ui.txtUsuario.text().strip()
        contrasena_ingresada = self.ui.txtContrasena.text().strip()

        if not usuario_ingresado or not contrasena_ingresada:
            QMessageBox.warning(self, "Campos vacíos", "Por favor ingrese usuario y contraseña.")
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                # JOIN con empleados para traer los nombres de la persona
                cursor.execute("""
                    SELECT u.usuario, u.contrasena, u.rol, u.estado, e.nombres, e.apellidos
                    FROM usuarios u
                    LEFT JOIN empleados e ON u.dni = e.dni
                    WHERE u.usuario = ?
                """, (usuario_ingresado,))
                resultado = cursor.fetchone()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo consultar la base de datos: {e}")
            return

        if not resultado or not verificar_contrasena(contrasena_ingresada, resultado[1]):
            QMessageBox.warning(self, "Error de Acceso", "Usuario o contraseña incorrectos.")
            return

        usuario, _, rol_usuario, estado, nombres_emp, apellidos_emp = resultado

        if estado != "Activo":
            QMessageBox.warning(self, "Usuario inactivo", "Este usuario está inactivo. Consulte con un administrador.")
            return

        if rol_usuario not in ROLES_CON_ACCESO:
            QMessageBox.warning(self, "Sin acceso", f"El rol '{rol_usuario}' no tiene acceso al sistema.")
            return

        # Si es un usuario por defecto (como admin) que no tiene empleado asociado, usamos su nombre de usuario
        if nombres_emp:
            nombre_completo = f"{nombres_emp} {apellidos_emp}"
        else:
            nombre_completo = usuario.capitalize()

        self.dashboard = VentanaDashboard(rol_usuario, nombre_completo)
        self.dashboard.show()
        self.close()


class VentanaDashboard(QtWidgets.QMainWindow):
    def __init__(self, rol_usuario, nombre_usuario="Usuario"):
        super().__init__()
        self.ui = Ui_Dashboard()
        self.ui.setupUi(self)

        self.rol_actual = rol_usuario

        # Mostramos el nombre real de la persona en lugar del rol
        self.ui.lblUsuario.setText(f" USUARIO: {nombre_usuario}")

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


    def aplicar_permisos(self, rol):
        permitidos, pagina = PERMISOS.get(rol, ([], None))
        for nombre in MODULOS:
            getattr(self.ui, nombre).setVisible(nombre in permitidos)
        if pagina:
            self.ui.StackedWidget.setCurrentWidget(getattr(self.ui, pagina))

    def cerrar_sesion(self):
        self.login = VentanaLogin()
        self.login.show()
        self.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Iniciamos mostrando la ventana de Login
    login = VentanaLogin()
    login.show()

    sys.exit(app.exec())
