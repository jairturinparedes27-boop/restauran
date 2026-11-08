import os


def test_un_cobro_queda_registrado_con_su_detalle_y_quien_cobro(vender, bd):
    caja = vender.abrir_caja("MESA 02", [("Inca Kola", 2), ("Choclo con Queso", 1)])
    caja.ui.txtPaga.setText("20,00")
    assert caja.ui.txtVuelto.text() == "S/. 7.00"
    caja.ui.btnPagar.click()

    assert bd.q("SELECT serie, numero, tipo_comprobante, metodo_pago, total, monto_recibido, vuelto, mesa, usuario "
                "FROM ventas") == [("B001", 1, "BOLETA", "Efectivo", 13.0, 20.0, 7.0, "MESA 02", "admin")]
    assert bd.q("SELECT producto, cantidad, subtotal FROM detalle_ventas ORDER BY producto") == [
        ("Choclo con Queso", 1, 5.0), ("Inca Kola", 2, 8.0)]
    assert not bd.q("SELECT 1 FROM detalle_pedidos WHERE mesa = 'MESA 02'")
    assert any(nombre.startswith("B001-00000001_") for nombre in os.listdir("boletas"))


def test_numeracion_correlativa_por_serie(vender, bd):
    vender("MESA 01", [("Agua", 1)])

    caja = vender.abrir_caja("MESA 02", [("Agua", 1)])
    caja.ui.rbFactura.setChecked(True)
    assert not caja.ui.txtDNI.isReadOnly()
    caja.ui.txtDNI.setText("20000000001")
    caja.ui.btnBuscar.click()
    assert caja.ui.txtRazon.text() == "Comercial Los Andes S.A.C."
    caja.ui.cmbMetodo.setCurrentText("Yape")
    caja.ui.btnPagar.click()

    vender("MESA 03", [("Agua", 1)], "Tarjeta")

    assert bd.q("SELECT serie, numero, cliente_documento FROM ventas ORDER BY id") == [
        ("B001", 1, "-"), ("F001", 1, "20000000001"), ("B001", 2, "-")]


def test_no_cobra_si_el_pedido_cambio_con_la_caja_abierta(vender, panel, bd, avisos):
    caja = vender.abrir_caja("MESA 04", [("Agua", 1)])
    panel.ui.txtBuscar.setText("Agua")
    panel.ui.txtCantidad.setText("1")
    panel.ui.btnAgregarPedido.click()

    caja.ui.cmbMetodo.setCurrentText("Yape")
    caja.ui.btnPagar.click()

    assert avisos[-1][1] == "Pedido modificado"
    assert bd.q("SELECT COUNT(*) FROM ventas") == [(0,)]


def test_el_comprobante_sale_en_una_sola_pagina_aunque_el_pedido_sea_largo(vender):
    import re
    platos = ["Anticuchos (1 Palito)", "Anticuchos (2 Palitos)", "Anticuchos (3 Palitos)", "Anticuchos (5 Palitos)",
              "Brocheta de Pollo (1 Palito)", "Brocheta de Pollo (2 Palitos)", "Brocheta de Pollo (3 Palitos)",
              "Chorizo (1 Unidad)", "Churrasco (200g aprox.)", "Chancho al Horno (200g aprox.)",
              "Choclo con Queso", "Inca Kola", "Coca-Cola", "Agua"]
    vender("MESA 06", [(plato, 1) for plato in platos])
    pdf = open(os.path.join("boletas", os.listdir("boletas")[0]), "rb").read()
    assert len(re.findall(rb"/Type\s*/Page[^s]", pdf)) == 1


def test_la_misma_caja_no_cobra_dos_veces(vender, bd):
    caja = vender("MESA 05", [("Agua", 1)])
    caja.ui.btnPagar.click()
    assert bd.q("SELECT COUNT(*) FROM ventas") == [(1,)]
