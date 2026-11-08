import pytest


@pytest.fixture
def usuarios(panel, bd):
    ui, gestion = panel.ui, panel.gestion_usuarios

    def fila(nombre):
        return next(r for r in range(ui.tableUsuario.rowCount()) if ui.tableUsuario.item(r, 1).text() == nombre)

    def seleccionar(nombre):
        gestion.cargar_usuarios()
        gestion.seleccionar_usuario(fila(nombre), 0)

    def crear(dni, usuario):
        gestion.limpiar_campos()
        ui.txtDniU.setText(dni)
        ui.txtUsuarioU.setText(usuario)
        ui.txtContrasenaU.setText("clave")
        ui.cmbEstadoU.setCurrentText("Activo")
        ui.btnGuardarU.click()

    bd.x("INSERT INTO empleados (dni, nombres, apellidos, telefono, cargo, fecha, estado) "
         "VALUES ('11111111', 'Ana', 'Paz', '', 'Personal de limpieza', '2026-11-08', 'Activo')")
    bd.x("INSERT INTO empleados (dni, nombres, apellidos, telefono, cargo, fecha, estado) "
         "VALUES ('22222222', 'Luis', 'Rio', '', 'Mozo', '2026-11-08', 'Activo')")
    return ui, seleccionar, crear


def test_admin_sin_dni_se_puede_editar_y_cambiar_contrasena(usuarios, login, avisos):
    ui, seleccionar, _ = usuarios
    seleccionar("admin")
    assert ui.txtCargoU.text() == "Administrador"
    assert ui.txtContrasenaU.text() == ""  # la contraseña nunca se muestra

    ui.txtContrasenaU.setText("nueva123")
    ui.btnEditarU.click()
    assert avisos[-1][1] == "Éxito"
    assert login("admin", "nueva123") is not None
    assert login("admin", "1234") is None


def test_editar_con_contrasena_vacia_la_conserva(usuarios, login):
    ui, seleccionar, _ = usuarios
    seleccionar("admin")
    ui.btnEditarU.click()
    assert login("admin", "1234") is not None


def test_no_se_crea_usuario_para_un_cargo_sin_acceso(usuarios, bd, avisos):
    _, _, crear = usuarios
    crear("11111111", "apaz")
    assert avisos[-1][1] == "Cargo sin acceso"
    assert not bd.q("SELECT 1 FROM usuarios WHERE usuario = 'apaz'")


def test_el_rol_sale_del_cargo_aunque_no_se_pulse_buscar(usuarios, bd):
    _, _, crear = usuarios
    crear("22222222", "lrio")
    assert bd.q("SELECT rol FROM usuarios WHERE usuario = 'lrio'") == [("Mozo",)]


def test_editar_y_eliminar_afectan_solo_al_usuario_elegido(usuarios, bd):
    ui, seleccionar, crear = usuarios
    crear("22222222", "lrio")
    crear("22222222", "lrio2")

    seleccionar("lrio2")
    ui.cmbEstadoU.setCurrentText("Inactivo")
    ui.btnEditarU.click()
    assert bd.q("SELECT usuario, estado FROM usuarios WHERE dni = '22222222' ORDER BY usuario") == [
        ("lrio", "Activo"), ("lrio2", "Inactivo")]

    seleccionar("lrio2")
    ui.btnEliminarU.click()
    assert bd.q("SELECT usuario FROM usuarios WHERE dni = '22222222'") == [("lrio",)]


def test_el_ultimo_administrador_activo_esta_protegido(usuarios, bd, avisos):
    ui, seleccionar, _ = usuarios
    bd.x("UPDATE usuarios SET estado = 'Inactivo' WHERE rol = 'Administrador' AND usuario != 'admin'")

    seleccionar("admin")
    ui.cmbEstadoU.setCurrentText("Inactivo")
    ui.btnEditarU.click()
    assert avisos[-1][1] == "Acción no permitida"

    seleccionar("admin")
    ui.btnEliminarU.click()
    assert avisos[-1][1] == "Acción no permitida"
    assert bd.q("SELECT estado FROM usuarios WHERE usuario = 'admin'") == [("Activo",)]
