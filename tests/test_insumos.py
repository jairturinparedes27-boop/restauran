import pytest

import database


@pytest.fixture
def insumos(panel):
    ui = panel.ui

    def fila(codigo):
        return next(r for r in range(ui.tableInsumos.rowCount()) if ui.tableInsumos.item(r, 0).text() == codigo)

    def seleccionar(codigo):
        panel.gestion_insumos.seleccionar(fila(codigo), 0)

    def llenar(codigo, nombre, categoria, stock, unidad, minimo, precio):
        panel.gestion_insumos.limpiar()
        ui.txtCodigoI.setText(codigo)
        ui.txtNombreI.setText(nombre)
        ui.cmbCategoriaI.setCurrentText(categoria)
        ui.txtStockI.setText(stock)
        if unidad:
            ui.cmbUnidadI.setCurrentText(unidad)
        ui.txtStockMinI.setText(minimo)
        ui.txtPrecioI.setText(precio)

    return ui, fila, seleccionar, llenar


def fondo(ui, fila):
    return ui.tableInsumos.item(fila, 0).background().color().name()


def test_bd_nueva_trae_insumos_y_marca_los_que_estan_bajo_el_minimo(insumos):
    ui, fila, _, _ = insumos
    assert ui.tableInsumos.rowCount() == 12
    assert [fondo(ui, fila(c)) for c in ("I03", "I08", "I11")] == ["#fdedec"] * 3
    assert fondo(ui, fila("I01")) != "#fdedec"
    assert ui.tableInsumos.item(fila("I01"), 6).text() == "S/. 216.00"  # 12 kg x S/ 18.00


def test_registrar_insumo_con_coma_decimal(insumos, bd):
    ui, _, _, llenar = insumos
    llenar("i13", "Limón", "Verduras", "4,5", "kg", "2", "3,20")
    ui.btnGuardarI.click()
    assert bd.q("SELECT codigo, nombre, categoria, stock_actual, unidad_medida, stock_minimo, precio_unitario "
                "FROM insumos WHERE codigo = 'I13'") == [("I13", "Limón", "Verduras", 4.5, "kg", 2.0, 3.2)]
    assert ui.tableInsumos.rowCount() == 13


def test_codigo_repetido(insumos, avisos):
    ui, _, _, llenar = insumos
    llenar("I01", "Otro", "Carnes", "1", "kg", "0", "1")
    ui.btnGuardarI.click()
    assert avisos[-1][1] == "Código repetido"


@pytest.mark.parametrize("campos, aviso", [
    (("I20", "", "Carnes", "1", "kg", "0", "1"), "Campos incompletos"),
    (("I20", "Sal", "", "1", "kg", "0", "1"), "Campos incompletos"),
    (("I20", "Sal", "Abarrotes", "1", "", "0", "1"), "Campos incompletos"),
    (("I20", "Sal", "Abarrotes", "abc", "kg", "0", "1"), "Valor inválido"),
    (("I20", "Sal", "Abarrotes", "1", "kg", "-2", "1"), "Valor inválido"),
    (("I20", "Sal", "Abarrotes", "1", "kg", "0", "-1"), "Valor inválido"),
])
def test_validaciones(insumos, bd, avisos, campos, aviso):
    ui, _, _, llenar = insumos
    llenar(*campos)
    ui.btnGuardarI.click()
    assert avisos[-1][1] == aviso
    assert not bd.q("SELECT 1 FROM insumos WHERE codigo = 'I20'")


def test_editar_y_eliminar(insumos, bd):
    ui, fila, seleccionar, _ = insumos
    seleccionar("I01")
    assert (ui.txtNombreI.text(), ui.cmbCategoriaI.currentText(), ui.txtStockMinI.text(),
            ui.cmbUnidadI.currentText()) == ("Corazón de res", "Carnes", "5", "kg")

    ui.txtStockI.setText("2")
    ui.btnEditarI.click()
    assert bd.q("SELECT stock_actual FROM insumos WHERE codigo = 'I01'") == [(2.0,)]
    assert fondo(ui, fila("I01")) == "#fdedec"  # ahora está bajo su mínimo de 5

    seleccionar("I01")
    ui.btnEliminarI.click()
    assert not bd.q("SELECT 1 FROM insumos WHERE codigo = 'I01'")


def test_editar_sin_seleccionar_avisa(insumos, avisos):
    ui, _, _, _ = insumos
    ui.btnEditarI.click()
    assert avisos[-1][1] == "Aviso"


def test_categoria_nueva_queda_en_la_lista(insumos):
    ui, _, _, llenar = insumos
    llenar("I30", "Langostinos", "Mariscos", "2", "kg", "1", "35")
    ui.btnGuardarI.click()
    assert ui.cmbCategoriaI.findText("Mariscos") >= 0


def test_tabla_insumos_antigua_se_migra(bd, avisos):
    bd.x("""CREATE TABLE insumos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL,
            stock_actual REAL NOT NULL, unidad_medida TEXT NOT NULL, stock_minimo REAL NOT NULL)""")
    bd.x("INSERT INTO insumos (nombre, stock_actual, unidad_medida, stock_minimo) VALUES ('Sal', 3, 'kg', 1)")

    import main
    panel = main.VentanaDashboard("Administrador", "Prueba", "admin")

    columnas = [c[1] for c in bd.q("PRAGMA table_info(insumos)")]
    assert {"codigo", "categoria", "precio_unitario"} <= set(columnas)
    assert panel.ui.tableInsumos.rowCount() == 1  # no se agregan los de ejemplo a una tabla con datos
    assert panel.ui.tableInsumos.item(0, 1).text() == "Sal"
