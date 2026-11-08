from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import QMarginsF
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QPageLayout, QPageSize
from database import GestorBaseDatos
from ui_caja import Ui_MainWindow as UiCajaWindow
from datetime import datetime
import os

class VentanaCaja(QtWidgets.QMainWindow):
    def __init__(self, mesa_actual, total_pagar, callback_exito=None):
        super().__init__()
        self.ui = UiCajaWindow()
        self.ui.setupUi(self)
        self.db = GestorBaseDatos()
        self.mesa_actual = mesa_actual
        self.total_pagar = total_pagar
        self.callback_exito = callback_exito
        self.pago_realizado = False  # Controla si ya se cobró

        # Textos iniciales
        if hasattr(self.ui, "label"):
            self.ui.label.setText(f"CAJA / COBRO - {self.mesa_actual}")
        if hasattr(self.ui, "lineEdit"):
            self.ui.lineEdit.setText(f"S/. {self.total_pagar:.2f}")
            self.ui.lineEdit.setReadOnly(True)

        # 1. Configurar ComboBox de Método de Pago
        if hasattr(self.ui, "comboBox"):
            self.ui.comboBox.clear()
            self.ui.comboBox.addItems(["Efectivo", "Tarjeta", "Yape", "Plin"])
            self.ui.comboBox.currentIndexChanged.connect(self.verificar_metodo_pago)

        # 2. Configurar Radios de Comprobante (Boleta Simple / Factura)
        if hasattr(self.ui, "radioButton") and hasattr(self.ui, "radioButton_2"):
            self.ui.radioButton.setChecked(True)  # Por defecto Boleta Simple
            self.ui.radioButton.toggled.connect(self.cambiar_tipo_comprobante)
            self.ui.radioButton_2.toggled.connect(self.cambiar_tipo_comprobante)
            self.cambiar_tipo_comprobante()

        # Conexiones de botones principales
        if hasattr(self.ui, "pushButton_3"):  # Confirmar Pago
            self.ui.pushButton_3.clicked.connect(self.confirmar_y_facturar)
        if hasattr(self.ui, "pushButton_2"):  # Botón de Cancelar / Volver
            self.ui.pushButton_2.clicked.connect(self.cerrar_o_volver)

        # Conexión del botón "Buscar" (Simulador Reniec / Sunat)
        if hasattr(self.ui, "pushButton"):
            self.ui.pushButton.clicked.connect(self.buscar_cliente_bd)

        # Cálculo dinámico de vuelto
        if hasattr(self.ui, "lineEdit_4"):
            self.ui.lineEdit_4.textChanged.connect(self.calcular_vuelto)

        if hasattr(self.ui, "lineEdit_5"):
            self.ui.lineEdit_5.setReadOnly(True)

    def cambiar_tipo_comprobante(self):
        es_factura = self.ui.radioButton_2.isChecked() if hasattr(self.ui, "radioButton_2") else False
        campos = [getattr(self.ui, "lineEdit_2", None), getattr(self.ui, "lineEdit_3", None)]
        boton_buscar = getattr(self.ui, "pushButton", None)

        for campo in campos:
            if campo:
                campo.setEnabled(es_factura)
                if not es_factura:
                    campo.clear()
                    
        if boton_buscar:
            boton_buscar.setEnabled(es_factura)

    def buscar_cliente_bd(self):
        dni_ruc = self.ui.lineEdit_2.text().strip() if hasattr(self.ui, "lineEdit_2") else ""
        if not dni_ruc:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "Ingrese un número de DNI o RUC para buscar.")
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT nombre FROM clientes WHERE documento = ?", (dni_ruc,))
                resultado = cursor.fetchone()

            if resultado:
                nombre_cliente = resultado[0]
                if hasattr(self.ui, "lineEdit_3"):
                    self.ui.lineEdit_3.setText(nombre_cliente)
            else:
                QtWidgets.QMessageBox.information(
                    self.ui.centralwidget, 
                    "No encontrado", 
                    "El documento no está registrado en la base de datos de clientes."
                )
        except Exception as e:
            print(f"Error al buscar cliente en la BD: {e}")

    def verificar_metodo_pago(self):
        metodo = self.ui.comboBox.currentText() if hasattr(self.ui, "comboBox") else "Efectivo"
        txt_paga = getattr(self.ui, "lineEdit_4", None)
        txt_vuelto = getattr(self.ui, "lineEdit_5", None)

        if metodo == "Efectivo":
            if txt_paga: txt_paga.setEnabled(True)
            if txt_vuelto: txt_vuelto.setEnabled(True)
        else:
            if txt_paga: 
                txt_paga.setText(f"{self.total_pagar:.2f}")
                txt_paga.setEnabled(False)
            if txt_vuelto: 
                txt_vuelto.setText("S/. 0.00")
                txt_vuelto.setEnabled(False)

    def calcular_vuelto(self):
        try:
            paga_con = float(self.ui.lineEdit_4.text().strip() or 0)
            vuelto = paga_con - self.total_pagar
            if hasattr(self.ui, "lineEdit_5"):
                self.ui.lineEdit_5.setText(f"S/. {max(0, vuelto):.2f}")
        except ValueError:
            if hasattr(self.ui, "lineEdit_5"):
                self.ui.lineEdit_5.setText("S/. 0.00")

    def obtener_detalles_mesa(self):
        items_agrupados = {}
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    SELECT producto, cantidad, precio_unitario, subtotal 
                    FROM detalle_pedidos 
                    WHERE mesa = ?
                """, (self.mesa_actual,))
                registros = cursor.fetchall()
                
                for prod, cant, p_unit, sub in registros:
                    if prod in items_agrupados:
                        items_agrupados[prod]['cantidad'] += int(cant)
                        items_agrupados[prod]['subtotal'] += float(sub)
                    else:
                        items_agrupados[prod] = {
                            'cantidad': int(cant),
                            'precio_unitario': float(p_unit),
                            'subtotal': float(sub)
                        }
                        
            items = [
                (prod, datos['cantidad'], datos['precio_unitario'], datos['subtotal'])
                for prod, datos in items_agrupados.items()
            ]
        except Exception as e:
            print(f"Error al obtener detalle de productos: {e}")
            items = []
        return items

    def confirmar_y_facturar(self):
        """Procesa el pago, genera el ticket, muestra la alerta de éxito y al aceptar regresa al panel de mesas"""
        metodo_pago = self.ui.comboBox.currentText() if hasattr(self.ui, "comboBox") else "Efectivo"
        
        monto_recibido = self.total_pagar
        if metodo_pago == "Efectivo":
            try:
                monto_recibido = float(self.ui.lineEdit_4.text().strip() or 0)
                if monto_recibido < self.total_pagar:
                    QtWidgets.QMessageBox.warning(self, "Aviso", "El monto recibido en efectivo es menor al total a pagar.")
                    return
            except ValueError:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Ingrese un monto en efectivo válido.")
                return

        es_factura = hasattr(self.ui, "radioButton_2") and self.ui.radioButton_2.isChecked()
        
        if es_factura:
            cliente_doc = self.ui.lineEdit_2.text().strip() if hasattr(self.ui, "lineEdit_2") else ""
            cliente_nombre = self.ui.lineEdit_3.text().strip() if hasattr(self.ui, "lineEdit_3") else ""
            if not cliente_doc or not cliente_nombre:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Para facturas debe completar el DNI/RUC y Razón Social.")
                return
        else:
            cliente_nombre = "CLIENTE VARIOS"
            cliente_doc = "-"

        productos = self.obtener_detalles_mesa()

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("UPDATE pedidos SET estado = 'PAGADO' WHERE mesa = ? AND estado != 'PAGADO'", (self.mesa_actual,))
                cursor.execute("DELETE FROM detalle_pedidos WHERE mesa = ?", (self.mesa_actual,))
                conexion.commit()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo guardar el cobro en la BD: {e}")
            return

        # 1. Generar e imprimir el ticket PDF
        self.imprimir_ticket(metodo_pago, monto_recibido, cliente_nombre, cliente_doc, productos)
        
        # 2. Mostrar la alerta de éxito. Al hacer clic en "Aceptar", avanzará al cierre automático.
        QtWidgets.QMessageBox.information(
            self, 
            "Cobro Exitoso", 
            f"¡Cobro exitoso! El pago de la {self.mesa_actual} se guardó correctamente y se generó el comprobante."
        )
        
        # 3. Ejecutar el callback para regresar al panel de mesas y cerrar la ventana de caja
        if self.callback_exito:
            self.callback_exito()
            
        self.close()

    def cerrar_o_volver(self):
        """Si ya se pagó, ejecuta el callback para regresar al panel general de mesas; si no, solo cierra"""
        if self.pago_realizado and self.callback_exito:
            self.callback_exito()
        self.close()

    def imprimir_ticket(self, metodo_pago, monto_recibido, cliente_nombre, cliente_doc, productos):
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        hora_actual = datetime.now().strftime("%H:%M:%S")
        
        subtotal = self.total_pagar / 1.18
        igv = self.total_pagar - subtotal
        vuelto = max(0, monto_recibido - self.total_pagar)

        es_factura = hasattr(self.ui, "radioButton_2") and self.ui.radioButton_2.isChecked()
        nombre_carpeta = "facturas" if es_factura else "boletas"
        tipo_comprobante = "FACTURA ELECTRÓNICA" if es_factura else "BOLETA DE VENTA ELECTRÓNICA"

        ruta_carpeta = os.path.join(os.getcwd(), nombre_carpeta)
        if not os.path.exists(ruta_carpeta):
            os.makedirs(ruta_carpeta)

        nombre_archivo = f"{'F' if es_factura else 'B'}_{self.mesa_actual.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        ruta_pdf = os.path.join(ruta_carpeta, nombre_archivo)

        filas_productos = ""
        for prod, cant, p_unit, sub in productos:
            filas_productos += f"""
                <tr>
                    <td style="text-align: center; width: 10%;">{cant}</td>
                    <td style="text-align: left; width: 48%;">{prod}</td>
                    <td style="text-align: right; width: 21%; white-space: nowrap;">S/{p_unit:.2f}</td>
                    <td style="text-align: right; width: 21%; white-space: nowrap;">S/{sub:.2f}</td>
                </tr>
            """

        html_ticket = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Courier New', Courier, monospace;
                    font-size: 10px;
                    width: 220px;
                    margin: 0 auto;
                    padding: 0;
                    color: #000;
                }}
                .center {{ text-align: center; }}
                .bold {{ font-weight: bold; }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 6px;
                    margin-bottom: 6px;
                }}
                th {{
                    font-size: 10px;
                    border-bottom: 1px solid #000;
                    padding: 3px 2px;
                    white-space: nowrap;
                }}
                td {{
                    font-size: 10px;
                    padding: 3px 2px;
                    vertical-align: top;
                }}
                .line {{
                    border-top: 1px dashed #000;
                    margin: 5px 0;
                }}
                .totales {{
                    text-align: right;
                    font-size: 10px;
                    padding-right: 5px;
                    white-space: nowrap;
                }}
            </style>
        </head>
        <body>
            <div class="center bold" style="font-size: 12px;">SUMAQ ÑAN RESTAURANTE</div>
            <div class="center">Sabores que nos unen</div>
            <div class="center">RUC: 20601234567</div>
            <div class="center">Av. Los Andes 123, Lima - Perú</div>
            <div class="center">Teléfono: 987 654 321</div>
            
            <div class="line"></div>
            <div class="center bold">{tipo_comprobante}</div>
            <div class="center">N.º B001-{datetime.now().strftime('%H%M%S')}</div>
            <div>Fecha: {fecha_actual} &nbsp; Hora: {hora_actual}</div>
            
            <div class="line"></div>
            <div class="bold">DATOS DEL CLIENTE</div>
            <div>Cliente: {cliente_nombre}</div>
            <div>Doc: {cliente_doc}</div>
            <div>Mesa: {self.mesa_actual}</div>
            
            <div class="line"></div>
            <table>
                <tr>
                    <th style="text-align: center; width: 10%;">Cant</th>
                    <th style="text-align: left; width: 48%;">Plato</th>
                    <th style="text-align: right; width: 21%;">P.U.</th>
                    <th style="text-align: right; width: 21%;">Total</th>
                </tr>
                {filas_productos}
            </table>
            
            <div class="line"></div>
            <div class="totales">Subtotal: S/ {subtotal:.2f}</div>
            <div class="totales">IGV (18%): S/ {igv:.2f}</div>
            <div class="totales bold" style="font-size: 11px;">TOTAL A PAGAR: S/ {self.total_pagar:.2f}</div>
            
            <div class="line"></div>
            <table style="margin: 0; width: 100%;">
                <tr>
                    <td style="text-align: left; border: none; padding: 1px 0; width: 55%;">Forma de pago:</td>
                    <td style="text-align: right; border: none; padding: 1px 0; width: 45%; white-space: nowrap;" class="bold">{metodo_pago}</td>
                </tr>
                <tr>
                    <td style="text-align: left; border: none; padding: 1px 0; width: 55%;">Monto recibido:</td>
                    <td style="text-align: right; border: none; padding: 1px 0; width: 45%; white-space: nowrap;" class="bold">S/ {monto_recibido:.2f}</td>
                </tr>
                <tr>
                    <td style="text-align: left; border: none; padding: 1px 0; width: 55%;">Vuelto:</td>
                    <td style="text-align: right; border: none; padding: 1px 0; width: 45%; white-space: nowrap;" class="bold">S/ {vuelto:.2f}</td>
                </tr>
            </table>
            
            <div class="line"></div>
            <div class="center">¡Gracias por su visita!</div>
            <div class="center bold" style="margin-top: 3px;">SUMAQ ÑAN RESTAURANTE</div>
            <div class="center" style="font-size: 9px;">La tradición también se sirve en la mesa.</div>
        </body>
        </html>
        """

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(ruta_pdf)
        
        page_size = QPageSize(QtCore.QSizeF(80, 220), QPageSize.Unit.Millimeter)
        page_layout = QPageLayout(page_size, QPageLayout.Orientation.Portrait, QMarginsF(1, 1, 1, 1))
        printer.setPageLayout(page_layout)

        documento = QtGui.QTextDocument()
        documento.setHtml(html_ticket)
        
        ancho_pts = printer.pageRect(QPrinter.Unit.Point).width()
        documento.setPageSize(QtCore.QSizeF(ancho_pts, printer.pageRect(QPrinter.Unit.Point).height()))

        getattr(documento, 'print')(printer)

        try:
            os.startfile(os.path.abspath(ruta_pdf))
        except Exception as e:
            print(f"No se pudo abrir el PDF automáticamente: {e}")