# Plan de migracion: nombre de archivo y comandos del chat a ingles

## Contexto

Tras migrar `config.json` y el formato interno de mensajes a ingles
(`docs/plans/20260819-migration-plan.md`), quedan dos piezas en español que
generan la misma inconsistencia: el nombre del archivo `conexion.py` y los
comandos de consola de `chat.py` (`/ayuda`, `/proveedor`, etc.). El objetivo es
terminar de unificar el proyecto bajo nombres en ingles para que sea
entendible a nivel global, manteniendo (como se acordo) toda la prosa
explicativa, mensajes y comentarios en español.

Se aprovecha tambien para añadir un mensaje de despedida aleatorio y
reutilizable (bilingue, con citas de peliculas) que reemplaza el actual
`"Hasta luego."` fijo.

Cambio limpio, sin alias/compatibilidad hacia atras para el nombre de archivo
ni para los comandos viejos (mismo criterio que el plan anterior): es un
proyecto local de un solo usuario.

## Alcance

1. **Renombrar `conexion.py` → `connection.py`. Este paso lo ejecuta el
   usuario manualmente, no el agente.** El agente NO debe tocar este archivo
   ni el import en `chat.py` correspondiente: debe detenerse antes de la
   Parte 1, esperar a que el usuario confirme explicitamente "alcance 1
   listo" (o equivalente), y recien ahi continuar con las partes 2 y 3. Ver
   la Parte 1 mas abajo, escrita como instructivo paso a paso para que el
   usuario la ejecute a mano.
2. Traducir los 7 comandos de consola de `chat.py` (solo los nombres de
   comando; el resto de mensajes/prompts se queda en español).
3. Nuevo modulo reutilizable `farewells.py` con mensajes de despedida
   aleatorios bilingues (incluye citas de peliculas), usado en las tres
   salidas del programa (`/exit`, `/bye`, `Ctrl+C`/`Ctrl+D`).
4. Actualizar `README.md` y `PLAN.md` (tabla de archivos, tabla de comandos,
   ejemplo de uso) para que coincidan. `CHECKLIST.md` y
   `docs/plans/20260819-migration-plan.md` quedan fuera de alcance: son
   registro historico de tareas ya hechas, no documentacion viva (mismo
   criterio que el plan anterior).

## Punto de control obligatorio antes de la Parte 1

El agente que ejecute este plan debe:

1. Anunciar el inicio y explicar que la Parte 1 (renombrar `conexion.py`) la
   hace el usuario manualmente.
2. **Detenerse y esperar** — no avanzar a la Parte 2 ni a la Parte 3, no
   tocar `chat.py`, `README.md` ni `PLAN.md` — hasta que el usuario informe
   explicitamente que el alcance 1 esta completo (por ejemplo: "alcance 1
   listo", "ya renombre el archivo", "listo el paso 1").
3. Antes de continuar, verificar por su cuenta que el cambio quedo bien
   hecho: que existe `connection.py` (y ya no `conexion.py`), y que
   `chat.py` importa desde `connection` y no desde `conexion`. Si algo no
   coincide, avisar al usuario en vez de asumir o corregirlo por su cuenta.

## Parte 1 — Renombrar `conexion.py` → `connection.py` (manual, la hace el usuario)

**Esta parte no la ejecuta el agente.** Se deja documentada aqui como
instructivo para que el usuario la haga a mano, con el detalle suficiente
para no dejar nada a medias. Cuando termine, el agente retoma con la Parte 2.

### Por que es un cambio de bajo riesgo

Hay un unico punto de acoplamiento en todo el proyecto: el `import` que hace
`chat.py`. Nada mas en el codigo referencia el nombre del archivo
`conexion.py` (las clases, funciones y variables internas ya quedaron en
ingles en el refactor anterior). Por eso alcanza con dos pasos.

### Paso a paso

1. **Verificar que no hay cambios sin guardar** antes de tocar nada:

   ```powershell
   git status
   ```

   Si aparece algo pendiente que no sea de este cambio, guardalo o
   descartalo primero (no mezclar con este rename).

2. **Renombrar el archivo preservando el historial de git.** No usar
   "cortar y pegar" ni crear el archivo nuevo a mano y borrar el viejo:
   usar `git mv`, que hace ambas cosas a la vez y deja registrado en git que
   es un rename (no un archivo borrado + uno nuevo):

   ```powershell
   git mv conexion.py connection.py
   ```

3. **Actualizar el import en `chat.py`.** Es la unica linea del proyecto que
   necesita tocarse. Buscar (alrededor de la linea 11):

   ```python
   from conexion import (
       LLMError,
       load_config,
       load_env,
       list_providers,
       get_provider,
       has_api_key,
   )
   ```

   y cambiar solo el nombre del modulo:

   ```python
   from connection import (
       LLMError,
       load_config,
       load_env,
       list_providers,
       get_provider,
       has_api_key,
   )
   ```

   El contenido interno de `connection.py` (docstring del modulo,
   comentarios, `CONFIG_PATH`/`ENV_PATH`, nombres de clases) no cambia en
   esta parte: ya quedaron en ingles (o son prosa en español que se
   mantiene) en el refactor anterior.

4. **Probar que arranca** antes de dar el paso por terminado:

   ```powershell
   python chat.py
   ```

   Si arranca sin `ImportError` y muestra el banner de la consola, el rename
   quedo bien. Salir con `/salir` (los comandos todavia estan en español en
   este punto: la Parte 2 es la que los traduce).

5. **Revisar que `conexion.py` ya no existe** y que `connection.py` si (por
   ejemplo con `git status`, deberia verse el rename detectado por git en
   lugar de un archivo borrado y otro sin trackear).

6. Cuando estos 5 pasos esten hechos y verificados, **avisar al agente**
   (por ejemplo: "alcance 1 listo") para que continue con la Parte 2 y la
   Parte 3 del plan.

## Parte 2 — Comandos de `chat.py`

| Español (actual) | Ingles (nuevo) |
| --- | --- |
| `/ayuda` | `/help` |
| `/estado` | `/status` |
| `/proveedores` | `/providers` |
| `/proveedor <nombre>` | `/provider <nombre>` |
| `/modelo <nombre>` | `/model <nombre>` |
| `/limpiar` | `/clear` |
| `/salir` | `/exit` **y** `/bye` (dos alias equivalentes) |

Puntos de `chat.py` a tocar (ademas de los `if command == "/..."`):
- Bloque `HELP`: los 7 nombres de comando en la lista (las descripciones se
  quedan en español). Añadir la linea de `/bye` junto a `/exit` como alias.
- Mensajes que referencian un comando por su nombre dentro del texto:
  - `"Uso: /proveedor <nombre>. Ver /proveedores"` → `"Uso: /provider <nombre>. Ver /providers"`
  - `"No hay proveedor activo. Usa /proveedor <nombre> primero."` → referencia a `/provider`
  - `"No hay proveedor activo. Usa /proveedor <nombre> (ver /proveedores).\n"` → referencias a `/provider` y `/providers`
  - `"Elige uno con:  /proveedor <nombre>"` (aviso de arranque) → `/provider`
  - `"Sin proveedor activo. Elige uno con /proveedor <nombre> | ..."` (en `/status`) → `/provider`
- El resto del texto de esos mensajes (la prosa en español) no cambia.

## Parte 3 — Mensajes de despedida aleatorios y reutilizables

Nuevo archivo `farewells.py` en la raiz del proyecto, sin dependencias
externas (solo `random` de la stdlib):

```python
"""Mensajes de despedida aleatorios y reutilizables.

Uso: from farewells import random_farewell
"""

import random

FAREWELLS = [
    # Espanol, casuales
    "Hasta luego.",
    "Nos vemos.",
    "Adios.",
    "Cuidate mucho.",
    # Ingles, casuales
    "Bye!",
    "See you later.",
    "Take care!",
    "Catch you later.",
    # Citas de peliculas
    "Hasta la vista, baby. (Terminator 2: Judgment Day, 1991)",
    "I'll be back. (The Terminator, 1984)",
    "May the Force be with you. (Star Wars, 1977)",
    "Live long and prosper. (Star Trek)",
    "So long, and thanks for all the fish. (The Hitchhiker's Guide to the Galaxy)",
    "That's all, folks! (Looney Tunes)",
]


def random_farewell():
    """Devuelve un mensaje de despedida al azar."""
    return random.choice(FAREWELLS)
```

Lista de ejemplo propuesta arriba (14 mensajes: 4 en español, 4 en ingles, 6
citas de peliculas verificadas). Revisar/ajustar el contenido exacto al
implementar si quieres agregar, quitar o cambiar alguna frase — el diseño
(lista plana + `random.choice`) es intencionalmente simple para que sea facil
de extender despues sin tocar la funcion.

Reutilizable: cualquier otro modulo puede hacer `from farewells import
random_farewell` sin acoplarse a `chat.py`.

### Integracion en `chat.py`

Los tres puntos de salida del programa imprimen hoy un texto fijo:

```python
except (EOFError, KeyboardInterrupt):
    print("\nHasta luego.")
    return 0
...
if command == "/salir":
    print("Hasta luego.")
    return 0
```

Pasan a:

```python
from farewells import random_farewell
...
except (EOFError, KeyboardInterrupt):
    print(f"\n{random_farewell()}")
    return 0
...
if command in ("/exit", "/bye"):
    print(random_farewell())
    return 0
```

## Archivos a modificar

- `conexion.py` → `connection.py`: **manual, lo hace el usuario (Parte 1)**.
  El agente no lo toca; solo verifica que ya este hecho antes de continuar.
- `chat.py`: import actualizado — **ya viene hecho del paso manual**; el
  agente solo agrega en este archivo los 7 comandos renombrados + alias
  `/bye`, los mensajes que citan comandos por nombre, y la integracion de
  `random_farewell()` en los 3 puntos de salida.
- `farewells.py` (nuevo, lo crea el agente).
- `README.md`: tabla de "Archivos" (`conexion.py`→`connection.py`), tabla de
  "Comandos de la consola" (7 filas con los nuevos nombres + fila de `/bye`),
  ejemplo de invocacion (bloque de comandos de ejemplo). Lo hace el agente.
- `PLAN.md`: diagrama de arquitectura (`conexion.py`→`connection.py`). Lo
  hace el agente.

## Orden de ejecucion

1. **(Manual, usuario)** Parte 1 completa: `git mv conexion.py
   connection.py` + actualizar el import en `chat.py` + probar que arranca.
   El agente espera aqui hasta recibir confirmacion.
2. **(Agente)** Verificar que la Parte 1 quedo aplicada (existe
   `connection.py`, `chat.py` importa de `connection`).
3. **(Agente)** `farewells.py` (nuevo modulo, independiente, sin tocar nada
   existente).
4. **(Agente)** Comandos de `chat.py`: renombrar los 7 `if command == ...`,
   el bloque `HELP`, los mensajes que citan comandos, y conectar
   `random_farewell()` en los 3 puntos de salida.
5. **(Agente)** `README.md` y `PLAN.md`.

## Verificacion

1. `python chat.py` arranca sin `ImportError` (confirma el rename de Parte 1).
2. Probar cada comando nuevo manualmente: `/help`, `/status`, `/providers`,
   `/provider <nombre>`, `/model <nombre>`, `/clear`, `/exit`.
3. Probar `/bye` por separado (debe comportarse igual que `/exit`).
4. Probar un comando viejo (`/ayuda`, `/proveedor`) y confirmar que responde
   "Comando desconocido" (no hay compatibilidad hacia atras, es el
   comportamiento esperado).
5. Salir varias veces (con `/exit`, con `/bye`, y con Ctrl+C) y confirmar que
   el mensaje de despedida cambia entre ejecuciones (aleatoriedad real).
6. `grep` final por `conexion`, `/ayuda`, `/estado`, `/proveedores`,
   `/proveedor`, `/modelo`, `/limpiar`, `/salir` en `.py` y `README.md`/`PLAN.md`
   para confirmar que no queda ninguna referencia residual (excepto en los
   documentos de plan e historico, fuera de alcance).
