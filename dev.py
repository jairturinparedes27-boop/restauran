"""Lanzador de desarrollo: abre la app y la reinicia cada vez que guardas un .py o un .ui.

Uso:
    py dev.py                      # abre el login normal
    py dev.py --rol Administrador  # salta el login y abre el panel con ese rol
                                   # (Administrador, Cajero o Mozo)

Al guardar un .ui en Qt Designer se regenera su ui_*.py antes de reiniciar,
salvo que eso haga desaparecer widgets que el código podría estar usando:
en ese caso avisa y no sobrescribe nada.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
IGNORAR = {".git", "__pycache__", ".venv", "venv"}

# .ui de Qt Designer -> módulo Python que importa la app
INTERFACES = {
    "Login.ui": "ui_Login.py",
    "Dasboard.ui": "ui_Dasboard.py",
    "Caja.ui": "ui_caja.py",
    "Categoria.ui": "ui_Categoria.py",
}


def log(mensaje):
    print(f"[dev {time.strftime('%H:%M:%S')}] {mensaje}", flush=True)


def instantanea():
    """Fecha de modificación de cada .py y .ui del proyecto."""
    estado = {}
    for ruta in RAIZ.rglob("*"):
        if ruta.suffix not in (".py", ".ui") or ruta.name == "dev.py":
            continue
        if IGNORAR.intersection(ruta.relative_to(RAIZ).parts):
            continue
        try:
            estado[ruta] = ruta.stat().st_mtime_ns
        except FileNotFoundError:
            pass
    return estado


def widgets(codigo):
    return set(re.findall(r"^\s+self\.(\w+) = ", codigo, re.M))


def regenerar_ui(ui):
    destino = RAIZ / INTERFACES[ui.name]
    anterior = destino.read_text(encoding="utf-8") if destino.exists() else ""

    with tempfile.TemporaryDirectory() as tmp:
        salida = Path(tmp) / destino.name
        comando = [sys.executable, "-m", "PyQt6.uic.pyuic", str(ui), "-o", str(salida)]
        if 'if __name__ == "__main__":' in anterior:
            comando.append("-x")  # conserva el bloque ejecutable que ya tenía el archivo
        res = subprocess.run(comando, capture_output=True, text=True)
        if res.returncode != 0:
            log(f"error al convertir {ui.name}:\n{res.stderr}")
            return

        faltan = widgets(anterior) - widgets(salida.read_text(encoding="utf-8"))
        if faltan:
            log(f"NO regeneré {destino.name}: desaparecerían estos widgets, "
                f"que el código puede estar usando: {', '.join(sorted(faltan))}")
            log(f"si el cambio es intencional, actualiza el código y ejecuta: "
                f"py -m PyQt6.uic.pyuic {ui.name} -o {destino.name}")
            return

        shutil.copyfile(salida, destino)
        log(f"{ui.name} -> {destino.name} regenerado")


def comando_app(rol):
    if not rol:
        return [sys.executable, "main.py"]
    codigo = (
        "import sys; from PyQt6 import QtWidgets; import main; "
        "app = QtWidgets.QApplication(sys.argv); "
        f"v = main.VentanaDashboard({rol!r}, 'Modo desarrollo'); v.show(); "
        "sys.exit(app.exec())"
    )
    return [sys.executable, "-c", codigo]


def main():
    parser = argparse.ArgumentParser(description="Ejecuta la app y la reinicia al guardar cambios.")
    parser.add_argument("--rol", choices=["Administrador", "Cajero", "Mozo"],
                        help="abre directamente el panel con este rol, sin pasar por el login")
    args = parser.parse_args()

    # Sin .pyc nuevos: __pycache__ está versionado en git.
    # UTF-8: si la salida no es una consola, los print() con emojis del código
    # lanzan UnicodeEncodeError y PyQt6 cierra la app.
    entorno = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1",
                   PYTHONIOENCODING="utf-8")
    proceso = None

    def iniciar():
        nonlocal proceso
        log("abriendo la app..." + (f" (rol: {args.rol})" if args.rol else ""))
        proceso = subprocess.Popen(comando_app(args.rol), cwd=RAIZ, env=entorno)

    def detener():
        if proceso and proceso.poll() is None:
            proceso.terminate()
            try:
                proceso.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proceso.kill()

    estado = instantanea()
    log(f"vigilando {len(estado)} archivos .py/.ui (Ctrl+C para salir)")
    iniciar()
    avisado = False
    try:
        while True:
            time.sleep(0.5)

            if proceso.poll() is not None and not avisado:
                if proceso.returncode:
                    log(f"la app terminó con error (código {proceso.returncode}); "
                        "corrígelo y guarda para reintentar")
                else:
                    log("la app se cerró; se volverá a abrir cuando guardes un cambio")
                avisado = True

            if instantanea() == estado:
                continue

            time.sleep(0.3)  # deja que el editor termine de escribir
            nuevo = instantanea()
            cambiados = [r for r in nuevo if estado.get(r) != nuevo[r]]
            for ruta in cambiados:
                if ruta.suffix == ".ui" and ruta.parent == RAIZ and ruta.name in INTERFACES:
                    regenerar_ui(ruta)
            estado = instantanea()

            nombres = ", ".join(str(r.relative_to(RAIZ)) for r in cambiados) or "archivo eliminado"
            log(f"cambio en {nombres} -> reiniciando")
            detener()
            iniciar()
            avisado = False
    except KeyboardInterrupt:
        detener()
        log("detenido")


if __name__ == "__main__":
    main()
