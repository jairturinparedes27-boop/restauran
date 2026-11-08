from PyQt6 import QtWidgets
from database import GestorBaseDatos

class GestionUsuarios:
    def __init__(self, ui_dashboard):
        self.ui = ui_dashboard
        self.db = GestorBaseDatos()
        
        self.configurar_comboboxes()
        
        self.ui.txtContrasenaU.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.ui.txtNombreU.setReadOnly(True)
        self.ui.txtApellidoU.setReadOnly(True)
        self.ui.txtCargoU.setReadOnly(True)
        
        # 💡 Bloquear la edición directa en la tabla (Solo selección)
        self.ui.tableUsuario.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.tableUsuario.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        
        self.ui.btnGuardarU.clicked.connect(self.guardar_usuario)
        self.ui.btnEditarU.clicked.connect(self.modificar_usuario)
        self.ui.btnEliminarU.clicked.connect(self.eliminar_usuario)
        self.ui.btnNuevoU.clicked.connect(self.limpiar_campos)
        self.ui.btnBuscarU.clicked.connect(self.buscar_empleado_por_dni)
        
        self.ui.tableUsuario.cellClicked.connect(self.seleccionar_usuario)
        
        self.cargar_usuarios()

    def configurar_comboboxes(self):
        self.ui.cmbEstadoU.clear()
        self.ui.cmbEstadoU.addItems(["Seleccionar estado...", "Activo", "Inactivo"])

    def buscar_empleado_por_dni(self):
        dni = self.ui.txtDniU.text().strip()
        if not dni:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "Ingrese un DNI para buscar.")
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT nombres, apellidos, cargo FROM empleados WHERE dni = ?", (dni,))
                resultado = cursor.fetchone()

            if resultado:
                self.ui.txtNombreU.setText(resultado[0])
                self.ui.txtApellidoU.setText(resultado[1])
                self.ui.txtCargoU.setText(resultado[2])
            else:
                QtWidgets.QMessageBox.warning(self.ui.centralwidget, "No encontrado", "No existe un empleado registrado con ese DNI.")
                self.limpiar_campos_empleado()
        except Exception as e:
            print(f"Error al buscar empleado: {e}")

    def cargar_usuarios(self):
        """Carga la tabla directamente desde DNI, ocultando el ID real en los datos internos"""
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                # Consultamos: id, dni, usuario, contrasena, rol, estado
                cursor.execute("SELECT id, dni, usuario, contrasena, rol, estado FROM usuarios")
                registros = cursor.fetchall()

            self.ui.tableUsuario.setRowCount(0)
            for row_idx, row_data in enumerate(registros):
                self.ui.tableUsuario.insertRow(row_idx)
                
                db_id = row_data[0]
                db_dni = row_data[1] if row_data[1] is not None else ""
                db_usuario = row_data[2] if row_data[2] is not None else ""
                db_contrasena = row_data[3] if row_data[3] is not None else ""
                db_rol = row_data[4] if row_data[4] is not None else ""
                db_estado = row_data[5] if row_data[5] is not None else ""
                
                pass_enmascarada = "*" * len(str(db_contrasena))
                
                # Columna 0: DNI
                item_dni = QtWidgets.QTableWidgetItem(str(db_dni))
                # Guardamos el ID real de la base de datos de manera oculta en esta celda
                item_dni.setData(100, db_id)
                self.ui.tableUsuario.setItem(row_idx, 0, item_dni)
                
                # Columna 1: Usuario
                self.ui.tableUsuario.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(db_usuario)))
                
                # Columna 2: Contraseña (enmascarada)
                self.ui.tableUsuario.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(pass_enmascarada))
                
                # Columna 3: Cargo / Rol
                self.ui.tableUsuario.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(str(db_rol)))
                
                # Columna 4: Estado
                self.ui.tableUsuario.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(str(db_estado)))

        except Exception as e:
            print(f"Error al cargar usuarios: {e}")

    def seleccionar_usuario(self, row, column):
        """Recupera los datos al hacer clic usando el ID oculto en la primera columna"""
        try:
            # Obtenemos el ID real guardado de forma interna en la columna 0 (DNI)
            id_usu = self.ui.tableUsuario.item(row, 0).data(100)
            
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT dni, usuario, contrasena, rol, estado FROM usuarios WHERE id = ?", (id_usu,))
                res = cursor.fetchone()

            if res:
                self.ui.txtDniU.setText(str(res[0] or ""))
                self.buscar_empleado_por_dni() # Autocompleta nombres, apellidos y cargo
                
                self.ui.txtUsuarioU.setText(str(res[1] or ""))
                self.ui.txtContrasenaU.setText(str(res[2] or ""))
                
                index_estado = self.ui.cmbEstadoU.findText(str(res[4] or ""))
                if index_estado >= 0:
                    self.ui.cmbEstadoU.setCurrentIndex(index_estado)
        except Exception as e:
            print(f"Error al seleccionar usuario: {e}")

    def guardar_usuario(self):
        dni = self.ui.txtDniU.text().strip()
        usuario = self.ui.txtUsuarioU.text().strip()
        contrasena = self.ui.txtContrasenaU.text().strip()
        rol = self.ui.txtCargoU.text().strip() # Usamos el cargo autocompletado como rol
        estado = self.ui.cmbEstadoU.currentText()

        if not dni or not usuario or not contrasena:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Campos vacíos", "DNI, Usuario y Contraseña son obligatorios.")
            return

        if estado == "Seleccionar estado...":
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Estado inválido", "Seleccione un estado válido.")
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    INSERT INTO usuarios (dni, usuario, contrasena, rol, estado)
                    VALUES (?, ?, ?, ?, ?)
                """, (dni, usuario, contrasena, rol, estado))
                conexion.commit()

            QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Usuario registrado correctamente.")
            self.cargar_usuarios()
            self.limpiar_campos()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo registrar el usuario: {e}")

    def seleccionar_usuario(self, row, column):
        try:
            id_usu = self.ui.tableUsuario.item(row, 0).data(100)
            
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT dni, usuario, contrasena, rol, estado FROM usuarios WHERE id = ?", (id_usu,))
                res = cursor.fetchone()

            if res:
                self.ui.txtDniU.setText(res[0])
                self.buscar_empleado_por_dni() # Esto llena automáticamente nombres, apellidos y txtCargoU
                
                self.ui.txtUsuarioU.setText(res[1])
                self.ui.txtContrasenaU.setText(res[2])
                
                index_estado = self.ui.cmbEstadoU.findText(res[4])
                if index_estado >= 0:
                    self.ui.cmbEstadoU.setCurrentIndex(index_estado)
        except Exception as e:
            print(f"Error al seleccionar usuario: {e}")

    def modificar_usuario(self):
        dni = self.ui.txtDniU.text().strip()
        usuario = self.ui.txtUsuarioU.text().strip()
        contrasena = self.ui.txtContrasenaU.text().strip()
        rol = self.ui.txtCargoU.text().strip()
        estado = self.ui.cmbEstadoU.currentText()

        if not dni or not usuario:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "Faltan datos obligatorios para modificar.")
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    UPDATE usuarios 
                    SET usuario = ?, contrasena = ?, rol = ?, estado = ?
                    WHERE dni = ?
                """, (usuario, contrasena, rol, estado, dni))
                conexion.commit()

            QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Usuario modificado correctamente.")
            self.cargar_usuarios()
            self.limpiar_campos()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo modificar: {e}")

    def eliminar_usuario(self):
        dni = self.ui.txtDniU.text().strip()
        if not dni:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "Seleccione un usuario de la tabla para eliminar.")
            return

        confirmacion = QtWidgets.QMessageBox.question(
            self.ui.centralwidget, "Confirmar", 
            f"¿Desea eliminar el usuario con DNI {dni}?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )

        if confirmacion == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                with self.db.conectar() as conexion:
                    cursor = conexion.cursor()
                    cursor.execute("DELETE FROM usuarios WHERE dni = ?", (dni,))
                    conexion.commit()

                QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Usuario eliminado.")
                self.cargar_usuarios()
                self.limpiar_campos()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo eliminar: {e}")

    def limpiar_campos(self):
        self.ui.txtDniU.clear()
        self.ui.txtNombreU.clear()
        self.ui.txtApellidoU.clear()
        self.ui.txtUsuarioU.clear()
        self.ui.txtContrasenaU.clear()
        self.ui.txtCargoU.clear()
        self.ui.cmbEstadoU.setCurrentIndex(0)

    def limpiar_campos_empleado(self):
        self.ui.txtNombreU.clear()
        self.ui.txtApellidoU.clear()
        self.ui.txtCargoU.clear()