from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import QMarginsF
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QPageLayout, QPageSize
from database import GestorBaseDatos
from ui_caja import Ui_MainWindow as UiCajaWindow
from datetime import datetime
from html import escape
import os

METODOS_PAGO = ["Efectivo", "Tarjeta", "Yape", "Plin"]


class VentanaCaja(QtWidgets.QMainWindow):
    def __init__(self, mesa_actual, total_pagar, callback_exito=None):
        super().__init__()
        self.ui = UiCajaWindow()
        self.ui.setupUi(self)
        self.db = GestorBaseDatos()
        self.mesa_actual = mesa_actual
        self.total_pagar = round(total_pagar, 2)
        self.callback_exito = callback_exito
        self.pago_realizado = False  # Controla si ya se cobró

        # Textos iniciales
        self.ui.lblCaja.setText(f"CAJA / COBRO - {self.mesa_actual}")
        self.ui.txtTotalPagar.setText(f"S/. {self.total_pagar:.2f}")
        self.ui.txtTotalPagar.setReadOnly(True)
        self.ui.txtVuelto.setReadOnly(True)
        # Caja.ui los marca de solo lectura, pero para emitir una factura hay que poder escribirlos
        self.ui.txtDNI.setReadOnly(False)
        self.ui.txtRazon.setReadOnly(False)

        # 1. Método de pago
        self.ui.cmbMetodo.clear()
        self.ui.cmbMetodo.addItems(METODOS_PAGO)
        self.ui.cmbMetodo.currentIndexChanged.connect(self.verificar_metodo_pago)

        # 2. Tipo de comprobante (Boleta Simple / Factura)
        self.ui.rbBoleta.setChecked(True)
        self.ui.rbFactura.toggled.connect(self.cambiar_tipo_comprobante)
        self.cambiar_tipo_comprobante()

        # 3. Botones
        self.ui.btnPagar.clicked.connect(self.confirmar_y_facturar)
        self.ui.btnCancelar.clicked.connect(self.cerrar_o_volver)
        self.ui.btnBuscar.clicked.connect(self.buscar_cliente_bd)

        # 4. Cálculo dinámico de vuelto
        self.ui.txtPaga.textChanged.connect(self.calcular_vuelto)

    def es_factura(self):
        return self.ui.rbFactura.isChecked()

    def cambiar_tipo_comprobante(self):
        es_factura = self.es_factura()
        for campo in (self.ui.txtDNI, self.ui.txtRazon):
            campo.setEnabled(es_factura)
            if not es_factura:
                campo.clear()
        self.ui.btnBuscar.setEnabled(es_factura)

    def buscar_cliente_bd(self):
        dni_ruc = self.ui.txtDNI.text().strip()
        if not dni_ruc:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Ingrese un número de DNI o RUC para buscar.")
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT nombre FROM clientes WHERE documento = ?", (dni_ruc,))
                resultado = cursor.fetchone()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo buscar el cliente: {e}")
            return

        if resultado:
            self.ui.txtRazon.setText(resultado[0])
        else:
            QtWidgets.QMessageBox.information(
                self, "No encontrado",
                "El documento no está registrado en la base de datos de clientes."
            )

    def leer_monto_recibido(self):
        """Monto escrito en 'Paga con' (acepta coma o punto decimal), o None si no es un número."""
        try:
            return float(self.ui.txtPaga.text().strip().replace(",", ".") or 0)
        except ValueError:
            return None

    def verificar_metodo_pago(self):
        if self.ui.cmbMetodo.currentText() == "Efectivo":
            self.ui.txtPaga.setEnabled(True)
            self.ui.txtVuelto.setEnabled(True)
        else:
            self.ui.txtPaga.setText(f"{self.total_pagar:.2f}")
            self.ui.txtPaga.setEnabled(False)
            self.ui.txtVuelto.setText("S/. 0.00")
            self.ui.txtVuelto.setEnabled(False)

    def calcular_vuelto(self):
        paga_con = self.leer_monto_recibido()
        vuelto = max(0, paga_con - self.total_pagar) if paga_con is not None else 0
        self.ui.txtVuelto.setText(f"S/. {vuelto:.2f}")

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
        except Exception as e:
            print(f"Error al obtener detalle de productos: {e}")

        return [
            (prod, datos['cantidad'], datos['precio_unitario'], datos['subtotal'])
            for prod, datos in items_agrupados.items()
        ]

    def confirmar_y_facturar(self):
        """Registra la venta, genera el ticket y regresa al panel de mesas"""
        metodo_pago = self.ui.cmbMetodo.currentText()

        monto_recibido = self.total_pagar
        if metodo_pago == "Efectivo":
            monto_recibido = self.leer_monto_recibido()
            if monto_recibido is None:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Ingrese un monto en efectivo válido.")
                return
            if monto_recibido < self.total_pagar:
                QtWidgets.QMessageBox.warning(self, "Aviso", "El monto recibido en efectivo es menor al total a pagar.")
                return
        vuelto = round(max(0, monto_recibido - self.total_pagar), 2)

        es_factura = self.es_factura()
        if es_factura:
            cliente_doc = self.ui.txtDNI.text().strip()
            cliente_nombre = self.ui.txtRazon.text().strip()
            if not cliente_doc or not cliente_nombre:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Para facturas debe completar el DNI/RUC y Razón Social.")
                return
        else:
            cliente_nombre = "CLIENTE VARIOS"
            cliente_doc = "-"

        serie = "F001" if es_factura else "B001"
        tipo = "FACTURA" if es_factura else "BOLETA"
        ahora = datetime.now()
        productos = self.obtener_detalles_mesa()
        numero = None

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()

                # Si la comanda cambió con la caja abierta, el total mostrado ya no es válido
                cursor.execute("SELECT COALESCE(SUM(subtotal), 0) FROM detalle_pedidos WHERE mesa = ?",
                               (self.mesa_actual,))
                total_bd = round(cursor.fetchone()[0], 2)

                if abs(total_bd - self.total_pagar) < 0.005:
                    # Número correlativo por serie: B001-00000001, B001-00000002, ...
                    cursor.execute("SELECT COALESCE(MAX(numero), 0) + 1 FROM ventas WHERE serie = ?", (serie,))
                    numero = cursor.fetchone()[0]

                    cursor.execute("""
                        INSERT INTO ventas (fecha, mesa, tipo_comprobante, serie, numero, cliente_documento,
                                            cliente_nombre, metodo_pago, total, monto_recibido, vuelto)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (ahora.strftime("%Y-%m-%d %H:%M:%S"), self.mesa_actual, tipo, serie, numero,
                          cliente_doc, cliente_nombre, metodo_pago, self.total_pagar, monto_recibido, vuelto))

                    # El detalle se copia al historial antes de liberar la mesa
                    cursor.execute("""
                        INSERT INTO detalle_ventas (id_venta, codigo, producto, cantidad, precio_unitario, subtotal)
                        SELECT ?, codigo, producto, cantidad, precio_unitario, subtotal
                        FROM detalle_pedidos WHERE mesa = ?
                    """, (cursor.lastrowid, self.mesa_actual))

                    cursor.execute("UPDATE pedidos SET estado = 'PAGADO' WHERE mesa = ? AND estado != 'PAGADO'",
                                   (self.mesa_actual,))
                    cursor.execute("DELETE FROM detalle_pedidos WHERE mesa = ?", (self.mesa_actual,))
                    conexion.commit()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo guardar el cobro en la BD: {e}")
            return

        if numero is None:
            QtWidgets.QMessageBox.warning(
                self, "Pedido modificado",
                f"El pedido de la {self.mesa_actual} cambió mientras la caja estaba abierta "
                f"(total actual: S/ {total_bd:.2f}). Cierre esta ventana y vuelva a cobrar."
            )
            return

        self.pago_realizado = True
        numero_comprobante = f"{serie}-{numero:08d}"

        # 1. Generar e imprimir el ticket PDF (la venta ya quedó registrada aunque esto falle)
        try:
            self.imprimir_ticket(numero_comprobante, ahora, metodo_pago, monto_recibido, vuelto,
                                 cliente_nombre, cliente_doc, productos)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Comprobante",
                                          f"La venta {numero_comprobante} se registró, pero no se pudo generar el PDF: {e}")

        # 2. Alerta de éxito
        QtWidgets.QMessageBox.information(
            self,
            "Cobro Exitoso",
            f"¡Cobro exitoso! El pago de la {self.mesa_actual} se guardó correctamente "
            f"con el comprobante {numero_comprobante}."
        )

        # 3. Regresar al panel de mesas y cerrar la ventana de caja
        if self.callback_exito:
            self.callback_exito()

        self.close()

    def cerrar_o_volver(self):
        """Si ya se pagó, ejecuta el callback para regresar al panel general de mesas; si no, solo cierra"""
        if self.pago_realizado and self.callback_exito:
            self.callback_exito()
        self.close()

    def imprimir_ticket(self, numero_comprobante, fecha_hora, metodo_pago, monto_recibido, vuelto,
                        cliente_nombre, cliente_doc, productos):
        fecha_actual = fecha_hora.strftime("%d/%m/%Y")
        hora_actual = fecha_hora.strftime("%H:%M:%S")

        subtotal = self.total_pagar / 1.18
        igv = self.total_pagar - subtotal

        es_factura = numero_comprobante.startswith("F")
        nombre_carpeta = "facturas" if es_factura else "boletas"
        tipo_comprobante = "FACTURA ELECTRÓNICA" if es_factura else "BOLETA DE VENTA ELECTRÓNICA"

        ruta_carpeta = os.path.join(os.getcwd(), nombre_carpeta)
        os.makedirs(ruta_carpeta, exist_ok=True)

        nombre_archivo = f"{numero_comprobante}_{fecha_hora.strftime('%Y%m%d_%H%M%S')}.pdf"
        ruta_pdf = os.path.join(ruta_carpeta, nombre_archivo)

        filas_productos = ""
        for prod, cant, p_unit, sub in productos:
            filas_productos += f"""
                <tr>
                    <td style="text-align: center; width: 10%;">{cant}</td>
                    <td style="text-align: left; width: 48%;">{escape(str(prod))}</td>
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
            <div class="center">N.º {numero_comprobante}</div>
            <div>Fecha: {fecha_actual} &nbsp; Hora: {hora_actual}</div>

            <div class="line"></div>
            <div class="bold">DATOS DEL CLIENTE</div>
            <div>Cliente: {escape(cliente_nombre)}</div>
            <div>Doc: {escape(cliente_doc)}</div>
            <div>Mesa: {escape(self.mesa_actual)}</div>

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
