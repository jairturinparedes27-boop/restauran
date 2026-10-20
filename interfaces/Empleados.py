from PyQt6 import QtWidgets
from database import GestorBaseDatos
from datetime import datetime

class GestionEmpleados:
    def __init__(self, ui_dashboard):
        self.ui = ui_dashboard
        self.db = GestorBaseDatos()

        self.ui.tableEmpleados.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.tableEmpleados.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        
        #  Configurar ComboBox
        self.configurar_comboboxes()
        
        #  Conectar botones
        self.ui.btnGuardarEmp.clicked.connect(self.agregar_empleado)
        self.ui.btnEditarEmp.clicked.connect(self.modificar_empleado)
        self.ui.btnEliminarEmp.clicked.connect(self.eliminar_empleado)
        self.ui.btnNuevoEmp.clicked.connect(self.limpiar_campos)
        
        #  Detectar cuando el usuario hace clic en una fila de la tabla
        self.ui.tableEmpleados.cellClicked.connect(self.seleccionar_empleado)
        
        # Cargar datos en la tabla al iniciar
        self.cargar_empleados()

    def configurar_comboboxes(self):
        self.ui.cmbCargoEmp.clear()
        self.ui.cmbCargoEmp.addItems(["Seleccionar cargo...", "Administrador", "Cajero", "Mozo"])
        
        self.ui.cmbEstadoEmp.clear()
        self.ui.cmbEstadoEmp.addItems(["Seleccionar estado...", "Activo", "Inactivo"])

    def cargar_empleados(self):
        """Carga y muestra los empleados respetando el orden: Dni, Nombres, Apellidos, Telefono, Cargo, Fecha, Estado"""
        try:
            conexion = self.db.conectar()
            cursor = conexion.cursor()
            cursor.execute("SELECT dni, nombres, apellidos, telefono, cargo, fecha, estado FROM empleados")
            registros = cursor.fetchall()
            conexion.close()

            self.ui.tableEmpleados.setRowCount(0)
            for row_idx, row_data in enumerate(registros):
                self.ui.tableEmpleados.insertRow(row_idx)
                for col_idx, data in enumerate(row_data):
                    self.ui.tableEmpleados.setItem(row_idx, col_idx, QtWidgets.QTableWidgetItem(str(data)))
        except Exception as e:
            print(f"Error al cargar empleados: {e}")

    def agregar_empleado(self):
        dni = self.ui.txtDniEmp.text().strip()
        nombres = self.ui.txtNombreEmp.text().strip()
        apellidos = self.ui.txtApellidosEmp.text().strip()
        telefono = self.ui.txtTelefonoEmp.text().strip()
        cargo = self.ui.cmbCargoEmp.currentText()
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
            conexion = self.db.conectar()
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO empleados (dni, nombres, apellidos, telefono, cargo, fecha, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (dni, nombres, apellidos, telefono, cargo, fecha, estado))
            conexion.commit()
            conexion.close()

            QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Empleado registrado correctamente.")
            self.cargar_empleados()
            self.limpiar_campos()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo registrar (DNI duplicado o error de BD): {e}")

    def seleccionar_empleado(self, row, column):
        """Pasa los datos de la fila seleccionada en la tabla hacia los campos del formulario"""
        self.ui.txtDniEmp.setText(self.ui.tableEmpleados.item(row, 0).text())
        self.ui.txtNombreEmp.setText(self.ui.tableEmpleados.item(row, 1).text())
        self.ui.txtApellidosEmp.setText(self.ui.tableEmpleados.item(row, 2).text())
        self.ui.txtTelefonoEmp.setText(self.ui.tableEmpleados.item(row, 3).text())
        
        # Seleccionar el cargo en el ComboBox
        cargo = self.ui.tableEmpleados.item(row, 4).text()
        index_cargo = self.ui.cmbCargoEmp.findText(cargo)
        if index_cargo >= 0:
            self.ui.cmbCargoEmp.setCurrentIndex(index_cargo)
            
        # Seleccionar el estado en el ComboBox
        estado = self.ui.tableEmpleados.item(row, 6).text()
        index_estado = self.ui.cmbEstadoEmp.findText(estado)
        if index_estado >= 0:
            self.ui.cmbEstadoEmp.setCurrentIndex(index_estado)

    def modificar_empleado(self):
        """Actualiza los datos del empleado utilizando el DNI como referencia"""
        dni = self.ui.txtDniEmp.text().strip()
        nombres = self.ui.txtNombreEmp.text().strip()
        apellidos = self.ui.txtApellidosEmp.text().strip()
        telefono = self.ui.txtTelefonoEmp.text().strip()
        cargo = self.ui.cmbCargoEmp.currentText()
        estado = self.ui.cmbEstadoEmp.currentText()

        if not dni:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "Selecciona o ingresa el DNI del empleado a modificar.")
            return

        try:
            conexion = self.db.conectar()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE empleados 
                SET nombres = ?, apellidos = ?, telefono = ?, cargo = ?, estado = ?
                WHERE dni = ?
            """, (nombres, apellidos, telefono, cargo, estado, dni))
            conexion.commit()
            conexion.close()

            QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Empleado actualizado correctamente.")
            self.cargar_empleados()
            self.limpiar_campos()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo actualizar: {e}")

    def eliminar_empleado(self):
        """Elimina al empleado seleccionado basándose en su DNI"""
        dni = self.ui.txtDniEmp.text().strip()

        if not dni:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "Selecciona de la tabla el empleado que deseas eliminar.")
            return

        # Cuadro de confirmación antes de borrar
        confirmacion = QtWidgets.QMessageBox.question(
            self.ui.centralwidget, 
            "Confirmar eliminación", 
            f"¿Estás seguro de eliminar al empleado con DNI {dni}?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )

        if confirmacion == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                conexion = self.db.conectar()
                cursor = conexion.cursor()
                cursor.execute("DELETE FROM empleados WHERE dni = ?", (dni,))
                conexion.commit()
                conexion.close()

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