from PyQt6 import QtWidgets
from datetime import datetime
from database import GestorBaseDatos
from Dasboard.Resumen import GestionResumen

class GestionPedidos:
    def __init__(self, ui_dashboard, usuario=""):
        self.ui = ui_dashboard
        self.db = GestorBaseDatos()
        self.mesa_actual = ""

        # Inicializamos el gestor del resumen para manejar los platos por mesa
        self.gestor_resumen = GestionResumen(self.ui, usuario)
        
        # Conectar los botones del salón y actualizar los colores/estados al iniciar
        self.conectar_eventos()
        self.actualizar_estado_mesas()

    def conectar_eventos(self):
        """Conecta los botones de las mesas del salón a la lógica de selección"""
        if hasattr(self.ui, "btnMesa1"):
            self.ui.btnMesa1.clicked.connect(lambda: self.seleccionar_mesa("MESA 01"))
        if hasattr(self.ui, "btnMesa2"):
            self.ui.btnMesa2.clicked.connect(lambda: self.seleccionar_mesa("MESA 02"))
        if hasattr(self.ui, "btnMesa3"):
            self.ui.btnMesa3.clicked.connect(lambda: self.seleccionar_mesa("MESA 03"))
        if hasattr(self.ui, "btnMesa4"):
            self.ui.btnMesa4.clicked.connect(lambda: self.seleccionar_mesa("MESA 04"))
        if hasattr(self.ui, "btnMesa5"):
            self.ui.btnMesa5.clicked.connect(lambda: self.seleccionar_mesa("MESA 05"))
        if hasattr(self.ui, "btnMesa6"):
            self.ui.btnMesa6.clicked.connect(lambda: self.seleccionar_mesa("MESA 06"))
        if hasattr(self.ui, "btnLlevar"):
            self.ui.btnLlevar.clicked.connect(lambda: self.seleccionar_mesa("PARA LLEVAR"))

        # Botón para volver al salón desde la página de resumen
        if hasattr(self.ui, 'btnVolver'):
            self.ui.btnVolver.clicked.connect(self.regresar_al_salon)

    def obtener_estado_mesa_db(self, mesa):
        """Calcula el total real sumando todos los productos de la mesa (pendientes o enviados)"""
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                
                # Sumamos los subtotales de todos los productos de la mesa sin filtrar por estado
                cursor.execute("""
                    SELECT SUM(subtotal) 
                    FROM detalle_pedidos 
                    WHERE mesa = ?
                """, (mesa,))
                resultado = cursor.fetchone()
                
                total = float(resultado[0]) if resultado and resultado[0] is not None else 0.0
                
                if total > 0:
                    return "OCUPADA", total
                    
                # 2. Si no hay ítems en el detalle, revisamos si la cabecera en pedidos fue abierta
                cursor.execute("""
                    SELECT estado 
                    FROM pedidos 
                    WHERE mesa = ? AND estado != 'PAGADO'
                """, (mesa,))
                res_pedido = cursor.fetchone()
                
                if res_pedido:
                    return "OCUPADA", 0.0
        except Exception as e:
            print(f"Error al consultar estado de la mesa {mesa}: {e}")
            
        return "LIBRE", 0.0

    def actualizar_estado_mesas(self):
        """Recorre las mesas, consulta la BD y actualiza textos y colores dinámicamente"""
        mesas = [
            ("MESA 01", getattr(self.ui, "btnMesa1", None)),
            ("MESA 02", getattr(self.ui, "btnMesa2", None)),
            ("MESA 03", getattr(self.ui, "btnMesa3", None)),
            ("MESA 04", getattr(self.ui, "btnMesa4", None)),
            ("MESA 05", getattr(self.ui, "btnMesa5", None)),
            ("MESA 06", getattr(self.ui, "btnMesa6", None)),
            ("PARA LLEVAR", getattr(self.ui, "btnLlevar", None))
        ]

        # Estilos visuales modernos (QSS) para los botones del salón
        estilo_libre = """
            QPushButton {
                background-color: #EAFAF1;
                color: #27AE60;
                border: 2px solid #27AE60;
                border-radius: 8px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover { background-color: #D4EFDF; }
        """

        estilo_ocupada = """
            QPushButton {
                background-color: #FDEDEC;
                color: #C0392B;
                border: 2px solid #C0392B;
                border-radius: 8px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover { background-color: #FADBD8; }
        """

        for nombre_mesa, boton in mesas:
            if not boton:
                continue

            estado, total = self.obtener_estado_mesa_db(nombre_mesa)

            # Actualiza el texto manteniendo el formato visual de tarjetas
            if nombre_mesa == "PARA LLEVAR":
                boton.setText(f"PARA LLEVAR\n{estado}\nS/ {total:.2f}")
            else:
                boton.setText(f"{nombre_mesa}\n{estado}\nS/ {total:.2f}")

            # Aplica el color correspondiente según la disponibilidad en la BD
            if estado == "LIBRE":
                boton.setStyleSheet(estilo_libre)
            else:
                boton.setStyleSheet(estilo_ocupada)

    def seleccionar_mesa(self, nombre_mesa):
        """Al seleccionar una mesa, la marca como ocupada de inmediato y abre su resumen"""
        self.mesa_actual = nombre_mesa
        
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                # Verificamos si la mesa ya tiene una cabecera activa en la BD
                cursor.execute("""
                    SELECT id FROM pedidos 
                    WHERE mesa = ? AND estado != 'PAGADO'
                """, (self.mesa_actual,))
                existe = cursor.fetchone()
                
                # Si la mesa está totalmente nueva/libre, creamos un registro inicial "OCUPADA" con S/. 0.00
                if not existe:
                    hora_actual = datetime.now().strftime("%H:%M:%S")
                    cursor.execute("""
                        INSERT INTO pedidos (mesa, hora, total, estado)
                        VALUES (?, ?, 0.0, 'OCUPADA')
                    """, (self.mesa_actual, hora_actual))
                    conexion.commit()
        except Exception as e:
            print(f"Error al registrar estado inicial de la mesa: {e}")

        # Cargamos los productos correspondientes a esta mesa en el módulo de resumen
        self.gestor_resumen.cargar_pedido_mesa(self.mesa_actual)
        
        # Actualiza el indicador superior y cambia de vista
        if hasattr(self.ui, 'lblAtender'):
            self.ui.lblAtender.setText(f"Atendiendo: {self.mesa_actual}")
        
        if hasattr(self.ui, 'StackedWidget') and hasattr(self.ui, 'pageResumen'):
            self.ui.StackedWidget.setCurrentWidget(self.ui.pageResumen)

    def regresar_al_salon(self):
        """Regresa al plano de mesas y refresca automáticamente los estados y montos de las tarjetas"""
        self.mesa_actual = ""
        self.actualizar_estado_mesas()
        
        if hasattr(self.ui, 'StackedWidget') and hasattr(self.ui, 'pagePedido'):
            self.ui.StackedWidget.setCurrentWidget(self.ui.pagePedido)