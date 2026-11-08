import pytest

import database


def test_contrasenas_en_texto_plano_se_convierten_a_hash(bd, login):
    bd.x("""CREATE TABLE usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, dni TEXT, usuario TEXT NOT NULL UNIQUE,
            contrasena TEXT NOT NULL, rol TEXT NOT NULL, estado TEXT)""")
    bd.x("INSERT INTO usuarios (usuario, contrasena, rol, estado) VALUES ('admin', '1234', 'Administrador', 'Activo')")

    database.GestorBaseDatos()

    assert all(database.es_hash(c) for (c,) in bd.q("SELECT contrasena FROM usuarios"))
    assert login("admin", "1234") is not None


def test_login_con_contrasena_correcta_e_incorrecta(login, avisos):
    assert login("admin", "1234") is not None
    assert login("admin", "mala") is None
    assert avisos[-1][1] == "Error de Acceso"


def test_usuario_inactivo_no_entra(bd, login, avisos):
    database.GestorBaseDatos()
    bd.x("UPDATE usuarios SET estado = 'Inactivo' WHERE usuario = 'cajero'")
    assert login("cajero", "1234") is None
    assert avisos[-1][1] == "Usuario inactivo"


def test_rol_sin_acceso_no_entra(bd, login, avisos):
    database.GestorBaseDatos()
    bd.x("INSERT INTO usuarios (usuario, contrasena, rol, estado) VALUES ('limpieza', ?, 'Personal de limpieza', 'Activo')",
         (database.hashear_contrasena("1234"),))
    assert login("limpieza", "1234") is None
    assert avisos[-1][1] == "Sin acceso"


@pytest.mark.parametrize("usuario, visibles", [
    ("mozo", ["btnClientes", "btnPedidos"]),
    ("cajero", ["btnClientes", "btnPedidos", "btnProductos"]),
    ("admin", sorted(["btnInicio", "btnUsuario", "btnEmpleados", "btnClientes",
                      "btnProductos", "btnInsumos", "btnPedidos", "btnReportes"])),
])
def test_cada_rol_ve_solo_sus_modulos(login, usuario, visibles):
    import main
    panel = login(usuario, "1234")
    assert sorted(b for b in main.MODULOS if not getattr(panel.ui, b).isHidden()) == visibles


def test_rol_desconocido_no_ve_ningun_modulo(bd, avisos):
    import main
    panel = main.VentanaDashboard("Rol raro", "x")
    assert all(getattr(panel.ui, b).isHidden() for b in main.MODULOS)
