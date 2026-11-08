from PyQt6 import QtWidgets
from database import GestorBaseDatos
from datetime import datetime

class GestionEmpleados:
    def __init__(self, ui_dashboard):
        self.ui = ui_dashboard
        self.db = GestorBaseDatos()

        # Bloquear edición directa en la tabla (Solo selección)
        self.ui.tableEmpleados.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.tableEmpleados.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        
        # 1. Configurar ComboBox
        self.configurar_comboboxes()
        
        # 2. Conectar botones
        self.ui.btnGuardarEmp.clicked.connect(self.agregar_empleado)
        self.ui.btnEditarEmp.clicked.connect(self.modificar_empleado)
        self.ui.btnEliminarEmp.clicked.connect(self.eliminar_empleado)
        self.ui.btnNuevoEmp.clicked.connect(self.limpiar_campos)
        
        # 3. Detectar cuando el usuario hace clic en una fila de la tabla
        self.ui.tableEmpleados.cellClicked.connect(self.seleccionar_empleado)
        
        # 4. Cargar datos en la tabla al iniciar
        self.cargar_empleados()

    def configurar_comboboxes(self):
        self.ui.cmbCargoEmp.clear()
        self.ui.cmbCargoEmp.addItems(["Seleccionar cargo...", "Administrador", "Cajero", "Mozo", "Personal de limpieza"])
        
        self.ui.cmbEstadoEmp.clear()
        self.ui.cmbEstadoEmp.addItems(["Seleccionar estado...", "Activo", "Inactivo"])
        
        # Configurar fecha actual por defecto si el componente dtIngresoEmp existe
        if hasattr(self.ui, "dtIngresoEmp"):
            from PyQt6.QtCore import QDate
            self.ui.dtIngresoEmp.setDate(QDate.currentDate())

    def cargar_empleados(self):
        """Carga y muestra los empleados ocultando el ID real de la BD en la primera celda"""
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT id, dni, nombres, apellidos, telefono, cargo, fecha, estado FROM empleados")
                registros = cursor.fetchall()

            self.ui.tableEmpleados.setColumnCount(7)
            self.ui.tableEmpleados.setHorizontalHeaderLabels(["DNI", "Nombres", "Apellidos", "Teléfono", "Cargo", "Fecha", "Estado"])
            
            self.ui.tableEmpleados.setRowCount(0)
            for row_idx, row_data in enumerate(registros):
                self.ui.tableEmpleados.insertRow(row_idx)
                
                db_id = row_data[0]
                db_dni = str(row_data[1] or "")
                
                # Columna 0: DNI (Guardamos el ID real de la BD de forma interna)
                item_dni = QtWidgets.QTableWidgetItem(db_dni)
                item_dni.setData(100, db_id)
                self.ui.tableEmpleados.setItem(row_idx, 0, item_dni)
                
                # Demás columnas
                self.ui.tableEmpleados.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(row_data[2] or "")))
                self.ui.tableEmpleados.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(str(row_data[3] or "")))
                self.ui.tableEmpleados.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(str(row_data[4] or "")))
                self.ui.tableEmpleados.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(str(row_data[5] or "")))
                self.ui.tableEmpleados.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(str(row_data[6] or "")))
                self.ui.tableEmpleados.setItem(row_idx, 6, QtWidgets.QTableWidgetItem(str(row_data[7] or "")))
                
        except Exception as e:
            print(f"Error al cargar empleados: {e}")

    def agregar_empleado(self):
        dni = self.ui.txtDniEmp.text().strip()
        nombres = self.ui.txtNombreEmp.text().strip()
        apellidos = self.ui.txtApellidosEmp.text().strip()
        telefono = self.ui.txtTelefonoEmp.text().strip()
        cargo = self.ui.cmbCargoEmp.currentText()
        
        if hasattr(self.ui, "dtIngresoEmp"):
            fecha = self.ui.dtIngresoEmp.date().toString("yyyy-MM-dd")
        else:
            fecha = datetime.now().strftime("%Y-%m-%d")
            
        estado = self.ui.cmbEstadoEmp.currentText()

        if not dni or not nombres or not apellidos:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Campos vacíos", "DNI, Nombres y Apellidos son obligatorios.")
            return
            
        if cargo == "Seleccionar cargo...":
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Cargo inválido", "Por favor selecciona un cargo válido.")
            return

        if estado == "Seleccionar estado...":
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Estado inválido", "Por favor selecciona si sigue trabajando (Activo/Inactivo).")
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    INSERT INTO empleados (dni, nombres, apellidos, telefono, cargo, fecha, estado)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (dni, nombres, apellidos, telefono, cargo, fecha, estado))
                conexion.commit()

            QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Empleado registrado correctamente.")
            self.cargar_empleados()
            self.limpiar_campos()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo registrar (DNI duplicado o error de BD): {e}")

    def seleccionar_empleado(self, row, column):
        """Pasa los datos de la fila seleccionada usando el ID oculto de la BD"""
        try:
            db_id = self.ui.tableEmpleados.item(row, 0).data(100)
            
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT dni, nombres, apellidos, telefono, cargo, fecha, estado FROM empleados WHERE id = ?", (db_id,))
                res = cursor.fetchone()

            if res:
                self.ui.txtDniEmp.setText(str(res[0] or ""))
                self.ui.txtNombreEmp.setText(str(res[1] or ""))
                self.ui.txtApellidosEmp.setText(str(res[2] or ""))
                self.ui.txtTelefonoEmp.setText(str(res[3] or ""))
                
                # Seleccionar cargo en el ComboBox
                cargo = str(res[4] or "")
                index_cargo = self.ui.cmbCargoEmp.findText(cargo)
                if index_cargo >= 0:
                    self.ui.cmbCargoEmp.setCurrentIndex(index_cargo)
                    
                # Seleccionar fecha en el QDateEdit
                if hasattr(self.ui, "dtIngresoEmp") and res[5]:
                    from PyQt6.QtCore import QDate
                    self.ui.dtIngresoEmp.setDate(QDate.fromString(str(res[5]), "yyyy-MM-dd"))
                
                # Seleccionar estado en el ComboBox
                estado = str(res[6] or "")
                index_estado = self.ui.cmbEstadoEmp.findText(estado)
                if index_estado >= 0:
                    self.ui.cmbEstadoEmp.setCurrentIndex(index_estado)

            # Guardamos temporalmente el ID seleccionado para editar o eliminar de forma segura
            self.ui.tableEmpleados.setProperty("id_seleccionado", db_id)
        except Exception as e:
            print(f"Error al seleccionar empleado: {e}")

    def modificar_empleado(self):
        """Actualiza los datos del empleado seleccionado usando su ID interno"""
        db_id = self.ui.tableEmpleados.property("id_seleccionado")
        if not db_id:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "Seleccione un empleado de la tabla para modificar.")
            return

        dni = self.ui.txtDniEmp.text().strip()
        nombres = self.ui.txtNombreEmp.text().strip()
        apellidos = self.ui.txtApellidosEmp.text().strip()
        telefono = self.ui.txtTelefonoEmp.text().strip()
        cargo = self.ui.cmbCargoEmp.currentText()
        
        if hasattr(self.ui, "dtIngresoEmp"):
            fecha = self.ui.dtIngresoEmp.date().toString("yyyy-MM-dd")
        else:
            fecha = datetime.now().strftime("%Y-%m-%d")
            
        estado = self.ui.cmbEstadoEmp.currentText()

        if not dni or not nombres or not apellidos:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Campos vacíos", "DNI, Nombres y Apellidos son obligatorios.")
            return

        if cargo == "Seleccionar cargo...":
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Cargo inválido", "Por favor selecciona un cargo válido.")
            return

        if estado == "Seleccionar estado...":
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Estado inválido", "Por favor selecciona si sigue trabajando (Activo/Inactivo).")
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    UPDATE empleados
                    SET dni = ?, nombres = ?, apellidos = ?, telefono = ?, cargo = ?, fecha = ?, estado = ?
                    WHERE id = ?
                """, (dni, nombres, apellidos, telefono, cargo, fecha, estado, db_id))
                conexion.commit()

            QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Empleado actualizado correctamente.")
            self.cargar_empleados()
            self.limpiar_campos()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo actualizar: {e}")

    def eliminar_empleado(self):
        """Elimina al empleado seleccionado basándose en su ID interno"""
        db_id = self.ui.tableEmpleados.property("id_seleccionado")

        if not db_id:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "Seleccione de la tabla el empleado que deseas eliminar.")
            return

        confirmacion = QtWidgets.QMessageBox.question(
            self.ui.centralwidget, 
            "Confirmar eliminación", 
            "¿Estás seguro de eliminar al empleado seleccionado?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )

        if confirmacion == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                with self.db.conectar() as conexion:
                    cursor = conexion.cursor()
                    cursor.execute("DELETE FROM empleados WHERE id = ?", (db_id,))
                    conexion.commit()

                QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Empleado eliminado correctamente.")
                self.cargar_empleados()
                self.limpiar_campos()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo eliminar: {e}")

    def limpiar_campos(self):
        """Limpia todos los campos del formulario y reinicia los ComboBox"""
        self.ui.txtDniEmp.clear()
        self.ui.txtNombreEmp.clear()
        self.ui.txtApellidosEmp.clear()
        self.ui.txtTelefonoEmp.clear()
        self.ui.cmbCargoEmp.setCurrentIndex(0)
        self.ui.cmbEstadoEmp.setCurrentIndex(0)
        if hasattr(self.ui, "dtIngresoEmp"):
            from PyQt6.QtCore import QDate
            self.ui.dtIngresoEmp.setDate(QDate.currentDate())
        if self.ui.tableEmpleados:
            self.ui.tableEmpleados.setProperty("id_seleccionado", None)