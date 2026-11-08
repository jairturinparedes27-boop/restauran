"""Configuración común de las pruebas.

Cada prueba corre en una carpeta temporal con su propia restaurante.db, así que nunca
toca la base de datos real. La interfaz se crea sin mostrarse (plataforma 'offscreen')
y los mensajes emergentes se registran en lugar de abrirse.

Ejecutar desde la raíz del proyecto:  python -m pytest
"""
import os
import sqlite3
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6 import QtWidgets  # noqa: E402


class BD:
    """Acceso directo a la restaurante.db de la prueba, para preparar y comprobar datos."""

    def __init__(self, ruta):
        self.ruta = ruta

    def q(self, sql, parametros=()):
        conexion = sqlite3.connect(self.ruta)
        try:
            return conexion.execute(sql, parametros).fetchall()
        finally:
            conexion.close()

    def x(self, sql, parametros=()):
        conexion = sqlite3.connect(self.ruta)
        try:
            conexion.execute(sql, parametros)
            conexion.commit()
        finally:
            conexion.close()


@pytest.fixture(scope="session")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def avisos(monkeypatch):
    """Lista de (tipo, título, texto) de cada QMessageBox; las preguntas se responden Sí."""
    registro = []

    def falso(tipo):
        def mostrar(parent, titulo, texto, *args, **kwargs):
            registro.append((tipo, titulo, texto))
            return QtWidgets.QMessageBox.StandardButton.Yes
        return staticmethod(mostrar)

    for tipo in ("warning", "information", "critical", "question"):
        monkeypatch.setattr(QtWidgets.QMessageBox, tipo, falso(tipo))
    return registro


@pytest.fixture
def bd(tmp_path, monkeypatch, qapp):
    monkeypatch.chdir(tmp_path)
    # Los PDF se generan, pero no se abren en pantalla
    monkeypatch.setattr(os, "startfile", lambda *args, **kwargs: None, raising=False)
    return BD(tmp_path / "restaurante.db")


@pytest.fixture
def login(bd, avisos):
    """login(usuario, contraseña) -> ventana del panel, o None si no pudo entrar."""
    import main

    def ingresar(usuario, contrasena):
        ventana = main.VentanaLogin()
        ventana.ui.txtUsuario.setText(usuario)
        ventana.ui.txtContrasena.setText(contrasena)
        ventana.ui.btnIngresar.click()
        return getattr(ventana, "dashboard", None)
    return ingresar


@pytest.fixture
def panel(bd, avisos):
    """Panel principal abierto como el usuario 'admin'."""
    import main
    return main.VentanaDashboard("Administrador", "Prueba", "admin")


@pytest.fixture
def vender(panel):
    """vender(mesa, [(plato, cantidad), ...], metodo) -> registra una venta desde la interfaz."""
    ui = panel.ui
    pedidos = panel.gestor_pedidos

    def abrir_caja(mesa, items):
        pedidos.seleccionar_mesa(mesa)
        for plato, cantidad in items:
            ui.txtBuscar.setText(plato)
            ui.txtCantidad.setText(str(cantidad))
            ui.btnAgregarPedido.click()
        ui.btnCobrar.click()
        return pedidos.gestor_resumen.ventana_caja

    def cobrar(mesa, items, metodo="Yape"):
        caja = abrir_caja(mesa, items)
        caja.ui.cmbMetodo.setCurrentText(metodo)
        caja.ui.btnPagar.click()
        return caja

    cobrar.abrir_caja = abrir_caja
    return cobrar
