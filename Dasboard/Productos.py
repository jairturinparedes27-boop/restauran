import math
from PyQt6 import QtWidgets
from database import GestorBaseDatos

class GestionProductos:
    def __init__(self, ui_dashboard):
        self.ui = ui_dashboard
        self.db = GestorBaseDatos()
        
        # Referencia a la tabla de productos (soportando ambos nombres posibles)
        self.tabla = getattr(self.ui, "tablaProductos", getattr(self.ui, "tableProductos", None))
        
        if self.tabla:
            self.tabla.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.tabla.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.tabla.cellClicked.connect(self.seleccionar_producto)
        
        # Conexiones de botones del módulo productos
        if hasattr(self.ui, "btnGuardarPRO"): 
            self.ui.btnGuardarPRO.clicked.connect(self.guardar_producto)
        if hasattr(self.ui, "btnEditarPRO"): 
            self.ui.btnEditarPRO.clicked.connect(self.modificar_producto)
        if hasattr(self.ui, "btnEliminarPRO"): 
            self.ui.btnEliminarPRO.clicked.connect(self.eliminar_producto)
        if hasattr(self.ui, "btnNuevoPRO"): 
            self.ui.btnNuevoPRO.clicked.connect(self.limpiar_campos)
        if hasattr(self.ui, "btnCategoriaPRO"):
            self.ui.btnCategoriaPRO.clicked.connect(self.abrir_ventana_categorias)
            
        # Recarga automática en tiempo real cada vez que haces clic en el ComboBox
        cmb = getattr(self.ui, "cmbCategoriaPRO", None)
        if cmb:
            original_focus = cmb.focusInEvent
            def nuevo_focus(event):
                self.cargar_categorias_combo()
                if original_focus:
                    original_focus(event)
            cmb.focusInEvent = nuevo_focus

        # Vinculamos el botón de menú lateral de productos para forzar la recarga al hacer clic en él
        if hasattr(self.ui, "btnProductos"):
            try:
                self.ui.btnProductos.clicked.connect(self.actualizar_vista_productos)
            except Exception:
                pass

        # Cargas iniciales
        self.cargar_categorias_combo()
        self.cargar_productos()

    def actualizar_vista_productos(self):
        """Método que se ejecuta al presionar el botón del menú 'Productos' para traer los datos frescos de la BD"""
        self.cargar_categorias_combo()
        self.cargar_productos()

    def cargar_categorias_combo(self):
        """Consulta la BD y recarga el ComboBox forzando la actualización visual inmediata"""
        if not hasattr(self.ui, "cmbCategoriaPRO"):
            return

        cmb = self.ui.cmbCategoriaPRO
        id_actual = cmb.currentData()

        cmb.hidePopup()
        cmb.clear()
        cmb.addItem("Seleccione una categoría...", None)
        
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT id, nombre_categoria FROM categorias")
                registros = cursor.fetchall()
                
                for cat_id, cat_nombre in registros:
                    cmb.addItem(str(cat_nombre), cat_id)
                    
            if id_actual is not None:
                index = cmb.findData(id_actual)
                if index >= 0:
                    cmb.setCurrentIndex(index)
            
            cmb.view().repaint()
            cmb.repaint()
            QtWidgets.QApplication.processEvents()
                    
        except Exception as e:
            print(f"Error al cargar categorías en el ComboBox: {e}")

    def abrir_ventana_categorias(self):
        """Abre la ventana de categorías y le asigna una función de retorno al cerrar"""
        try:
            from Dasboard.Categoria import VentanaCategorias
            self.ventana_categorias = VentanaCategorias()
            self.ventana_categorias.callback_actualizar = self.cargar_categorias_combo
            self.ventana_categorias.show()
        except Exception as e:
            print(f"Error al abrir la ventana de categorías: {e}")

    def cargar_productos(self):
        """Carga los productos haciendo JOIN con la tabla categorias y leyendo el stock real"""
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    SELECT p.id, p.codigo, p.nombre, c.nombre_categoria, p.precio_compra, p.precio_venta, p.stock, p.id_categoria
                    FROM productos p
                    LEFT JOIN categorias c ON p.id_categoria = c.id
                """)
                registros = cursor.fetchall()

            if self.tabla:
                self.tabla.setColumnCount(6)
                self.tabla.setHorizontalHeaderLabels(["Código", "Nombre", "Categoría", "P. Compra", "P. Venta", "Stock"])
                
                self.tabla.setRowCount(0)
                for row_idx, row_data in enumerate(registros):
                    self.tabla.insertRow(row_idx)
                    
                    db_id = row_data[0]
                    codigo = row_data[1]
                    nombre = row_data[2]
                    categoria = row_data[3] or "Sin categoría"
                    p_compra = row_data[4] or 0.0
                    p_venta = row_data[5] or 0.0
                    stock = row_data[6] if row_data[6] is not None else 0
                    id_cat = row_data[7]
                    
                    item_cod = QtWidgets.QTableWidgetItem(str(codigo))
                    item_cod.setData(100, db_id)
                    item_cod.setData(101, id_cat)
                    
                    self.tabla.setItem(row_idx, 0, item_cod)
                    self.tabla.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(nombre)))
                    self.tabla.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(str(categoria)))
                    self.tabla.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(f"S/. {p_compra:.2f}"))
                    self.tabla.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(f"S/. {p_venta:.2f}"))
                    self.tabla.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(str(stock)))
        except Exception as e:
            print(f"Error al cargar productos: {e}")

    def leer_valores_numericos(self):
        """Lee precios y stock del formulario (acepta coma o punto decimal).
        Devuelve (precio_compra, precio_venta, stock), o None tras avisar si algún valor es inválido."""
        def numero(campo, tipo):
            try:
                valor = tipo(campo.text().strip().replace(",", "."))
            except ValueError:
                return None
            return valor if math.isfinite(valor) else None

        precio_compra = numero(self.ui.txtPrecioCompraPRO, float)
        precio_venta = numero(self.ui.txtPrecioVentaPRO, float)
        stock = numero(self.ui.txtStockPRO, int)

        if precio_compra is None or precio_compra < 0:
            error = "El precio de compra debe ser un número mayor o igual a 0 (ej. 12.50 o 12,50)."
        elif precio_venta is None or precio_venta <= 0:
            error = "El precio de venta debe ser un número mayor que 0 (ej. 18.00 o 18,00)."
        elif stock is None or stock < 0:
            error = "El stock debe ser un número entero mayor o igual a 0."
        else:
            return precio_compra, precio_venta, stock

        QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Valor inválido", error)
        return None

    def guardar_producto(self):
        """Registra un nuevo producto vinculándolo con el ID de la categoría seleccionada"""
        codigo = self.ui.txtCodigoPRO.text().strip() if hasattr(self.ui, "txtCodigoPRO") else ""
        nombre = self.ui.txtNombrePRO.text().strip() if hasattr(self.ui, "txtNombrePRO") else ""
        
        cmb = getattr(self.ui, "cmbCategoriaPRO", None)
        id_categoria = cmb.currentData() if cmb else None
        
        if not codigo or not nombre or not id_categoria:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "Complete el código y el nombre, y seleccione una categoría.")
            return

        valores = self.leer_valores_numericos()
        if valores is None:
            return
        precio_compra, precio_venta, stock = valores

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    INSERT INTO productos (codigo, nombre, id_categoria, precio_compra, precio_venta, stock)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (codigo, nombre, id_categoria, precio_compra, precio_venta, stock))
                conexion.commit()

            QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Producto registrado correctamente.")
            self.cargar_productos()
            self.limpiar_campos()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo registrar (El código ya existe): {e}")

    def seleccionar_producto(self, row, column):
        """Carga los datos del producto seleccionado en el formulario y selecciona su categoría"""
        try:
            if not self.tabla:
                return
            
            item_cod = self.tabla.item(row, 0)
            db_id = item_cod.data(100)
            id_cat = item_cod.data(101)
            
            if hasattr(self.ui, "txtCodigoPRO"):
                self.ui.txtCodigoPRO.setText(item_cod.text())
            if hasattr(self.ui, "txtNombrePRO"):
                self.ui.txtNombrePRO.setText(self.tabla.item(row, 1).text())
                
            cmb = getattr(self.ui, "cmbCategoriaPRO", None)
            if cmb and id_cat:
                index = cmb.findData(id_cat)
                if index >= 0:
                    cmb.setCurrentIndex(index)
            
            p_compra = self.tabla.item(row, 3).text().replace("S/. ", "").strip()
            p_venta = self.tabla.item(row, 4).text().replace("S/. ", "").strip()
            stock = self.tabla.item(row, 5).text()
            
            if hasattr(self.ui, "txtPrecioCompraPRO"):
                self.ui.txtPrecioCompraPRO.setText(p_compra)
            if hasattr(self.ui, "txtPrecioVentaPRO"):
                self.ui.txtPrecioVentaPRO.setText(p_venta)
            if hasattr(self.ui, "txtStockPRO"):
                self.ui.txtStockPRO.setText(stock)
            
            self.tabla.setProperty("id_seleccionado", db_id)
        except Exception as e:
            print(f"Error al seleccionar producto: {e}")

    def modificar_producto(self):
        """Actualiza el producto seleccionado"""
        if not self.tabla:
            return
            
        db_id = self.tabla.property("id_seleccionado")
        codigo = self.ui.txtCodigoPRO.text().strip() if hasattr(self.ui, "txtCodigoPRO") else ""
        nombre = self.ui.txtNombrePRO.text().strip() if hasattr(self.ui, "txtNombrePRO") else ""
        
        cmb = getattr(self.ui, "cmbCategoriaPRO", None)
        id_categoria = cmb.currentData() if cmb else None
        
        if not db_id or not codigo or not nombre or not id_categoria:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "Seleccione un producto y verifique los campos.")
            return

        valores = self.leer_valores_numericos()
        if valores is None:
            return
        precio_compra, precio_venta, stock = valores

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    UPDATE productos 
                    SET codigo = ?, nombre = ?, id_categoria = ?, precio_compra = ?, precio_venta = ?, stock = ?
                    WHERE id = ?
                """, (codigo, nombre, id_categoria, precio_compra, precio_venta, stock, db_id))
                conexion.commit()

            QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Producto actualizado correctamente.")
            self.cargar_productos()
            self.limpiar_campos()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo actualizar: {e}")

    def eliminar_producto(self):
        """Elimina el producto seleccionado"""
        if not self.tabla:
            return
            
        db_id = self.tabla.property("id_seleccionado")
        if not db_id:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "Seleccione un producto de la tabla.")
            return

        confirmar = QtWidgets.QMessageBox.question(
            self.ui.centralwidget, "Confirmar", "¿Desea eliminar este producto?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )

        if confirmar == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                with self.db.conectar() as conexion:
                    cursor = conexion.cursor()
                    cursor.execute("DELETE FROM productos WHERE id = ?", (db_id,))
                    conexion.commit()

                QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", "Producto eliminado.")
                self.cargar_productos()
                self.limpiar_campos()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo eliminar: {e}")

    def limpiar_campos(self):
        """Limpia los campos del formulario de productos"""
        if hasattr(self.ui, "txtCodigoPRO"): self.ui.txtCodigoPRO.clear()
        if hasattr(self.ui, "txtNombrePRO"): self.ui.txtNombrePRO.clear()
        if hasattr(self.ui, "txtPrecioCompraPRO"): self.ui.txtPrecioCompraPRO.clear()
        if hasattr(self.ui, "txtPrecioVentaPRO"): self.ui.txtPrecioVentaPRO.clear()
        if hasattr(self.ui, "txtStockPRO"): self.ui.txtStockPRO.clear()
        
        cmb = getattr(self.ui, "cmbCategoriaPRO", None)
        if cmb: cmb.setCurrentIndex(0)
        
        if self.tabla: self.tabla.setProperty("id_seleccionado", None)