from PyQt6 import QtWidgets, QtCore
from database import GestorBaseDatos
from datetime import datetime
from Dasboard.Caja import VentanaCaja

class GestionResumen:
    def __init__(self, ui_dashboard, usuario=""):
        self.ui = ui_dashboard
        self.db = GestorBaseDatos()
        self.mesa_actual = ""
        self.usuario = usuario  # quien inició sesión: queda registrado en cada venta

        self.tabla = getattr(self.ui, "tablePedidos", None)
        if self.tabla:
            self.tabla.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.tabla.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            
        if hasattr(self.ui, "btnAgregarPedido"):
            self.ui.btnAgregarPedido.clicked.connect(self.agregar_producto)
        if hasattr(self.ui, "btnQuitar"):
            self.ui.btnQuitar.clicked.connect(self.quitar_producto)
        if hasattr(self.ui, "btnEnviarCocina"):
            self.ui.btnEnviarCocina.clicked.connect(self.guardar_pedido_en_bd)
            
        for btn_nombre in ["btnPreCuenta", "BtnPreCuenta"]:
            btn = getattr(self.ui, btn_nombre, None)
            if btn:
                btn.setText("Cancelar Pedido")
                btn.clicked.connect(self.cancelar_mesa)

        if hasattr(self.ui, "btnCobrar"):
            self.ui.btnCobrar.clicked.connect(self.abrir_ventana_cobro)
            
        self.configurar_buscador()

    def configurar_buscador(self):
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT nombre FROM productos")
                resultados = cursor.fetchall()
                
            nombres_platos = [row[0] for row in resultados]
            campo_buscar = getattr(self.ui, "txtBuscar", None)
            
            if campo_buscar:
                self.completer = QtWidgets.QCompleter(nombres_platos, campo_buscar)
                self.completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
                self.completer.setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
                campo_buscar.setCompleter(self.completer)
        except Exception as e:
            print(f"Error al configurar autocompletado en Resumen: {e}")

    def cargar_pedido_mesa(self, nombre_mesa):
        self.mesa_actual = nombre_mesa
        self.configurar_buscador()
        
        if hasattr(self.ui, 'lblAtender'):
            self.ui.lblAtender.setText(f"Atendiendo: {self.mesa_actual}")
            
        if not self.tabla:
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    SELECT codigo, producto, cantidad, precio_unitario, subtotal, estado 
                    FROM detalle_pedidos 
                    WHERE mesa = ?
                """, (self.mesa_actual,))
                registros = cursor.fetchall()

            self.tabla.setRowCount(0)
            for row_idx, row_data in enumerate(registros):
                self.tabla.insertRow(row_idx)
                
                item_cod = QtWidgets.QTableWidgetItem(str(row_data[0]))
                item_cod.setData(200, row_data[5])
                
                self.tabla.setItem(row_idx, 0, item_cod)
                self.tabla.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(row_data[1])))
                self.tabla.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(str(row_data[2])))
                self.tabla.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(f"S/. {row_data[3]:.2f}"))
                self.tabla.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(f"S/. {row_data[4]:.2f}"))
                
            self.recalcular_total_pantalla()
        except Exception as e:
            print(f"Error al cargar pedido de la mesa: {e}")
            if self.tabla:
                self.tabla.setRowCount(0)
            self.recalcular_total_pantalla()

    def sincronizar_bd_mesa(self):
        """Guarda el estado actual y actualiza la tabla pedidos con el total exacto para que se vea en las tarjetas"""
        if not self.mesa_actual:
            return

        try:
            total_general = 0.0
            items = []
            
            if self.tabla:
                for row in range(self.tabla.rowCount()):
                    codigo = self.tabla.item(row, 0).text()
                    estado_item = self.tabla.item(row, 0).data(200) or 'PENDIENTE'
                    producto = self.tabla.item(row, 1).text()
                    cantidad = int(self.tabla.item(row, 2).text())
                    p_unit = float(self.tabla.item(row, 3).text().replace("S/. ", ""))
                    subtotal = float(self.tabla.item(row, 4).text().replace("S/. ", ""))
                    total_general += subtotal
                    items.append((self.mesa_actual, codigo, producto, cantidad, p_unit, subtotal, estado_item))

            hora_actual = datetime.now().strftime("%H:%M:%S")

            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("DELETE FROM detalle_pedidos WHERE mesa = ?", (self.mesa_actual,))
                cursor.execute("DELETE FROM pedidos WHERE mesa = ? AND estado != 'PAGADO'", (self.mesa_actual,))
                
                if items:
                    cursor.execute("""
                        INSERT INTO pedidos (mesa, hora, total, estado)
                        VALUES (?, ?, ?, 'OCUPADA')
                    """, (self.mesa_actual, hora_actual, total_general))
                    
                    for item in items:
                        cursor.execute("""
                            INSERT INTO detalle_pedidos (mesa, codigo, producto, cantidad, precio_unitario, subtotal, estado)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, item)
                        
                conexion.commit()
                
            self.actualizar_tarjetas_mesas()
            
        except Exception as e:
            print(f"Error al sincronizar BD de la mesa: {e}")

    def actualizar_tarjetas_mesas(self):
        try:
            parent_window = self.ui.centralwidget.window()
            if hasattr(parent_window, "gestor_pedidos"):
                parent_window.gestor_pedidos.actualizar_estado_mesas()
        except Exception as e:
            print(f"No se pudieron actualizar las tarjetas de las mesas: {e}")

    def agregar_producto(self):
        """Agrega un plato, descuenta el stock en la BD de forma inmediata y sincroniza el total de la mesa"""
        nombre_plato = self.ui.txtBuscar.text().strip() if hasattr(self.ui, 'txtBuscar') else ""
        cantidad_str = self.ui.txtCantidad.text().strip() if hasattr(self.ui, 'txtCantidad') else "1"
        
        if not nombre_plato:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "Ingrese o seleccione un plato o bebida.")
            return

        try:
            cantidad = int(cantidad_str) if cantidad_str else 1
        except ValueError:
            cantidad = 0

        if cantidad <= 0:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Cantidad inválida", "La cantidad debe ser un número entero mayor que 0.")
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT codigo, precio_venta, stock FROM productos WHERE nombre = ?", (nombre_plato,))
                producto = cursor.fetchone()
                
            if not producto:
                QtWidgets.QMessageBox.warning(self.ui.centralwidget, "No encontrado", "El producto no existe en la base de datos.")
                return
                
            codigo, precio_unitario, stock_actual = producto[0], float(producto[1]), producto[2]
            
            if stock_actual is None:
                stock_actual = 0

            # Validar stock disponible
            if stock_actual < cantidad:
                QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Stock Insuficiente", f"Solo quedan {stock_actual} unidades disponibles de {nombre_plato}.")
                return

            subtotal = precio_unitario * cantidad

            # 1. Descontar stock directamente en la base de datos con commit seguro
            nuevo_stock = stock_actual - cantidad
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("UPDATE productos SET stock = ? WHERE codigo = ?", (nuevo_stock, codigo))
                conexion.commit()

            if self.tabla:
                row_idx = self.tabla.rowCount()
                self.tabla.insertRow(row_idx)
                
                item_cod = QtWidgets.QTableWidgetItem(str(codigo))
                item_cod.setData(200, 'PENDIENTE')
                
                self.tabla.setItem(row_idx, 0, item_cod)
                self.tabla.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(nombre_plato)))
                self.tabla.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(str(cantidad)))
                self.tabla.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(f"S/. {precio_unitario:.2f}"))
                self.tabla.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(f"S/. {subtotal:.2f}"))
                
                if hasattr(self.ui, 'txtBuscar'): self.ui.txtBuscar.clear()
                if hasattr(self.ui, 'txtCantidad'): self.ui.txtCantidad.clear()
                
                self.recalcular_total_pantalla()
                
                # 2. Sincronizamos para guardar los ítems, actualizar el total de la mesa y refrescar las tarjetas
                self.sincronizar_bd_mesa()
                
        except Exception as e:
            print(f"Error al agregar producto: {e}")

    def quitar_producto(self):
        if not self.tabla:
            return
        fila = self.tabla.currentRow()
        if fila < 0:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "Seleccione un producto de la tabla para quitar.")
            return
            
        item_cod = self.tabla.item(fila, 0)
        estado_item = item_cod.data(200) if item_cod else 'PENDIENTE'
        
        if estado_item == 'ENVIADO':
            QtWidgets.QMessageBox.warning(
                self.ui.centralwidget, 
                "Acción no permitida", 
                "Este plato ya fue enviado a cocina y no se puede eliminar directamente."
            )
            return
            
        codigo = item_cod.text()
        try:
            cantidad_removida = int(self.tabla.item(fila, 2).text())
            
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("UPDATE productos SET stock = stock + ? WHERE codigo = ?", (cantidad_removida, codigo))
                conexion.commit()
        except Exception as e:
            print(f"Error al devolver stock al quitar producto: {e}")
            
        self.tabla.removeRow(fila)
        self.recalcular_total_pantalla()
        self.sincronizar_bd_mesa()

    def recalcular_total_pantalla(self):
        if not self.tabla:
            return
        suma_total = 0.0
        for row in range(self.tabla.rowCount()):
            item_sub = self.tabla.item(row, 4)
            if item_sub:
                try:
                    valor = float(item_sub.text().replace("S/. ", "").strip())
                    suma_total += valor
                except ValueError:
                    pass
                    
        if hasattr(self.ui, 'lblTotal'):
            self.ui.lblTotal.setText(f"TOTAL: S/ {suma_total:.2f}")

    def guardar_pedido_en_bd(self):
        if not self.tabla or self.tabla.rowCount() == 0:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "No hay productos en la comanda para enviar.")
            return

        try:
            for row in range(self.tabla.rowCount()):
                item_cod = self.tabla.item(row, 0)
                if item_cod:
                    item_cod.setData(200, 'ENVIADO')

            self.sincronizar_bd_mesa()
            QtWidgets.QMessageBox.information(self.ui.centralwidget, "Éxito", f"Pedido enviado a cocina para la {self.mesa_actual}.")
            self.cargar_pedido_mesa(self.mesa_actual)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo enviar a cocina: {e}")

    def cancelar_mesa(self):
        if not self.mesa_actual:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "No hay ninguna mesa activa para cancelar.")
            return

        respuesta = QtWidgets.QMessageBox.question(
            self.ui.centralwidget,
            "Confirmar Cancelación",
            f"¿Está seguro de anular y cancelar todo el pedido de la {self.mesa_actual}? Se repondrá el stock y la mesa quedará libre.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )

        if respuesta != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT codigo, cantidad FROM detalle_pedidos WHERE mesa = ?", (self.mesa_actual,))
                items_mesa = cursor.fetchall()
                
                for codigo, cant in items_mesa:
                    cursor.execute("UPDATE productos SET stock = stock + ? WHERE codigo = ?", (cant, codigo))

                cursor.execute("DELETE FROM detalle_pedidos WHERE mesa = ?", (self.mesa_actual,))
                cursor.execute("DELETE FROM pedidos WHERE mesa = ? AND estado != 'PAGADO'", (self.mesa_actual,))
                conexion.commit()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui.centralwidget, "Error", f"No se pudo cancelar el pedido: {e}")
            return

        if self.tabla:
            self.tabla.setRowCount(0)
        self.recalcular_total_pantalla()
        
        mesa_cancelada = self.mesa_actual
        self.mesa_actual = ""

        QtWidgets.QMessageBox.information(
            self.ui.centralwidget,
            "Mesa Cancelada",
            f"El pedido de la {mesa_cancelada} ha sido cancelado correctamente."
        )

        if hasattr(self.ui, "StackedWidget") and hasattr(self.ui, "pagePedido"):
            self.ui.StackedWidget.setCurrentWidget(self.ui.pagePedido)

        self.actualizar_tarjetas_mesas()

    def abrir_ventana_cobro(self):
        total = 0.0
        for row in range(self.tabla.rowCount()):
            sub = self.tabla.item(row, 4).text()
            try:
                total += float(sub.replace("S/. ", ""))
            except ValueError:
                pass
                
        if total <= 0:
            QtWidgets.QMessageBox.warning(self.ui.centralwidget, "Aviso", "La mesa no cuenta con un consumo registrado para cobrar.")
            return
            
        def terminar_cobro_y_volver():
            if self.tabla:
                self.tabla.setRowCount(0)
            self.recalcular_total_pantalla()
            self.mesa_actual = ""
            
            if hasattr(self.ui, "StackedWidget") and hasattr(self.ui, "pagePedido"):
                self.ui.StackedWidget.setCurrentWidget(self.ui.pagePedido)
                
            self.actualizar_tarjetas_mesas()

        self.ventana_caja = VentanaCaja(self.mesa_actual, total, callback_exito=terminar_cobro_y_volver,
                                        usuario=self.usuario)
        self.ventana_caja.show()