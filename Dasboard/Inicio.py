from datetime import date, datetime
from PyQt6 import QtWidgets
from database import GestorBaseDatos

# Un producto con esta cantidad o menos aparece en "Stock crítico"
STOCK_CRITICO = 10
ULTIMAS_VENTAS = 10


def cantidad(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


class GestionInicio:
    """Página de Inicio: resumen del día con datos reales de la base de datos."""

    def __init__(self, ui_dashboard):
        self.ui = ui_dashboard
        self.db = GestorBaseDatos()

        for tabla in (self.ui.tablePedidosInicio, self.ui.tableStockInicio):
            tabla.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            tabla.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        # La pestaña muestra productos (que hoy son los que llevan stock) e insumos
        self.ui.tableStockInicio.setHorizontalHeaderLabels(
            ["Código", "Producto / Insumo", "Categoría", "Stock actual", "Unidad"])
        self.ui.tablePedidosInicio.setHorizontalHeaderLabels(["Nro. Pedido", "Mesa", "Hora", "Total", "Estado"])
        self.ui.tabWidget.setCurrentWidget(self.ui.tabUltimosPedidos)

        # Accesos rápidos
        for boton, pagina in [(self.ui.btnNuevoInicio, self.ui.pagePedido),
                              (self.ui.btnMenuInicio, self.ui.pageProductos),
                              (self.ui.btnInsumosInicio, self.ui.pageInsumos),
                              (self.ui.btnReportesInicio, self.ui.pageReportes)]:
            boton.clicked.connect(lambda _=False, p=pagina: self.ui.StackedWidget.setCurrentWidget(p))

        # Datos frescos cada vez que se entra a Inicio
        self.ui.StackedWidget.currentChanged.connect(self.al_cambiar_pagina)
        self.actualizar()

    def al_cambiar_pagina(self, _indice):
        if self.ui.StackedWidget.currentWidget() is self.ui.pageInicio:
            self.actualizar()

    def actualizar(self):
        hoy = date.today().isoformat()
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    SELECT COUNT(*), COALESCE(SUM(total), 0) FROM ventas
                    WHERE fecha BETWEEN ? AND ?
                """, (f"{hoy} 00:00:00", f"{hoy} 23:59:59"))
                pedidos_hoy, ventas_hoy = cursor.fetchone()

                cursor.execute("SELECT COUNT(*) FROM productos WHERE COALESCE(stock, 0) > 0")
                disponibles = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT p.codigo, p.nombre, COALESCE(c.nombre_categoria, '-'), COALESCE(p.stock, 0), 'unid.'
                    FROM productos p LEFT JOIN categorias c ON p.id_categoria = c.id
                    WHERE COALESCE(p.stock, 0) <= ?
                    ORDER BY COALESCE(p.stock, 0), p.codigo
                """, (STOCK_CRITICO,))
                criticos = cursor.fetchall()
                cursor.execute("""
                    SELECT COALESCE(codigo, id), nombre, COALESCE(categoria, '-'), stock_actual, unidad_medida
                    FROM insumos WHERE stock_actual <= stock_minimo
                    ORDER BY codigo
                """)
                criticos += cursor.fetchall()

                # Mesas abiertas primero, luego las últimas ventas cobradas
                cursor.execute("SELECT mesa, hora, total FROM pedidos WHERE estado != 'PAGADO' ORDER BY id DESC")
                abiertos = cursor.fetchall()
                cursor.execute("SELECT serie, numero, mesa, fecha, total FROM ventas ORDER BY id DESC LIMIT ?",
                               (ULTIMAS_VENTAS,))
                cobrados = cursor.fetchall()
        except Exception as e:
            print(f"Error al cargar el resumen de Inicio: {e}")
            return

        self.ui.lblVentasInicio.setText(f"S/. {ventas_hoy:,.2f}")
        self.ui.lblMesasInicio.setText(cantidad(pedidos_hoy, "pedido hoy", "pedidos hoy"))
        self.ui.lblPlatosInicio.setText(cantidad(disponibles, "disponible", "disponibles"))
        self.ui.lblStockInicio.setText(cantidad(len(criticos), "alerta", "alertas") if criticos else "Sin alertas")

        filas = [("—", mesa, hora[:5], total, "En curso") for mesa, hora, total in abiertos]
        filas += [(f"{serie}-{numero:08d}", mesa, datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M"),
                   total, "Pagado") for serie, numero, mesa, fecha, total in cobrados]
        self.llenar(self.ui.tablePedidosInicio,
                    [(nro, mesa, hora, f"S/. {total:.2f}", estado) for nro, mesa, hora, total, estado in filas])
        self.llenar(self.ui.tableStockInicio,
                    [(codigo, nombre, categoria, f"{stock:g}", unidad)
                     for codigo, nombre, categoria, stock, unidad in criticos])

    @staticmethod
    def llenar(tabla, filas):
        tabla.setRowCount(0)
        for i, fila in enumerate(filas):
            tabla.insertRow(i)
            for j, valor in enumerate(fila):
                tabla.setItem(i, j, QtWidgets.QTableWidgetItem(str(valor)))
