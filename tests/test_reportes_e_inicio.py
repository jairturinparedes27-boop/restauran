import pytest
from PyQt6 import QtWidgets
from PyQt6.QtCore import QDate


@pytest.fixture
def con_ventas(panel, vender, bd):
    vender("MESA 01", [("Inca Kola", 2), ("Choclo con Queso", 1)], "Yape")   # 13.00
    vender("MESA 02", [("Churrasco (200g aprox.)", 1)], "Tarjeta")          # 18.00
    # Una venta de otro día, que no debe aparecer en el reporte de hoy
    bd.x("UPDATE ventas SET fecha = '2026-01-15 20:00:00' WHERE mesa = 'MESA 02'")
    return panel


@pytest.fixture
def guardar_en(monkeypatch, tmp_path):
    """Responde al diálogo 'Guardar como' con un archivo dentro de la carpeta de la prueba."""
    def responder(nombre):
        ruta = tmp_path / nombre
        monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName",
                            staticmethod(lambda *args, **kwargs: (str(ruta), "")))
        return ruta
    return responder


def test_reporte_de_hoy(con_ventas):
    ui = con_ventas.ui
    con_ventas.gestion_reportes.filtrar()
    assert ui.tableReporte.rowCount() == 1
    assert [ui.tableReporte.item(0, c).text() for c in (0, 3, 4, 5)] == ["B001-00000001", "MESA 01", "admin", "S/. 13.00"]
    assert ui.txtTotalR.text() == "13.00"


def test_reporte_de_un_rango_de_fechas(con_ventas):
    ui = con_ventas.ui
    ui.dtInicioR.setDate(QDate(2026, 1, 1))
    ui.btnFiltrarR.click()
    assert ui.tableReporte.rowCount() == 2
    assert ui.txtTotalR.text() == "31.00"


def test_fecha_inicio_posterior_a_fecha_fin(con_ventas, avisos):
    ui = con_ventas.ui
    avisos_antes = len(avisos)
    ui.dtInicioR.setDate(QDate.currentDate().addDays(1))
    # Mientras se eligen fechas no salen ventanas; el mensaje queda en la tabla
    assert len(avisos) == avisos_antes
    assert "posterior" in ui.tableReporte.item(0, 0).text()
    ui.btnFiltrarR.click()
    assert avisos[-1][1] == "Fechas inválidas"


def test_sin_ventas_la_tabla_lo_explica(panel):
    ui = panel.ui
    panel.gestion_reportes.filtrar()
    assert ui.tableReporte.rowCount() == 1
    assert ui.tableReporte.item(0, 0).text().startswith("No hay ventas registradas el ")
    assert ui.txtTotalR.text() == "0.00"
    assert ui.lblResumenR.text() == ""


def test_cambiar_una_fecha_actualiza_el_reporte(con_ventas):
    ui = con_ventas.ui
    ui.dtInicioR.setDate(QDate(2026, 1, 1))  # sin pulsar Filtrar
    assert ui.tableReporte.rowCount() == 2
    assert ui.txtTotalR.text() == "31.00"
    assert ui.lblResumenR.text() == "2 ventas · ticket promedio S/ 15.50"


def test_doble_clic_muestra_el_detalle_de_la_venta(con_ventas):
    ui = con_ventas.ui
    con_ventas.gestion_reportes.filtrar()
    ui.tableReporte.cellDoubleClicked.emit(0, 0)

    dialogo = con_ventas.gestion_reportes.dialogo_detalle
    assert dialogo.isVisible() and dialogo.windowTitle() == "Venta B001-00000001"
    tabla = dialogo.findChild(QtWidgets.QTableWidget)
    platos = sorted((tabla.item(r, 0).text(), tabla.item(r, 1).text()) for r in range(tabla.rowCount()))
    assert platos == [("Choclo con Queso", "1"), ("Inca Kola", "2")]
    dialogo.close()


def test_exportar_excel(con_ventas, guardar_en):
    openpyxl = pytest.importorskip("openpyxl")
    ruta = guardar_en("reporte.xlsx")
    con_ventas.ui.dtInicioR.setDate(QDate(2026, 1, 1))
    con_ventas.ui.btnFiltrarR.click()
    con_ventas.ui.btnExcelR.click()

    libro = openpyxl.load_workbook(ruta)
    assert libro.sheetnames == ["Ventas", "Productos", "Métodos de pago"]
    filas = [fila for fila in libro["Ventas"].iter_rows(min_row=5, values_only=True) if any(fila)]
    assert filas[-1][0] == "Total recaudado" and filas[-1][8] == 31.0
    assert len(filas) == 3  # dos ventas y el total
    productos = list(libro["Productos"].iter_rows(min_row=5, values_only=True))
    assert productos[0] == ("Churrasco (200g aprox.)", 1, 18.0)


def test_exportar_pdf(con_ventas, guardar_en):
    ruta = guardar_en("reporte.pdf")
    con_ventas.ui.btnFiltrarR.click()
    con_ventas.ui.btnPdfR.click()
    assert ruta.read_bytes().startswith(b"%PDF")


def test_exportar_sin_ventas_avisa(panel, guardar_en, avisos):
    ruta = guardar_en("vacio.xlsx")
    panel.gestion_reportes.filtrar()
    panel.ui.btnExcelR.click()
    assert avisos[-1][1] == "Sin datos"
    assert not ruta.exists()


def test_inicio_muestra_datos_reales(con_ventas, bd):
    ui = con_ventas.ui
    bd.x("UPDATE productos SET stock = 3 WHERE codigo = 'P12'")
    con_ventas.gestor_pedidos.seleccionar_mesa("MESA 06")  # mesa abierta sin cobrar
    con_ventas.gestion_inicio.actualizar()

    assert ui.lblVentasInicio.text() == "S/. 13.00"            # solo las ventas de hoy
    assert ui.lblMesasInicio.text() == "1 pedido hoy"
    assert ui.lblPlatosInicio.text() == "16 disponibles"
    # P12 más los 3 insumos de ejemplo que empiezan bajo su mínimo
    assert ui.lblStockInicio.text() == "4 alertas"
    codigos = [ui.tableStockInicio.item(r, 0).text() for r in range(ui.tableStockInicio.rowCount())]
    assert codigos == ["P12", "I03", "I08", "I11"]

    estados = [ui.tablePedidosInicio.item(r, 4).text() for r in range(ui.tablePedidosInicio.rowCount())]
    assert estados == ["En curso", "Pagado", "Pagado"]


def test_accesos_rapidos_de_inicio(panel):
    ui = panel.ui
    ui.btnReportesInicio.click()
    assert ui.StackedWidget.currentWidget() is ui.pageReportes
    ui.btnNuevoInicio.click()
    assert ui.StackedWidget.currentWidget() is ui.pagePedido
