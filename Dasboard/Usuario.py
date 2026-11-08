from PyQt6 import QtWidgets
from database import GestorBaseDatos, ROLES_CON_ACCESO, hashear_contrasena

ESTADOS = ["Activo", "Inactivo"]


class GestionUsuarios:
    def __init__(self, ui_dashboard):
        self.ui = ui_dashboard
        self.db = GestorBaseDatos()
        self.id_seleccionado = None

        self.configurar_comboboxes()

        self.ui.txtContrasenaU.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.ui.txtNombreU.setReadOnly(True)
        self.ui.txtApellidoU.setReadOnly(True)
        self.ui.txtCargoU.setReadOnly(True)

        # Bloquear la edición directa en la tabla (solo selección)
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
        self.ui.cmbEstadoU.addItems(["Seleccionar estado..."] + ESTADOS)

    def aviso(self, titulo, mensaje):
        QtWidgets.QMessageBox.warning(self.ui.centralwidget, titulo, mensaje)

    def buscar_empleado(self, dni):
        """Devuelve (nombres, apellidos, cargo) del empleado con ese DNI, o None."""
        with self.db.conectar() as conexion:
            cursor = conexion.cursor()
            cursor.execute("SELECT nombres, apellidos, cargo FROM empleados WHERE dni = ?", (dni,))
            return cursor.fetchone()

    def buscar_empleado_por_dni(self):
        dni = self.ui.txtDniU.text().strip()
        if not dni:
            self.aviso("Aviso", "Ingrese un DNI para buscar.")
            return

        try:
            empleado = self.buscar_empleado(dni)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo buscar el empleado: {e}")
            return

        if empleado:
            self.ui.txtNombreU.setText(empleado[0])
            self.ui.txtApellidoU.setText(empleado[1])
            self.ui.txtCargoU.setText(empleado[2])
        else:
            self.aviso("No encontrado", "No existe un empleado registrado con ese DNI.")
            self.limpiar_campos_empleado()

    def obtener_rol(self, dni, rol_actual=None):
        """El rol de un usuario es el cargo de su empleado. Los usuarios sin DNI
        (admin, cajero, mozo) conservan su rol actual. Devuelve None, tras avisar,
        si el rol no da acceso al sistema."""
        if dni:
            empleado = self.buscar_empleado(dni)
            if not empleado:
                self.aviso("No encontrado", f"No existe un empleado registrado con el DNI {dni}.")
                return None
            rol = empleado[2]
        else:
            rol = rol_actual

        if rol not in ROLES_CON_ACCESO:
            self.aviso("Cargo sin acceso",
                       f"El cargo '{rol or 'sin cargo'}' no tiene acceso al sistema. "
                       f"Solo pueden tener usuario: {', '.join(ROLES_CON_ACCESO)}.")
            return None
        return rol

    def es_ultimo_admin_activo(self, id_usuario):
        with self.db.conectar() as conexion:
            cursor = conexion.cursor()
            cursor.execute("SELECT rol, estado FROM usuarios WHERE id = ?", (id_usuario,))
            if cursor.fetchone() != ("Administrador", "Activo"):
                return False
            cursor.execute("""
                SELECT COUNT(*) FROM usuarios
                WHERE rol = 'Administrador' AND estado = 'Activo' AND id != ?
            """, (id_usuario,))
            return cursor.fetchone()[0] == 0

    def cargar_usuarios(self):
        """Carga la tabla mostrando el DNI y guardando el ID real de forma oculta"""
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT id, dni, usuario, rol, estado FROM usuarios")
                registros = cursor.fetchall()

            self.ui.tableUsuario.setRowCount(0)
            for row_idx, (db_id, dni, usuario, rol, estado) in enumerate(registros):
                self.ui.tableUsuario.insertRow(row_idx)

                # Columna 0: DNI, con el ID real de la BD guardado de forma oculta
                item_dni = QtWidgets.QTableWidgetItem(str(dni or ""))
                item_dni.setData(100, db_id)
                self.ui.tableUsuario.setItem(row_idx, 0, item_dni)

                self.ui.tableUsuario.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(usuario or "")))
                # La contraseña se guarda cifrada: nunca se muestra
                self.ui.tableUsuario.setItem(row_idx, 2, QtWidgets.QTableWidgetItem("********"))
                self.ui.tableUsuario.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(str(rol or "")))
                self.ui.tableUsuario.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(str(estado or "")))

        except Exception as e:
            print(f"Error al cargar usuarios: {e}")

    def seleccionar_usuario(self, row, column):
        """Recupera los datos al hacer clic usando el ID oculto en la primera columna"""
        try:
            id_usu = self.ui.tableUsuario.item(row, 0).data(100)
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT dni, usuario, rol, estado FROM usuarios WHERE id = ?", (id_usu,))
                res = cursor.fetchone()
            empleado = self.buscar_empleado(res[0]) if res and res[0] else None
        except Exception as e:
            print(f"Error al seleccionar usuario: {e}")
            return

        if not res:
            return

        dni, usuario, rol, estado = res
        self.id_seleccionado = id_usu

        self.ui.txtDniU.setText(dni or "")
        self.ui.txtUsuarioU.setText(usuario or "")
        self.ui.txtContrasenaU.clear()
        self.ui.txtContrasenaU.setPlaceholderText("(vacío = no cambiarla)")

        if empleado:
            self.ui.txtNombreU.setText(empleado[0])
            self.ui.txtApellidoU.setText(empleado[1])
            self.ui.txtCargoU.setText(empleado[2])
        else:
            self.limpiar_campos_empleado()
            self.ui.txtCargoU.setText(rol or "")

        index_estado = self.ui.cmbEstadoU.findText(estado or "")
        self.ui.cmbEstadoU.setCurrentIndex(max(index_estado, 0))

    def guardar_usuario(self):
        dni = self.ui.txtDniU.text().strip()
        usuario = self.ui.txtUsuarioU.text().strip()
        contrasena = self.ui.txtContrasenaU.text().strip()
        estado = self.ui.cmbEstadoU.currentText()

        if not dni or not usuario or not contrasena:
            self.aviso("Campos vacíos", "DNI, Usuario y Contraseña son obligatorios.")
            return

        if estado not in ESTADOS:
            self.aviso("Estado inválido", "Seleccione un estado válido.")
            return

        try:
            rol = self.obtener_rol(dni)
            if rol is None:
                return

            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    INSERT INTO usuarios (dni, usuario, contrasena, rol, estado)
                    VALUES (?, ?, ?, ?, ?)
                """, (dni, usuario, hashear_contrasena(contrasena), rol, estado))
                conexion.commit()

            QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Usuario registrado correctamente.")
            self.cargar_usuarios()
            self.limpiar_campos()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error",
                                           f"No se pudo registrar el usuario (¿el nombre de usuario ya existe?): {e}")

    def modificar_usuario(self):
        if self.id_seleccionado is None:
            self.aviso("Aviso", "Seleccione un usuario de la tabla para modificar.")
            return

        dni = self.ui.txtDniU.text().strip()
        usuario = self.ui.txtUsuarioU.text().strip()
        contrasena = self.ui.txtContrasenaU.text().strip()
        estado = self.ui.cmbEstadoU.currentText()

        if not usuario:
            self.aviso("Aviso", "El nombre de usuario es obligatorio.")
            return

        if estado not in ESTADOS:
            self.aviso("Estado inválido", "Seleccione un estado válido.")
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT rol FROM usuarios WHERE id = ?", (self.id_seleccionado,))
                fila = cursor.fetchone()
            if not fila:
                self.aviso("Aviso", "El usuario seleccionado ya no existe.")
                self.cargar_usuarios()
                self.limpiar_campos()
                return

            rol = self.obtener_rol(dni, fila[0])
            if rol is None:
                return

            if self.es_ultimo_admin_activo(self.id_seleccionado) and (rol != "Administrador" or estado != "Activo"):
                self.aviso("Acción no permitida",
                           "Este es el último administrador activo: no se puede desactivar ni cambiar su rol.")
                return

            campos = ["dni = ?", "usuario = ?", "rol = ?", "estado = ?"]
            valores = [dni or None, usuario, rol, estado]
            if contrasena:
                campos.append("contrasena = ?")
                valores.append(hashear_contrasena(contrasena))
            valores.append(self.id_seleccionado)

            with self.db.conectar() as conexion:
                conexion.execute(f"UPDATE usuarios SET {', '.join(campos)} WHERE id = ?", valores)
                conexion.commit()

            QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Usuario modificado correctamente.")
            self.cargar_usuarios()
            self.limpiar_campos()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo modificar: {e}")

    def eliminar_usuario(self):
        if self.id_seleccionado is None:
            self.aviso("Aviso", "Seleccione un usuario de la tabla para eliminar.")
            return

        usuario = self.ui.txtUsuarioU.text().strip()
        try:
            if self.es_ultimo_admin_activo(self.id_seleccionado):
                self.aviso("Acción no permitida", "No se puede eliminar al último administrador activo.")
                return
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo verificar el usuario: {e}")
            return

        confirmacion = QtWidgets.QMessageBox.question(
            self.ui.centralwidget, "Confirmar",
            f"¿Desea eliminar el usuario '{usuario}'?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )

        if confirmacion == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                with self.db.conectar() as conexion:
                    conexion.execute("DELETE FROM usuarios WHERE id = ?", (self.id_seleccionado,))
                    conexion.commit()

                QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Usuario eliminado.")
                self.cargar_usuarios()
                self.limpiar_campos()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo eliminar: {e}")

    def limpiar_campos(self):
        self.id_seleccionado = None
        self.ui.txtDniU.clear()
        self.ui.txtUsuarioU.clear()
        self.ui.txtContrasenaU.clear()
        self.ui.txtContrasenaU.setPlaceholderText("")
        self.limpiar_campos_empleado()
        self.ui.cmbEstadoU.setCurrentIndex(0)

    def limpiar_campos_empleado(self):
        self.ui.txtNombreU.clear()
        self.ui.txtApellidoU.clear()
        self.ui.txtCargoU.clear()
