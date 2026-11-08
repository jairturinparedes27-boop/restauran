import os
from datetime import datetime
from html import escape
from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import QDate
from PyQt6.QtPrintSupport import QPrinter
from database import GestorBaseDatos
from Dasboard.estilo import ESTILO_TABLA, ajustar_tabla

COLUMNAS_VENTAS = ["Comprobante", "Fecha / Hora", "Tipo", "Documento", "Cliente", "Mesa",
                   "Método de pago", "Usuario", "Total"]


def fecha_corta(fecha):
    return datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")


def dia(iso):
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")


class GestionReportes:
    """Página de Reportes: ventas cobradas entre dos fechas, con exportación a Excel y PDF."""

    def __init__(self, ui_dashboard):
        self.ui = ui_dashboard
        self.db = GestorBaseDatos()
        self.ventas = []          # filas del último filtro
        self.ids = []             # id de cada venta de self.ventas (para ver su detalle)
        self.rango = None         # (inicio, fin) del último filtro, en formato AAAA-MM-DD
        self.dialogo_detalle = None

        self.ui.tableReporte.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.tableReporte.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.txtTotalR.setReadOnly(True)

        # Por defecto, las ventas de hoy
        for campo in (self.ui.dtInicioR, self.ui.dtFinR):
            campo.setDisplayFormat("dd/MM/yyyy")
            campo.setCalendarPopup(True)
            campo.setDate(QDate.currentDate())

        self.ui.btnFiltrarR.clicked.connect(lambda: self.filtrar())
        self.ui.btnExcelR.clicked.connect(self.exportar_excel)
        self.ui.btnPdfR.clicked.connect(self.exportar_pdf)
        self.ui.StackedWidget.currentChanged.connect(self.al_cambiar_pagina)
        # Al cambiar una fecha el reporte se actualiza solo (sin ventanas de aviso mientras se elige)
        self.ui.dtInicioR.dateChanged.connect(lambda _: self.filtrar(silencioso=True))
        self.ui.dtFinR.dateChanged.connect(lambda _: self.filtrar(silencioso=True))
        # Doble clic en una venta: ver su detalle
        self.ui.tableReporte.cellDoubleClicked.connect(lambda fila, _col: self.abrir_detalle(fila))

        self.filtrar()

    def al_cambiar_pagina(self, _indice):
        if self.ui.StackedWidget.currentWidget() is self.ui.pageReportes:
            self.filtrar(silencioso=True)

    def aviso(self, titulo, mensaje):
        QtWidgets.QMessageBox.warning(self.ui.centralwidget, titulo, mensaje)

    # ---------- Consultas ----------

    def consultar(self, sql, inicio, fin):
        with self.db.conectar() as conexion:
            return conexion.execute(sql, (f"{inicio} 00:00:00", f"{fin} 23:59:59")).fetchall()

    def filtrar(self, silencioso=False):
        inicio = self.ui.dtInicioR.date().toString("yyyy-MM-dd")
        fin = self.ui.dtFinR.date().toString("yyyy-MM-dd")
        if inicio > fin:
            self.ventas, self.ids, self.rango = [], [], None
            self.mostrar_vacio("La fecha de inicio es posterior a la fecha fin.")
            if not silencioso:
                self.aviso("Fechas inválidas", "La fecha de inicio es posterior a la fecha fin.")
            return

        try:
            filas = self.consultar("""
                SELECT id, serie || '-' || printf('%08d', numero), fecha, tipo_comprobante, cliente_documento,
                       cliente_nombre, mesa, metodo_pago, COALESCE(usuario, ''), total
                FROM ventas WHERE fecha BETWEEN ? AND ? ORDER BY fecha DESC, id DESC
            """, inicio, fin)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudieron consultar las ventas: {e}")
            return
        self.ids = [fila[0] for fila in filas]
        self.ventas = [fila[1:] for fila in filas]
        self.rango = (inicio, fin)

        if not self.ventas:
            rango = dia(inicio) if inicio == fin else f"el {dia(inicio)} y el {dia(fin)}"
            self.mostrar_vacio(f"No hay ventas registradas {'el ' if inicio == fin else 'entre '}{rango}.")
            return

        tabla = self.ui.tableReporte
        tabla.clearSpans()
        tabla.setRowCount(0)
        for i, (comprobante, fecha, _tipo, documento, _cliente, mesa, _metodo, usuario, total) in enumerate(self.ventas):
            tabla.insertRow(i)
            for j, valor in enumerate([comprobante, fecha_corta(fecha), documento, mesa, usuario, f"S/. {total:.2f}"]):
                item = QtWidgets.QTableWidgetItem(str(valor))
                item.setToolTip("Doble clic para ver el detalle de la venta")
                if j == 5:
                    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
                tabla.setItem(i, j, item)

        total = self.total()
        self.ui.txtTotalR.setText(f"{total:,.2f}")
        cantidad = len(self.ventas)
        self.ui.lblResumenR.setText(f"{cantidad} {'venta' if cantidad == 1 else 'ventas'} · "
                                    f"ticket promedio S/ {total / cantidad:,.2f}")

    def mostrar_vacio(self, mensaje):
        """Una sola fila con el mensaje, ocupando todo el ancho de la tabla."""
        tabla = self.ui.tableReporte
        tabla.clearSpans()
        tabla.setRowCount(1)
        tabla.setSpan(0, 0, 1, tabla.columnCount())
        item = QtWidgets.QTableWidgetItem(mensaje)
        item.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QtGui.QColor("#7f8c8d"))
        tabla.setItem(0, 0, item)
        self.ui.txtTotalR.setText("0.00")
        self.ui.lblResumenR.setText("")

    def detalle_venta(self, id_venta):
        """Cabecera y platos de una venta."""
        with self.db.conectar() as conexion:
            cabecera = conexion.execute("""
                SELECT serie || '-' || printf('%08d', numero), fecha, tipo_comprobante, cliente_documento,
                       cliente_nombre, mesa, metodo_pago, COALESCE(usuario, ''), total, monto_recibido, vuelto
                FROM ventas WHERE id = ?
            """, (id_venta,)).fetchone()
            platos = conexion.execute("""
                SELECT producto, cantidad, precio_unitario, subtotal FROM detalle_ventas
                WHERE id_venta = ? ORDER BY id
            """, (id_venta,)).fetchall()
        return cabecera, platos

    def abrir_detalle(self, fila):
        if fila >= len(self.ids):
            return  # fila de "no hay ventas"
        try:
            cabecera, platos = self.detalle_venta(self.ids[fila])
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo leer la venta: {e}")
            return
        comprobante, fecha, tipo, documento, cliente, mesa, metodo, usuario, total, recibido, vuelto = cabecera

        dialogo = QtWidgets.QDialog(self.ui.centralwidget.window())
        dialogo.setWindowTitle(f"Venta {comprobante}")
        dialogo.resize(520, 380)
        capa = QtWidgets.QVBoxLayout(dialogo)

        datos = QtWidgets.QLabel(
            f"<b>{tipo.capitalize()} {comprobante}</b> · {fecha_corta(fecha)}<br>"
            f"Cliente: {escape(cliente)} ({escape(documento)}) · {escape(mesa)}<br>"
            f"Pago: {escape(metodo)} · Recibido S/ {recibido:.2f} · Vuelto S/ {vuelto:.2f}"
            + (f"<br>Atendido por: {escape(usuario)}" if usuario else ""))
        capa.addWidget(datos)

        tabla = QtWidgets.QTableWidget(len(platos), 4)
        tabla.setHorizontalHeaderLabels(["Producto", "Cantidad", "P. unitario", "Subtotal"])
        tabla.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        tabla.setStyleSheet(ESTILO_TABLA)
        for i, (producto, cantidad, precio, subtotal) in enumerate(platos):
            for j, valor in enumerate([producto, cantidad, f"S/. {precio:.2f}", f"S/. {subtotal:.2f}"]):
                tabla.setItem(i, j, QtWidgets.QTableWidgetItem(str(valor)))
        ajustar_tabla(tabla, (0,))
        capa.addWidget(tabla)

        pie = QtWidgets.QLabel(f"<b>Total: S/ {total:,.2f}</b>")
        pie.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        capa.addWidget(pie)
        cerrar = QtWidgets.QPushButton("Cerrar")
        cerrar.clicked.connect(dialogo.close)
        capa.addWidget(cerrar, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        self.dialogo_detalle = dialogo
        dialogo.show()

    def total(self):
        return sum(fila[-1] for fila in self.ventas)

    def por_metodo(self):
        inicio, fin = self.rango
        return self.consultar("""
            SELECT metodo_pago, COUNT(*), SUM(total) FROM ventas
            WHERE fecha BETWEEN ? AND ? GROUP BY metodo_pago ORDER BY SUM(total) DESC
        """, inicio, fin)

    def por_producto(self):
        inicio, fin = self.rango
        return self.consultar("""
            SELECT d.producto, SUM(d.cantidad), SUM(d.subtotal)
            FROM detalle_ventas d JOIN ventas v ON v.id = d.id_venta
            WHERE v.fecha BETWEEN ? AND ? GROUP BY d.producto ORDER BY SUM(d.subtotal) DESC
        """, inicio, fin)

    # ---------- Exportación ----------

    def ruta_destino(self, extension, filtro):
        """Pregunta dónde guardar; por defecto en la carpeta 'reportes' del proyecto."""
        if not self.ventas:
            self.aviso("Sin datos", "No hay ventas en el rango filtrado. Ajuste las fechas y pulse Filtrar.")
            return None
        carpeta = os.path.join(os.getcwd(), "reportes")
        os.makedirs(carpeta, exist_ok=True)
        inicio, fin = self.rango
        sugerida = os.path.join(carpeta, f"ventas_{inicio}_a_{fin}.{extension}")
        ruta, _ = QtWidgets.QFileDialog.getSaveFileName(self.ui.centralwidget, "Guardar reporte", sugerida, filtro)
        return ruta or None

    def abrir(self, ruta):
        try:
            os.startfile(os.path.abspath(ruta))
        except Exception as e:
            print(f"No se pudo abrir el reporte automáticamente: {e}")

    def exportar_excel(self):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font, PatternFill
        except ImportError:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Falta una biblioteca",
                                           "Para exportar a Excel instale openpyxl:  pip install openpyxl")
            return

        ruta = self.ruta_destino("xlsx", "Excel (*.xlsx)")
        if not ruta:
            return

        inicio, fin = self.rango
        negrita = Font(bold=True)
        cabecera = (Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2C3E50"))
        soles = '"S/ "#,##0.00'

        def hoja(ws, titulo, columnas, filas, anchos, col_soles):
            ws.append([titulo])
            ws["A1"].font = Font(bold=True, size=13)
            ws.append([f"Del {dia(inicio)} al {dia(fin)}"])
            ws.append([])
            ws.append(columnas)
            for celda in ws[4]:
                celda.font, celda.fill = cabecera
                celda.alignment = Alignment(horizontal="center")
            for fila in filas:
                ws.append(list(fila))
            for letra, ancho in anchos.items():
                ws.column_dimensions[letra].width = ancho
            for fila in ws.iter_rows(min_row=5):
                for indice in col_soles:
                    fila[indice].number_format = soles
            ws.freeze_panes = "A5"

        try:
            libro = Workbook()
            ventas = libro.active
            ventas.title = "Ventas"
            hoja(ventas, "Reporte de ventas", COLUMNAS_VENTAS,
                 [(c, fecha_corta(f), t, d, cl, m, mp, u, tot) for c, f, t, d, cl, m, mp, u, tot in self.ventas],
                 dict(zip("ABCDEFGHI", [17, 17, 10, 14, 34, 13, 15, 14, 12])), [8])
            ventas.append([])
            ventas.append(["Total recaudado"] + [""] * 7 + [self.total()])
            ultima = ventas.max_row
            ventas.cell(ultima, 1).font = negrita
            ventas.cell(ultima, 9).font = negrita
            ventas.cell(ultima, 9).number_format = soles

            hoja(libro.create_sheet("Productos"), "Productos vendidos", ["Producto", "Cantidad", "Total"],
                 self.por_producto(), {"A": 36, "B": 11, "C": 13}, [2])
            hoja(libro.create_sheet("Métodos de pago"), "Ventas por método de pago",
                 ["Método de pago", "Ventas", "Total"], self.por_metodo(), {"A": 18, "B": 9, "C": 13}, [2])

            libro.save(ruta)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo guardar el Excel: {e}")
            return
        self.abrir(ruta)

    def exportar_pdf(self):
        ruta = self.ruta_destino("pdf", "PDF (*.pdf)")
        if not ruta:
            return

        inicio, fin = self.rango
        estilo_tabla = 'border="1" cellspacing="0" cellpadding="4" width="100%" style="border-collapse: collapse;"'

        def tabla(columnas, filas, derecha=()):
            cab = "".join(f'<th style="background-color:#2c3e50; color:white;">{escape(c)}</th>' for c in columnas)
            cuerpo = ""
            for fila in filas:
                celdas = "".join(f'<td align="{"right" if j in derecha else "left"}">{escape(str(v))}</td>'
                                 for j, v in enumerate(fila))
                cuerpo += f"<tr>{celdas}</tr>"
            return f"<table {estilo_tabla}><tr>{cab}</tr>{cuerpo}</table>"

        ventas = [(c, fecha_corta(f), cl if t == "FACTURA" else "Cliente varios", m, mp, u, f"S/ {tot:,.2f}")
                  for c, f, t, _d, cl, m, mp, u, tot in self.ventas]
        metodos = [(mp, n, f"S/ {tot:,.2f}") for mp, n, tot in self.por_metodo()]
        productos = [(p, n, f"S/ {tot:,.2f}") for p, n, tot in self.por_producto()[:10]]

        html = f"""
        <html><body style="font-family: Arial; font-size: 9pt;">
            <h2 style="margin-bottom: 0;">SUMAQ ÑAN RESTAURANTE — Reporte de ventas</h2>
            <p>Del {dia(inicio)} al {dia(fin)} · Generado el {datetime.now():%d/%m/%Y %H:%M}</p>
            {tabla(["Comprobante", "Fecha / Hora", "Cliente", "Mesa", "Pago", "Usuario", "Total"], ventas, derecha=(6,))}
            <h3>Total recaudado: S/ {self.total():,.2f} ({len(self.ventas)} ventas)</h3>
            <h3>Por método de pago</h3>
            {tabla(["Método de pago", "Ventas", "Total"], metodos, derecha=(1, 2))}
            <h3>Productos más vendidos</h3>
            {tabla(["Producto", "Cantidad", "Total"], productos, derecha=(1, 2))}
        </body></html>
        """

        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(ruta)
            printer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A4))
            printer.setPageMargins(QtCore.QMarginsF(12, 12, 12, 12), QtGui.QPageLayout.Unit.Millimeter)
            documento = QtGui.QTextDocument()
            documento.setHtml(html)
            getattr(documento, "print")(printer)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo generar el PDF: {e}")
            return
        self.abrir(ruta)
