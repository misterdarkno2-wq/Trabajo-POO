"""
Sistema de préstamos de equipos del laboratorio.
Actividad práctica de Programación Orientada a Objetos (OA 4).

Uso:
    python prestamos.py            -> abre la interfaz gráfica (Flet + MySQL)
    python prestamos.py --consola  -> demostración en consola (8 casos, en memoria)
    python prestamos.py --test     -> pruebas automatizadas (unittest, en memoria)

Requisitos:  pip install flet pymysql
"""

import os
import sys
import unittest

import pymysql


# ---------------------------------------------------------------------------
# Configuración de la base de datos (MySQL / MariaDB vía pymysql)
# Se puede cambiar aquí o con variables de entorno.
# ---------------------------------------------------------------------------

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "laboratorio"),
}


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------

class Equipo:
    """Un equipo del laboratorio. Solo puede estar prestado a una persona."""

    def __init__(self, codigo, nombre, tipo):
        codigo = str(codigo).strip().upper()
        nombre = str(nombre).strip()
        tipo = str(tipo).strip()
        if not codigo:
            raise ValueError("El código no puede estar vacío.")
        if not nombre:
            raise ValueError("El nombre no puede estar vacío.")
        if not tipo:
            raise ValueError("El tipo no puede estar vacío.")
        self.codigo = codigo
        self.nombre = nombre
        self.tipo = tipo
        self.prestado_a = None  # None = disponible

    def esta_disponible(self):
        return self.prestado_a is None

    def prestar(self, persona):
        persona = str(persona).strip()
        if not persona:
            raise ValueError("Debe indicar a quién se presta el equipo.")
        if not self.esta_disponible():
            raise ValueError(
                f"El equipo {self.codigo} ya está prestado a {self.prestado_a}."
            )
        self.prestado_a = persona

    def devolver(self):
        if self.esta_disponible():
            raise ValueError(f"El equipo {self.codigo} no está prestado.")
        self.prestado_a = None

    def estado(self):
        return "Disponible" if self.esta_disponible() else f"Prestado a {self.prestado_a}"

    def __str__(self):
        return f"[{self.codigo}] {self.nombre} ({self.tipo}) - {self.estado()}"


class ErrorBaseDatos(Exception):
    """Falla de conexión o de consulta en MySQL."""


class BaseDatos:
    """Guarda los equipos y el historial de préstamos en MySQL con pymysql."""

    def __init__(self, config=None):
        config = dict(config or DB_CONFIG)
        nombre_bd = config.pop("database")
        try:
            # Crea la base de datos si no existe
            conexion = pymysql.connect(**config, charset="utf8mb4")
            with conexion.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{nombre_bd}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            conexion.close()

            self.conexion = pymysql.connect(
                **config, database=nombre_bd, charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor, autocommit=False,
            )
            self._crear_tablas()
        except pymysql.MySQLError as error:
            raise ErrorBaseDatos(f"No se pudo conectar a MySQL: {error}") from error

    def _ejecutar(self, sql, parametros=None):
        try:
            self.conexion.ping(reconnect=True)
            with self.conexion.cursor() as cursor:
                cursor.execute(sql, parametros)
                filas = cursor.fetchall()
            self.conexion.commit()
            return filas
        except pymysql.MySQLError as error:
            self.conexion.rollback()
            raise ErrorBaseDatos(f"Error de base de datos: {error}") from error

    def _crear_tablas(self):
        self._ejecutar("""
            CREATE TABLE IF NOT EXISTS equipos (
                codigo      VARCHAR(20)  PRIMARY KEY,
                nombre      VARCHAR(100) NOT NULL,
                tipo        VARCHAR(50)  NOT NULL,
                prestado_a  VARCHAR(100) NULL
            )
        """)
        self._ejecutar("""
            CREATE TABLE IF NOT EXISTS prestamos (
                id               INT AUTO_INCREMENT PRIMARY KEY,
                codigo           VARCHAR(20)  NOT NULL,
                persona          VARCHAR(100) NOT NULL,
                fecha_prestamo   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                fecha_devolucion DATETIME     NULL,
                FOREIGN KEY (codigo) REFERENCES equipos(codigo)
            )
        """)

    def cargar_equipos(self):
        return self._ejecutar(
            "SELECT codigo, nombre, tipo, prestado_a FROM equipos ORDER BY codigo")

    def insertar_equipo(self, equipo):
        self._ejecutar(
            "INSERT INTO equipos (codigo, nombre, tipo, prestado_a) VALUES (%s, %s, %s, NULL)",
            (equipo.codigo, equipo.nombre, equipo.tipo),
        )

    def registrar_prestamo(self, equipo):
        self._ejecutar("UPDATE equipos SET prestado_a = %s WHERE codigo = %s",
                       (equipo.prestado_a, equipo.codigo))
        self._ejecutar("INSERT INTO prestamos (codigo, persona) VALUES (%s, %s)",
                       (equipo.codigo, equipo.prestado_a))

    def registrar_devolucion(self, equipo):
        self._ejecutar("UPDATE equipos SET prestado_a = NULL WHERE codigo = %s",
                       (equipo.codigo,))
        self._ejecutar(
            "UPDATE prestamos SET fecha_devolucion = NOW() "
            "WHERE codigo = %s AND fecha_devolucion IS NULL",
            (equipo.codigo,),
        )

    def cerrar(self):
        self.conexion.close()


class SistemaPrestamos:
    """Administra los equipos registrados y sus préstamos.

    Sin base de datos (bd=None) trabaja solo en memoria.
    Con base de datos, carga los equipos al iniciar y guarda cada cambio.
    """

    def __init__(self, bd=None):
        self.equipos = {}  # codigo -> Equipo
        self.bd = bd
        if bd:
            for fila in bd.cargar_equipos():
                equipo = Equipo(fila["codigo"], fila["nombre"], fila["tipo"])
                equipo.prestado_a = fila["prestado_a"]
                self.equipos[equipo.codigo] = equipo

    def registrar_equipo(self, codigo, nombre, tipo):
        equipo = Equipo(codigo, nombre, tipo)  # valida los datos
        if equipo.codigo in self.equipos:
            raise ValueError(f"Ya existe un equipo con el código {equipo.codigo}.")
        if self.bd:
            self.bd.insertar_equipo(equipo)
        self.equipos[equipo.codigo] = equipo
        return equipo

    def buscar(self, codigo):
        codigo = str(codigo).strip().upper()
        if codigo not in self.equipos:
            raise ValueError(f"No existe un equipo con el código {codigo}.")
        return self.equipos[codigo]

    def prestar(self, codigo, persona):
        equipo = self.buscar(codigo)
        equipo.prestar(persona)
        if self.bd:
            try:
                self.bd.registrar_prestamo(equipo)
            except ErrorBaseDatos:
                equipo.prestado_a = None  # si MySQL falla, se deshace el cambio
                raise
        return equipo

    def devolver(self, codigo):
        equipo = self.buscar(codigo)
        persona = equipo.prestado_a
        equipo.devolver()
        if self.bd:
            try:
                self.bd.registrar_devolucion(equipo)
            except ErrorBaseDatos:
                equipo.prestado_a = persona  # si MySQL falla, se deshace el cambio
                raise
        return equipo

    def listar(self):
        return list(self.equipos.values())

    def disponibles(self):
        return [e for e in self.equipos.values() if e.esta_disponible()]

    def prestados(self):
        return [e for e in self.equipos.values() if not e.esta_disponible()]


def crear_sistema_demo(bd=None):
    """Sistema con los tres equipos ficticios del laboratorio.

    Si la base de datos ya tiene equipos, no se vuelven a insertar.
    """
    sistema = SistemaPrestamos(bd)
    if not sistema.listar():
        sistema.registrar_equipo("NB-01", "Notebook Lenovo", "Notebook")
        sistema.registrar_equipo("PR-01", "Proyector Epson", "Proyector")
        sistema.registrar_equipo("AR-01", "Kit Arduino Uno", "Kit Arduino")
    return sistema


# ---------------------------------------------------------------------------
# Demostración en consola: 8 casos revisados
# ---------------------------------------------------------------------------

def demo_consola():
    sistema = SistemaPrestamos()

    def caso(numero, descripcion, accion, esperado):
        try:
            accion()
            resultado = "OK"
        except (ValueError, ErrorBaseDatos) as error:
            resultado = f"ERROR: {error}"
        cumple = (resultado == "OK") == (esperado == "OK")
        print(f"Caso {numero}: {descripcion}")
        print(f"  Esperado: {esperado} | Obtenido: {resultado} | {'✔' if cumple else '✘'}")

    def listar():
        for equipo in sistema.listar():
            print("   ", equipo)
        print()

    print("=== Sistema de préstamos de equipos ===\n")

    caso(1, "Registrar tres equipos válidos", lambda: (
        sistema.registrar_equipo("NB-01", "Notebook Lenovo", "Notebook"),
        sistema.registrar_equipo("PR-01", "Proyector Epson", "Proyector"),
        sistema.registrar_equipo("AR-01", "Kit Arduino Uno", "Kit Arduino"),
    ), "OK")
    listar()

    caso(2, "Registrar un código repetido (NB-01)",
         lambda: sistema.registrar_equipo("NB-01", "Otro notebook", "Notebook"), "ERROR")
    print(f"  Equipos registrados: {len(sistema.listar())} (deben seguir siendo 3)\n")

    caso(3, "Prestar NB-01 a Ana Pérez",
         lambda: sistema.prestar("NB-01", "Ana Pérez"), "OK")
    listar()

    caso(4, "Prestar NB-01 (ya prestado) a Luis Soto",
         lambda: sistema.prestar("NB-01", "Luis Soto"), "ERROR")
    print(f"  NB-01 sigue: {sistema.buscar('NB-01').estado()}\n")

    caso(5, "Prestar un código inexistente (XX-99)",
         lambda: sistema.prestar("XX-99", "Ana Pérez"), "ERROR")
    print()

    caso(6, "Prestar PR-01 sin indicar persona",
         lambda: sistema.prestar("PR-01", "   "), "ERROR")
    print(f"  PR-01 sigue: {sistema.buscar('PR-01').estado()}\n")

    caso(7, "Devolver NB-01",
         lambda: sistema.devolver("NB-01"), "OK")
    listar()

    caso(8, "Devolver AR-01 (no estaba prestado)",
         lambda: sistema.devolver("AR-01"), "ERROR")
    print(f"  AR-01 sigue: {sistema.buscar('AR-01').estado()}\n")

    print("Listado final:")
    listar()


# ---------------------------------------------------------------------------
# Pruebas automatizadas
# ---------------------------------------------------------------------------

class PruebasSistema(unittest.TestCase):

    def setUp(self):
        self.sistema = crear_sistema_demo()

    def test_prestamo_y_devolucion(self):
        self.sistema.prestar("NB-01", "Ana Pérez")
        self.assertEqual(self.sistema.buscar("NB-01").prestado_a, "Ana Pérez")
        self.sistema.devolver("NB-01")
        self.assertTrue(self.sistema.buscar("NB-01").esta_disponible())

    def test_no_prestar_equipo_ya_prestado(self):
        self.sistema.prestar("PR-01", "Ana Pérez")
        with self.assertRaises(ValueError):
            self.sistema.prestar("PR-01", "Luis Soto")
        # el error no cambia los datos
        self.assertEqual(self.sistema.buscar("PR-01").prestado_a, "Ana Pérez")

    def test_codigo_duplicado_no_se_registra(self):
        with self.assertRaises(ValueError):
            self.sistema.registrar_equipo("AR-01", "Otro kit", "Kit Arduino")
        self.assertEqual(len(self.sistema.listar()), 3)
        self.assertEqual(self.sistema.buscar("AR-01").nombre, "Kit Arduino Uno")

    def test_devolver_equipo_disponible_falla(self):
        with self.assertRaises(ValueError):
            self.sistema.devolver("AR-01")
        self.assertTrue(self.sistema.buscar("AR-01").esta_disponible())

    def test_codigo_inexistente(self):
        with self.assertRaises(ValueError):
            self.sistema.prestar("XX-99", "Ana Pérez")

    def test_falla_de_mysql_no_altera_datos(self):
        class BaseDatosQueFalla:
            def cargar_equipos(self):
                return [{"codigo": "NB-01", "nombre": "Notebook Lenovo",
                         "tipo": "Notebook", "prestado_a": None}]

            def registrar_prestamo(self, equipo):
                raise ErrorBaseDatos("conexión perdida")

        sistema = SistemaPrestamos(BaseDatosQueFalla())
        with self.assertRaises(ErrorBaseDatos):
            sistema.prestar("NB-01", "Ana Pérez")
        self.assertTrue(sistema.buscar("NB-01").esta_disponible())


# ---------------------------------------------------------------------------
# Interfaz gráfica con Flet
# ---------------------------------------------------------------------------

def main_flet(page):
    import flet as ft

    try:
        bd = BaseDatos()
        sistema = crear_sistema_demo(bd)
        estado_bd = ft.Text(
            f"● Conectado a MySQL ({DB_CONFIG['host']}/{DB_CONFIG['database']})",
            color=ft.Colors.GREEN_700)
    except ErrorBaseDatos as error:
        sistema = crear_sistema_demo()
        estado_bd = ft.Text(f"● Sin base de datos, trabajando en memoria. {error}",
                            color=ft.Colors.RED_700)

    page.title = "Préstamos de equipos"
    page.window.width = 900
    page.window.height = 700
    page.padding = 20
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO

    def avisar(texto, error=False):
        page.show_dialog(ft.SnackBar(
            ft.Text(texto, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
        ))

    # --- Tabla de equipos ---
    tabla = ft.DataTable(
        columns=[
            ft.DataColumn("Código"),
            ft.DataColumn("Nombre"),
            ft.DataColumn("Tipo"),
            ft.DataColumn("Estado"),
        ],
        rows=[],
        heading_row_color=ft.Colors.BLUE_50,
    )
    resumen = ft.Text(size=14, color=ft.Colors.GREY_700)

    # --- Formularios ---
    reg_codigo = ft.TextField(label="Código", width=140)
    reg_nombre = ft.TextField(label="Nombre", width=220)
    reg_tipo = ft.Dropdown(
        label="Tipo", width=180, value="Notebook",
        options=[ft.DropdownOption(t) for t in ("Notebook", "Proyector", "Kit Arduino")],
    )

    pre_equipo = ft.Dropdown(label="Equipo disponible", width=260)
    pre_persona = ft.TextField(label="Persona", width=220)

    dev_equipo = ft.Dropdown(label="Equipo prestado", width=260)

    def refrescar():
        tabla.rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(e.codigo, weight=ft.FontWeight.BOLD)),
                ft.DataCell(e.nombre),
                ft.DataCell(e.tipo),
                ft.DataCell(ft.Text(
                    e.estado(),
                    color=ft.Colors.GREEN_700 if e.esta_disponible() else ft.Colors.ORANGE_800,
                )),
            ])
            for e in sistema.listar()
        ]
        pre_equipo.options = [
            ft.DropdownOption(key=e.codigo, text=f"{e.codigo} - {e.nombre}")
            for e in sistema.disponibles()
        ]
        dev_equipo.options = [
            ft.DropdownOption(key=e.codigo, text=f"{e.codigo} - {e.prestado_a}")
            for e in sistema.prestados()
        ]
        pre_equipo.value = None
        dev_equipo.value = None
        resumen.value = (
            f"Total: {len(sistema.listar())}  ·  "
            f"Disponibles: {len(sistema.disponibles())}  ·  "
            f"Prestados: {len(sistema.prestados())}"
        )
        page.update()

    def on_registrar(e):
        try:
            equipo = sistema.registrar_equipo(
                reg_codigo.value or "", reg_nombre.value or "", reg_tipo.value or "")
            reg_codigo.value = ""
            reg_nombre.value = ""
            avisar(f"Equipo {equipo.codigo} registrado.")
        except (ValueError, ErrorBaseDatos) as error:
            avisar(str(error), error=True)
        refrescar()

    def on_prestar(e):
        try:
            if not pre_equipo.value:
                raise ValueError("Seleccione un equipo disponible.")
            equipo = sistema.prestar(pre_equipo.value, pre_persona.value or "")
            pre_persona.value = ""
            avisar(f"{equipo.codigo} prestado a {equipo.prestado_a}.")
        except (ValueError, ErrorBaseDatos) as error:
            avisar(str(error), error=True)
        refrescar()

    def on_devolver(e):
        try:
            if not dev_equipo.value:
                raise ValueError("Seleccione un equipo prestado.")
            equipo = sistema.devolver(dev_equipo.value)
            avisar(f"{equipo.codigo} devuelto. Ya está disponible.")
        except (ValueError, ErrorBaseDatos) as error:
            avisar(str(error), error=True)
        refrescar()

    def tarjeta(titulo, icono, controles):
        return ft.Card(content=ft.Container(
            padding=16,
            content=ft.Column([
                ft.Row([ft.Icon(icono, color=ft.Colors.BLUE_700),
                        ft.Text(titulo, size=16, weight=ft.FontWeight.BOLD)]),
                ft.Row(controles, wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ]),
        ))

    page.add(
        ft.Text("Sistema de préstamos de equipos", size=26, weight=ft.FontWeight.BOLD),
        estado_bd,
        resumen,
        tarjeta("Equipos del laboratorio", ft.Icons.INVENTORY_2, [tabla]),
        tarjeta("Registrar equipo", ft.Icons.ADD_BOX, [
            reg_codigo, reg_nombre, reg_tipo,
            ft.FilledButton("Registrar", icon=ft.Icons.ADD, on_click=on_registrar),
        ]),
        tarjeta("Prestar equipo", ft.Icons.OUTBOX, [
            pre_equipo, pre_persona,
            ft.FilledButton("Prestar", icon=ft.Icons.ARROW_UPWARD, on_click=on_prestar),
        ]),
        tarjeta("Devolver equipo", ft.Icons.MOVE_TO_INBOX, [
            dev_equipo,
            ft.FilledButton("Devolver", icon=ft.Icons.ARROW_DOWNWARD, on_click=on_devolver),
        ]),
    )
    refrescar()


if __name__ == "__main__":
    if "--consola" in sys.argv:
        demo_consola()
    elif "--test" in sys.argv:
        unittest.main(argv=[sys.argv[0], "-v"])
    else:
        import flet as ft
        ft.run(main_flet)
