# aicoapi

Cliente de consola para hablar con varias APIs de LLM (OpenAI, Claude, Gemini,
Mammouth AI) desde una misma interfaz.

**Sin dependencias externas**: solo la biblioteca estandar de Python 3.11+.
Probado con Python 3.14.5.

## Puesta en marcha

1. Copia la plantilla de claves y rellena las que vayas a usar:

   ```powershell
   copy .env.example .env
   notepad .env
   ```

   No hace falta rellenarlas todas: basta con la del proveedor que quieras usar.
   El archivo `.env` esta en `.gitignore`, nunca se sube al repositorio.

2. Ejecuta el chat:

   ```powershell
   python chat.py
   ```

## Comandos de la consola

| Comando | Que hace |
| --- | --- |
| `/ayuda` | Muestra la ayuda |
| `/estado` | Proveedor y modelo activos, y turnos en memoria |
| `/proveedores` | Lista los proveedores configurados |
| `/proveedor <nombre>` | Cambia de proveedor (limpia el historial) |
| `/modelo <nombre>` | Cambia el modelo del proveedor actual |
| `/limpiar` | Borra el historial de la conversacion |
| `/salir` | Termina el programa |

Ejemplo de invocacion y uso de los comandos:

```
$ python chat.py

tu> /proveedores
tu> /proveedor mammouth
tu> /modelo kimi-k2.6
tu> Hola, como estas?
tu> /estado
tu> /limpiar
tu> /salir
``` 

Si el proveedor por defecto no tiene su clave definida, el programa **arranca
igualmente** sin proveedor activo: avisa, lista los que si tienen clave y puedes
elegir uno con `/proveedor <nombre>`. En `/proveedores` se marca cuales no tienen
clave y que variable les falta.

Cualquier otro texto se envia al modelo. El historial se mantiene en memoria y
se reenvia en cada turno, asi que el modelo recuerda lo hablado. Al cerrar el
programa el historial se pierde (la persistencia en SQLite es la v2).

## Archivos

| Archivo | Contenido |
| --- | --- |
| `conexion.py` | Configuracion, HTTP y traduccion al formato de cada API. No imprime nada. |
| `chat.py` | Interfaz de consola: ciclo de entrada, comandos e historial. |
| `config.json` | Proveedores, modelos, URLs, timeout y `max_tokens`. Sin secretos, versionable. |
| `.env` | Las API keys. Local, ignorado por git. |
| `PLAN.md` | Diseño del proyecto. |
| `CHECKLIST.md` | Estado del desarrollo. |

## Configuracion

Todo se ajusta en `config.json` sin tocar codigo:

- `default_provider`: con cual arranca la consola.
- `timeout_seconds`, `max_tokens`, `system_prompt`: globales.
- `providers.<nombre>`:
  - `type`: formato de API (`openai`, `anthropic`, `gemini`). Es lo que decide el
    adaptador, no el nombre. Mammouth usa el tipo `openai` porque su API es
    compatible con ese formato.
  - `model`, `url`, `api_key_env`: modelo, endpoint y nombre de la variable
    de entorno donde se busca la clave.

Para añadir un proveedor nuevo compatible con OpenAI basta con añadir una entrada
mas con `"type": "openai"` y su URL: no hay que escribir codigo.

## Como añadir un tipo de API nuevo

Crear una subclase de `Provider` en `conexion.py` que implemente
`send(messages, system) -> str`, y registrarla en el diccionario `TYPES`.
El historial llega siempre en el formato interno neutro
`[{"role": "user"|"assistant", "text": "..."}]`.
