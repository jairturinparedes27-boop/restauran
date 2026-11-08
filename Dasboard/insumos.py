import math
import sqlite3

from PyQt6 import QtWidgets, QtGui
from database import GestorBaseDatos

CATEGORIAS = ["Carnes", "Verduras", "Lácteos", "Condimentos", "Abarrotes", "Bebidas",
              "Descartables", "Limpieza", "Otros"]
UNIDADES = ["kg", "g", "L", "ml", "unidad", "paquete", "caja"]
COLOR_BAJO_MINIMO = QtGui.QColor("#FDEDEC")

# Columnas de tableInsumos
COLUMNAS = ["Código", "Insumo", "Categoría", "Stock actual", "Unidad", "Precio unitario", "Total"]


def numero(texto):
    """Número escrito en un campo (acepta coma o punto decimal), o None si no es válido."""
    try:
        valor = float(texto.strip().replace(",", "."))
    except ValueError:
        return None
    return valor if math.isfinite(valor) else None


class GestionInsumos:
    """Página de Insumos: materia prima del restaurante con su stock y su stock mínimo."""

    def __init__(self, ui_dashboard):
        self.ui = ui_dashboard
        self.db = GestorBaseDatos()
        self.id_seleccionado = None

        tabla = self.ui.tableInsumos
        tabla.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        tabla.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        tabla.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        tabla.setColumnCount(len(COLUMNAS))
        tabla.setHorizontalHeaderLabels(COLUMNAS)
        tabla.cellClicked.connect(self.seleccionar)

        # Categoría: se elige de la lista o se escribe una nueva
        self.ui.cmbCategoriaI.setEditable(True)
        self.ui.cmbCategoriaI.lineEdit().setPlaceholderText("Elija o escriba...")
        self.ui.cmbUnidadI.addItems(UNIDADES)
        self.ui.cmbUnidadI.setPlaceholderText("Seleccione...")
        for campo, ejemplo in [(self.ui.txtStockI, "Ej. 12,5"), (self.ui.txtStockMinI, "Alerta si baja de aquí"),
                               (self.ui.txtPrecioI, "Precio por unidad")]:
            campo.setPlaceholderText(ejemplo)

        self.ui.btnGuardarI.clicked.connect(self.guardar)
        self.ui.btnEditarI.clicked.connect(self.editar)
        self.ui.btnEliminarI.clicked.connect(self.eliminar)
        self.ui.btnNuevoI.clicked.connect(self.limpiar)

        self.cargar()
        self.limpiar()

    def aviso(self, titulo, mensaje):
        QtWidgets.QMessageBox.warning(self.ui.centralwidget, titulo, mensaje)

    # ---------- Lectura ----------

    def cargar(self):
        try:
            with self.db.conectar() as conexion:
                registros = conexion.execute("""
                    SELECT id, COALESCE(codigo, ''), nombre, COALESCE(categoria, ''), stock_actual,
                           unidad_medida, stock_minimo, precio_unitario
                    FROM insumos ORDER BY codigo, nombre
                """).fetchall()
                categorias = [fila[0] for fila in conexion.execute(
                    "SELECT DISTINCT categoria FROM insumos WHERE COALESCE(categoria, '') != ''")]
        except Exception as e:
            print(f"Error al cargar insumos: {e}")
            return

        tabla = self.ui.tableInsumos
        tabla.setRowCount(0)
        for fila, (id_insumo, codigo, nombre, categoria, stock, unidad, minimo, precio) in enumerate(registros):
            tabla.insertRow(fila)
            valores = [codigo, nombre, categoria, f"{stock:g}", unidad, f"S/. {precio:.2f}", f"S/. {stock * precio:.2f}"]
            bajo_minimo = stock <= minimo
            for columna, valor in enumerate(valores):
                item = QtWidgets.QTableWidgetItem(valor)
                if bajo_minimo:
                    item.setBackground(COLOR_BAJO_MINIMO)
                    item.setToolTip(f"Stock bajo el mínimo ({minimo:g} {unidad})")
                tabla.setItem(fila, columna, item)
            tabla.item(fila, 0).setData(100, id_insumo)

        # Las categorías nuevas que se hayan escrito quedan disponibles en la lista
        texto_actual = self.ui.cmbCategoriaI.currentText()
        self.ui.cmbCategoriaI.clear()
        self.ui.cmbCategoriaI.addItems(sorted(set(CATEGORIAS) | set(categorias), key=str.lower))
        self.ui.cmbCategoriaI.setCurrentText(texto_actual)

    def seleccionar(self, fila, _columna):
        id_insumo = self.ui.tableInsumos.item(fila, 0).data(100)
        try:
            with self.db.conectar() as conexion:
                registro = conexion.execute("""
                    SELECT COALESCE(codigo, ''), nombre, COALESCE(categoria, ''), stock_actual, stock_minimo,
                           unidad_medida, precio_unitario
                    FROM insumos WHERE id = ?
                """, (id_insumo,)).fetchone()
        except Exception as e:
            print(f"Error al seleccionar insumo: {e}")
            return
        if not registro:
            return

        codigo, nombre, categoria, stock, minimo, unidad, precio = registro
        self.id_seleccionado = id_insumo
        self.ui.txtCodigoI.setText(codigo)
        self.ui.txtNombreI.setText(nombre)
        self.ui.cmbCategoriaI.setCurrentText(categoria)
        self.ui.txtStockI.setText(f"{stock:g}")
        self.ui.txtStockMinI.setText(f"{minimo:g}")
        if self.ui.cmbUnidadI.findText(unidad) < 0:
            self.ui.cmbUnidadI.addItem(unidad)  # unidad registrada antes que no está en la lista
        self.ui.cmbUnidadI.setCurrentText(unidad)
        self.ui.txtPrecioI.setText(f"{precio:.2f}")

    def leer_formulario(self):
        """Datos del formulario validados, o None tras avisar qué falta o qué está mal."""
        codigo = self.ui.txtCodigoI.text().strip().upper()
        nombre = self.ui.txtNombreI.text().strip()
        categoria = self.ui.cmbCategoriaI.currentText().strip()
        unidad = self.ui.cmbUnidadI.currentText()

        faltan = [campo for campo, valor in [("Código", codigo), ("Nombre", nombre),
                                             ("Categoría", categoria), ("Unidad de medida", unidad)] if not valor]
        if faltan:
            self.aviso("Campos incompletos", "Complete: " + ", ".join(faltan) + ".")
            return None

        stock = numero(self.ui.txtStockI.text())
        minimo = numero(self.ui.txtStockMinI.text() or "0")
        precio = numero(self.ui.txtPrecioI.text())
        for etiqueta, valor in [("El stock actual", stock), ("El stock mínimo", minimo),
                                ("El precio unitario", precio)]:
            if valor is None or valor < 0:
                self.aviso("Valor inválido", f"{etiqueta} debe ser un número mayor o igual a 0 (ej. 12.5 o 12,5).")
                return None

        return codigo, nombre, categoria, stock, unidad, minimo, precio

    # ---------- Escritura ----------

    def guardar(self):
        datos = self.leer_formulario()
        if datos is None:
            return
        try:
            with self.db.conectar() as conexion:
                conexion.execute("""
                    INSERT INTO insumos (codigo, nombre, categoria, stock_actual, unidad_medida, stock_minimo,
                                         precio_unitario)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, datos)
        except sqlite3.IntegrityError:
            self.aviso("Código repetido", f"Ya existe un insumo con el código {datos[0]}.")
            return
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo registrar el insumo: {e}")
            return

        QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Insumo registrado correctamente.")
        self.cargar()
        self.limpiar()

    def editar(self):
        if self.id_seleccionado is None:
            self.aviso("Aviso", "Seleccione un insumo de la tabla para modificar.")
            return
        datos = self.leer_formulario()
        if datos is None:
            return
        try:
            with self.db.conectar() as conexion:
                conexion.execute("""
                    UPDATE insumos SET codigo = ?, nombre = ?, categoria = ?, stock_actual = ?, unidad_medida = ?,
                                       stock_minimo = ?, precio_unitario = ?
                    WHERE id = ?
                """, (*datos, self.id_seleccionado))
        except sqlite3.IntegrityError:
            self.aviso("Código repetido", f"Ya existe otro insumo con el código {datos[0]}.")
            return
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo actualizar el insumo: {e}")
            return

        QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Insumo actualizado correctamente.")
        self.cargar()
        self.limpiar()

    def eliminar(self):
        if self.id_seleccionado is None:
            self.aviso("Aviso", "Seleccione un insumo de la tabla para eliminar.")
            return

        nombre = self.ui.txtNombreI.text().strip()
        respuesta = QtWidgets.QMessageBox.question(
            self.ui.centralwidget, "Confirmar", f"¿Desea eliminar el insumo '{nombre}'?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        if respuesta != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        try:
            with self.db.conectar() as conexion:
                conexion.execute("DELETE FROM insumos WHERE id = ?", (self.id_seleccionado,))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo eliminar el insumo: {e}")
            return

        QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Insumo eliminado.")
        self.cargar()
        self.limpiar()

    def limpiar(self):
        self.id_seleccionado = None
        for campo in (self.ui.txtCodigoI, self.ui.txtNombreI, self.ui.txtStockI, self.ui.txtStockMinI,
                      self.ui.txtPrecioI):
            campo.clear()
        self.ui.cmbCategoriaI.setCurrentIndex(-1)
        self.ui.cmbCategoriaI.clearEditText()
        self.ui.cmbUnidadI.setCurrentIndex(-1)
        self.ui.tableInsumos.clearSelection()
