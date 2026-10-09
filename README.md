# Sistema de préstamos de equipos

Trabajo de Programación Orientada a Objetos (OA 4). Sistema en Python para registrar los equipos del laboratorio (notebooks, proyectores y kits Arduino), prestarlos y devolverlos.

## Qué tiene

- Clases `Equipo` y `SistemaPrestamos` que controlan el estado de cada equipo
- Conexión a MySQL / MariaDB con **pymysql** (clase `BaseDatos`)
- Interfaz gráfica hecha con **Flet**
- Demostración por consola con 8 casos y 6 pruebas automáticas con `unittest`

## Cómo usarlo

```bash
pip install flet pymysql
```

```bash
python prestamos.py            # interfaz gráfica (Flet + MySQL)
python prestamos.py --consola  # demostración de los 8 casos en consola
python prestamos.py --test     # pruebas automáticas
```

## Base de datos

Por defecto se conecta a `localhost:3306` con usuario `root` sin contraseña (como XAMPP) y usa la base `laboratorio`. Se puede cambiar en `DB_CONFIG` o con las variables de entorno `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` y `DB_NAME`.

El programa crea la base de datos y las tablas solo. El script `base_datos.sql` tiene las mismas tablas por si se quieren crear a mano.

Si MySQL no está encendido, la interfaz igual abre y trabaja en memoria.

| Tabla | Para qué sirve |
|---|---|
| `equipos` | Cada equipo con su código (PK) y a quién está prestado (`prestado_a`, NULL si está disponible) |
| `prestamos` | Historial de préstamos con fecha de préstamo y de devolución (FK `codigo` → `equipos`) |
