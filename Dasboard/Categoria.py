from PyQt6 import QtWidgets
from ui_Categoria import Ui_MainWindow
from database import GestorBaseDatos

class VentanaCategorias(QtWidgets.QMainWindow):  # 👈 Hereda de QWidget para solucionar el error de setCentralWidget
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.db = GestorBaseDatos()
        self.id_seleccionado = None

        # Configuración inicial de la tabla
        if hasattr(self.ui, "tableCategoria"):
            self.ui.tableCategoria.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.ui.tableCategoria.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.ui.tableCategoria.cellClicked.connect(self.seleccionar_fila)

        # Conexión de botones
        if hasattr(self.ui, "btnGuardarcat"):
            self.ui.btnGuardarcat.clicked.connect(self.guardar)
        if hasattr(self.ui, "btnEditarcat"):
            self.ui.btnEditarcat.clicked.connect(self.editar)
        if hasattr(self.ui, "btnEliminarcat"):
            self.ui.btnEliminarcat.clicked.connect(self.eliminar)
        if hasattr(self.ui, "btnNuevoCat"):
            self.ui.btnNuevoCat.clicked.connect(self.limpiar)

        self.cargar_tabla()

    def cargar_tabla(self):
        """Carga las categorías de la base de datos a la tabla"""
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT id, nombre_categoria FROM categorias")
                registros = cursor.fetchall()

            if hasattr(self.ui, "tableCategoria"):
                self.ui.tableCategoria.setRowCount(0)
                for row_idx, row_data in enumerate(registros):
                    self.ui.tableCategoria.insertRow(row_idx)
                    self.ui.tableCategoria.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(row_data[0])))
                    self.ui.tableCategoria.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(row_data[1])))
        except Exception as e:
            print(f"Error al cargar tabla de categorías: {e}")

    def closeEvent(self, event):
        """Se ejecuta de manera instantánea al cerrar la ventana de categorías"""
        if hasattr(self, 'callback_actualizar') and self.callback_actualizar:
            self.callback_actualizar()  # Recarga el ComboBox en Productos al instante
        event.accept()

    def guardar(self):
        """Inserta una nueva categoría"""
        nombre = self.ui.txtNombrecat.text().strip() if hasattr(self.ui, "txtNombrecat") else ""
        if not nombre:
            QtWidgets.QMessageBox.warning(self, "Aviso", "El nombre de la categoría es obligatorio.")
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("INSERT INTO categorias (nombre_categoria) VALUES (?)", (nombre,))
                conexion.commit()

            QtWidgets.QMessageBox.information(self, "Éxito", "Categoría registrada correctamente.")
            self.cargar_tabla()
            self.limpiar()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo registrar (Posible duplicado): {e}")

    def seleccionar_fila(self, row, column):
        """Captura los datos de la fila seleccionada"""
        try:
            item_id = self.ui.tableCategoria.item(row, 0)
            item_nombre = self.ui.tableCategoria.item(row, 1)
            if item_id and item_nombre:
                self.id_seleccionado = item_id.text()
                if hasattr(self.ui, "txtNombrecat"):
                    self.ui.txtNombrecat.setText(item_nombre.text())
        except Exception as e:
            print(f"Error al seleccionar: {e}")

    def editar(self):
        """Actualiza la categoría seleccionada"""
        if not self.id_seleccionado:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Seleccione una categoría de la tabla.")
            return

        nombre = self.ui.txtNombrecat.text().strip() if hasattr(self.ui, "txtNombrecat") else ""
        if not nombre:
            QtWidgets.QMessageBox.warning(self, "Aviso", "El campo no puede estar vacío.")
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("UPDATE categorias SET nombre_categoria = ? WHERE id = ?", (nombre, self.id_seleccionado))
                conexion.commit()

            QtWidgets.QMessageBox.information(self, "Éxito", "Categoría actualizada.")
            self.cargar_tabla()
            self.limpiar()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo actualizar: {e}")

    def eliminar(self):
        """Elimina la categoría seleccionada"""
        if not self.id_seleccionado:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Seleccione una categoría para eliminar.")
            return

        confirmar = QtWidgets.QMessageBox.question(
            self, "Confirmar", "¿Desea eliminar esta categoría?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )

        if confirmar == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                with self.db.conectar() as conexion:
                    cursor = conexion.cursor()
                    cursor.execute("DELETE FROM categorias WHERE id = ?", (self.id_seleccionado,))
                    conexion.commit()

                QtWidgets.QMessageBox.information(self, "Éxito", "Categoría eliminada.")
                self.cargar_tabla()
                self.limpiar()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo eliminar: {e}")

    def limpiar(self):
        """Limpia los campos del formulario"""
        if hasattr(self.ui, "txtNombrecat"):
            self.ui.txtNombrecat.clear()
        self.id_seleccionado = None