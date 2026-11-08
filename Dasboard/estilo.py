from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

Modo = QtWidgets.QHeaderView.ResizeMode


def ajustar_tabla(tabla, columnas_flexibles=None):
    """Oculta los números de fila y reparte el ancho de la tabla: las columnas flexibles
    se reparten el espacio libre y las demás se ajustan a su contenido.
    Sin columnas_flexibles, todas las columnas se reparten el ancho por igual."""
    tabla.verticalHeader().setVisible(False)
    cabecera = tabla.horizontalHeader()
    cabecera.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
    cabecera.setStretchLastSection(False)
    cabecera.setMinimumSectionSize(80)
    for columna in range(tabla.columnCount()):
        if columnas_flexibles is None or columna in columnas_flexibles:
            cabecera.setSectionResizeMode(columna, Modo.Stretch)
        else:
            cabecera.setSectionResizeMode(columna, Modo.ResizeToContents)
