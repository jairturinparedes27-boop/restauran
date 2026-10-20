from PyQt6 import QtWidgets
from database import GestorBaseDatos

class GestionClientes:
    def __init__(self, ui_dashboard):
        self.ui = ui_dashboard
        self.db = GestorBaseDatos()
        
        # Asegurar que la tabla de clientes exista 
        self.crear_tabla_clientes_si_no_existe()
        
        # Detectar el nombre de la tabla 
        self.tabla = getattr(self.ui, "tableClientes", getattr(self.ui, "clientes", None))
        
        if self.tabla:
            self.tabla.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.tabla.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.tabla.cellClicked.connect(self.seleccionar_cliente)
        
        # Conexiones de los botones usando tus nombres exactos
        if hasattr(self.ui, "btnGuardarCli"): 
            self.ui.btnGuardarCli.clicked.connect(self.guardar_cliente)
        if hasattr(self.ui, "btnEditarCli"): 
            self.ui.btnEditarCli.clicked.connect(self.modificar_cliente)
        if hasattr(self.ui, "btnEliminarCli"): 
            self.ui.btnEliminarCli.clicked.connect(self.eliminar_cliente)
        if hasattr(self.ui, "btnNuevoCli"): 
            self.ui.btnNuevoCli.clicked.connect(self.limpiar_campos_cliente)
            
        # Carga inicial
        self.cargar_clientes()

    def crear_tabla_clientes_si_no_existe(self):
        """Crea la tabla clientes en SQLite si aún no está creada"""
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS clientes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        documento TEXT UNIQUE,
                        nombre TEXT,
                        telefono TEXT,
                        direccion TEXT
                    )
                """)
                conexion.commit()
        except Exception as e:
            print(f"Error al crear tabla clientes: {e}")

    def cargar_clientes(self):
        """Carga todos los clientes en la tabla de la interfaz"""
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT id, documento, nombre, telefono, direccion FROM clientes")
                registros = cursor.fetchall()

            if self.tabla:
                self.tabla.setColumnCount(4)
                self.tabla.setHorizontalHeaderLabels(["Documento", "Nombre / Razón Social", "Teléfono", "Dirección"])
                
                self.tabla.setRowCount(0)
                for row_idx, row_data in enumerate(registros):
                    self.tabla.insertRow(row_idx)
                    
                    db_id = row_data[0]
                    documento = row_data[1]
                    nombre = row_data[2]
                    telefono = row_data[3]
                    direccion = row_data[4]
                    
                    item_doc = QtWidgets.QTableWidgetItem(str(documento))
                    item_doc.setData(100, db_id) # Guardamos el ID interno de la BD
                    
                    self.tabla.setItem(row_idx, 0, item_doc)
                    self.tabla.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(nombre)))
                    self.tabla.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(str(telefono or "")))
                    self.tabla.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(str(direccion or "")))
        except Exception as e:
            print(f"Error al cargar clientes: {e}")

    def guardar_cliente(self):
        """Registra un nuevo cliente con depuración de errores"""
        documento = self.ui.txtDocumentoCli.text().strip() if hasattr(self.ui, "txtDocumentoCli") else ""
        nombre = self.ui.txtNombreCli.text().strip() if hasattr(self.ui, "txtNombreCli") else ""
        telefono = self.ui.txtRelefonoCli.text().strip() if hasattr(self.ui, "txtRelefonoCli") else ""
        direccion = self.ui.txtDireccionCli.text().strip() if hasattr(self.ui, "txtDireccionCli") else ""

        print(f"[DEBUG CLIENTE] Intentando guardar -> Doc: {documento} | Nombre: {nombre}")

        if not documento or not nombre:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Campos incompletos", "El número de Documento y el Nombre/Razón Social son obligatorios.")
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    INSERT INTO clientes (documento, nombre, telefono, direccion)
                    VALUES (?, ?, ?, ?)
                """, (documento, nombre, telefono, direccion))
                conexion.commit()

            print(" [DEBUG CLIENTE] ¡Guardado exitosamente en la BD!")
            QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Cliente registrado correctamente.")
            self.cargar_clientes()
            self.limpiar_campos_cliente()
        except Exception as e:
            print(f" [ERROR AL GUARDAR CLIENTE]: {e}")
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo registrar: {e}")

    def seleccionar_cliente(self, row, column):
        """Pasa los datos de la fila seleccionada a las cajas de texto"""
        try:
            if not self.tabla:
                return
            
            item_doc = self.tabla.item(row, 0)
            db_id = item_doc.data(100)
            
            if hasattr(self.ui, "txtDocumentoCli"):
                self.ui.txtDocumentoCli.setText(item_doc.text())
            if hasattr(self.ui, "txtNombreCli"):
                self.ui.txtNombreCli.setText(self.tabla.item(row, 1).text())
            if hasattr(self.ui, "txtRelefonoCli"):
                self.ui.txtRelefonoCli.setText(self.tabla.item(row, 2).text())
            if hasattr(self.ui, "txtDireccionCli"):
                self.ui.txtDireccionCli.setText(self.tabla.item(row, 3).text())
            
            self.tabla.setProperty("id_seleccionado", db_id)
        except Exception as e:
            print(f"Error al seleccionar cliente: {e}")

    def modificar_cliente(self):
        """Actualiza los datos del cliente seleccionado"""
        if not self.tabla:
            return
            
        db_id = self.tabla.property("id_seleccionado")
        documento = self.ui.txtDocumentoCli.text().strip() if hasattr(self.ui, "txtDocumentoCli") else ""
        nombre = self.ui.txtNombreCli.text().strip() if hasattr(self.ui, "txtNombreCli") else ""
        telefono = self.ui.txtRelefonoCli.text().strip() if hasattr(self.ui, "txtRelefonoCli") else ""
        direccion = self.ui.txtDireccionCli.text().strip() if hasattr(self.ui, "txtDireccionCli") else ""

        if not db_id or not documento or not nombre:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "Seleccione un cliente de la tabla para modificar.")
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    UPDATE clientes 
                    SET documento = ?, nombre = ?, telefono = ?, direccion = ?
                    WHERE id = ?
                """, (documento, nombre, telefono, direccion, db_id))
                conexion.commit()

            QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Cliente actualizado correctamente.")
            self.cargar_clientes()
            self.limpiar_campos_cliente()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo actualizar: {e}")

    def eliminar_cliente(self):
        """Elimina el cliente seleccionado"""
        if not self.tabla:
            return
            
        db_id = self.tabla.property("id_seleccionado")
        if not db_id:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "Seleccione un cliente de la tabla para eliminar.")
            return

        confirmacion = QtWidgets.QMessageBox.question(
            self.ui.centralwidget, "Confirmar", "¿Desea eliminar este cliente?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )

        if confirmacion == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                with self.db.conectar() as conexion:
                    cursor = conexion.cursor()
                    cursor.execute("DELETE FROM clientes WHERE id = ?", (db_id,))
                    conexion.commit()

                QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Cliente eliminado.")
                self.cargar_clientes()
                self.limpiar_campos_cliente()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo eliminar: {e}")

    def limpiar_campos_cliente(self):
        """Limpia las cajas de texto y quita la selección"""
        if hasattr(self.ui, "txtDocumentoCli"): self.ui.txtDocumentoCli.clear()
        if hasattr(self.ui, "txtNombreCli"): self.ui.txtNombreCli.clear()
        if hasattr(self.ui, "txtRelefonoCli"): self.ui.txtRelefonoCli.clear()
        if hasattr(self.ui, "txtDireccionCli"): self.ui.txtDireccionCli.clear()
        if self.tabla: self.tabla.setProperty("id_seleccionado", None)