import pytest


def test_el_telefono_del_cliente_se_guarda_y_se_conserva_al_editar(panel, bd):
    ui = panel.ui
    ui.txtDocumentoCli.setText("99999999")
    ui.txtNombreCli.setText("Cliente Prueba")
    ui.txtTelefonoCli.setText("987111222")
    ui.btnGuardarCli.click()
    assert bd.q("SELECT telefono FROM clientes WHERE documento = '99999999'") == [("987111222",)]

    fila = next(r for r in range(ui.tableClientes.rowCount()) if ui.tableClientes.item(r, 0).text() == "99999999")
    panel.gestion_clientes.seleccionar_cliente(fila, 0)
    assert ui.txtTelefonoCli.text() == "987111222"

    ui.txtDireccionCli.setText("Calle 2")
    ui.btnEditarCli.click()
    assert bd.q("SELECT telefono, direccion FROM clientes WHERE documento = '99999999'") == [("987111222", "Calle 2")]


@pytest.mark.parametrize("cantidad", ["-5", "0", "abc", "2.5"])
def test_cantidad_invalida_en_la_comanda_se_rechaza(panel, bd, avisos, cantidad):
    panel.gestor_pedidos.seleccionar_mesa("MESA 03")
    panel.ui.txtBuscar.setText("Inca Kola")
    panel.ui.txtCantidad.setText(cantidad)
    panel.ui.btnAgregarPedido.click()
    assert avisos[-1][1] == "Cantidad inválida"
    assert bd.q("SELECT stock FROM productos WHERE nombre = 'Inca Kola'") == [(100,)]
    assert panel.ui.tablePedidos.rowCount() == 0


@pytest.mark.parametrize("cantidad, stock", [("", 99), ("3", 97)])
def test_cantidad_valida_descuenta_stock(panel, bd, cantidad, stock):
    panel.gestor_pedidos.seleccionar_mesa("MESA 03")
    panel.ui.txtBuscar.setText("Inca Kola")
    panel.ui.txtCantidad.setText(cantidad)
    panel.ui.btnAgregarPedido.click()
    assert bd.q("SELECT stock FROM productos WHERE nombre = 'Inca Kola'") == [(stock,)]


@pytest.mark.parametrize("compra, venta, stock, aceptado", [
    ("12,50", "18,90", "40", True),
    ("abc", "18", "40", False),
    ("10", "0", "40", False),
    ("10", "18", "4.5", False),
    ("-1", "18", "40", False),
])
def test_precios_de_productos(panel, bd, avisos, compra, venta, stock, aceptado):
    ui = panel.ui
    fila = next(r for r in range(ui.tableProductos.rowCount()) if ui.tableProductos.item(r, 0).text() == "P11")
    panel.gestion_productos.seleccionar_producto(fila, 0)
    ui.txtPrecioCompraPRO.setText(compra)
    ui.txtPrecioVentaPRO.setText(venta)
    ui.txtStockPRO.setText(stock)
    ui.btnEditarPRO.click()

    guardado = bd.q("SELECT precio_compra, precio_venta, stock FROM productos WHERE codigo = 'P11'")
    if aceptado:
        assert guardado == [(12.5, 18.9, 40)]
    else:
        assert avisos[-1][1] == "Valor inválido"
        assert guardado == [(10.0, 18.0, 100)]  # sin cambios


def test_editar_empleado_sin_cargo_se_rechaza(panel, avisos):
    panel.gestion_emp.seleccionar_empleado(0, 0)
    panel.ui.cmbCargoEmp.setCurrentIndex(0)
    panel.ui.btnEditarEmp.click()
    assert avisos[-1][1] == "Cargo inválido"
