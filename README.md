# Sumaq Ñan — sistema de restaurante

Aplicación de escritorio en Python + PyQt6 con base de datos SQLite: login por roles, mantenimiento de usuarios, empleados, clientes y productos, toma de pedidos por mesa y cobro con boleta o factura en PDF.

## Instalación

```
pip install -r requirements.txt
```

En Anaconda usa `pip install "PyQt6==6.6.1" "PyQt6-Qt6==6.6.1"`: las versiones más nuevas no cargan porque Anaconda trae una versión antigua de las bibliotecas de Visual C++.

## Ejecutar

```
python main.py
```

La primera vez se crea `restaurante.db` con datos de ejemplo. Usuarios iniciales: `admin`, `cajero` y `mozo`, todos con contraseña `1234`. **Cámbialas** desde el módulo Usuarios.

## Desarrollo

```
python dev.py                     # reinicia la app cada vez que guardas un .py o .ui
python dev.py --rol Administrador # entra directo al panel (también Cajero o Mozo)
```

Al guardar un `.ui` en Qt Designer, `dev.py` regenera su `ui_*.py`, salvo que desaparezca algún widget que el código pueda estar usando.

## Pruebas

```
pip install -r requirements-dev.txt
python -m pytest
```

Cada prueba usa una base de datos temporal (nunca toca `restaurante.db`) y la interfaz se crea sin mostrarse. Pasa las pruebas antes de subir cambios.

## Roles

| Rol | Módulos |
|---|---|
| Administrador | Todos |
| Cajero | Clientes, Productos, Pedidos |
| Mozo | Clientes, Pedidos |

Solo estos tres cargos pueden tener usuario. El rol de un usuario es el cargo de su empleado.

## Ventas

Cada cobro se guarda en las tablas `ventas` y `detalle_ventas` con fecha, método de pago, cliente, quién cobró y número correlativo (`B001-00000001` para boletas, `F001-00000001` para facturas). Los PDF se guardan en `boletas/` y `facturas/`.

- **Inicio:** ventas y pedidos del día, platos disponibles, productos con 10 unidades o menos (e insumos bajo su mínimo), mesas abiertas y últimas ventas.
- **Reportes:** ventas entre dos fechas con su total, número de ventas y ticket promedio; se actualiza al cambiar las fechas y con doble clic se ve el detalle de una venta. Se exportan a Excel (hojas de ventas, productos vendidos y métodos de pago) o a PDF; por defecto se guardan en `reportes/`.
- **Insumos:** materia prima con código, categoría, stock actual, stock mínimo, unidad y precio. Los que están en su mínimo o por debajo se marcan en rojo y aparecen como alerta en Inicio.
