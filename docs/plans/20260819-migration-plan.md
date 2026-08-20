# Plan de migracion: claves de config.json a ingles

## Contexto

El refactor de ayer (commit `ff600ee`) tradujo nombres de funciones, variables
y parametros del codigo Python a ingles (`Provider`, `send`, `TYPES`,
`get_provider`, etc.). Sin embargo, la estructura del archivo `config.json`
sigue en español (`proveedor_por_defecto`, `proveedores`, `tipo`, `modelo`,
`variable_api_key`, etc.), y el formato interno de historial de mensajes
tambien (`{"rol": "usuario"|"asistente", "texto": "..."}`).

Esta inconsistencia hace que el proyecto sea mas dificil de entender a nivel
global: el codigo Python (identificadores, clases) esta en ingles, pero el
contrato de datos (JSON de configuracion y formato interno de mensajes) esta
en español. El objetivo de este refactor es unificar todo bajo nombres en
ingles, completando el trabajo de accesibilidad global iniciado ayer.

Se hace un cambio limpio, sin shim de compatibilidad hacia atras: `config.json`
es un archivo local, versionado en el propio repo, sin usuarios externos ni
version publicada que dependa del formato anterior.

## Alcance

1. Claves de `config.json` (nivel raiz y por proveedor).
2. Todo el codigo que lee/valida/genera esas claves: `conexion.py` y `chat.py`.
3. Formato interno de historial de mensajes (`rol`/`texto` → `role`/`text`,
   `usuario`/`asistente` → `user`/`assistant`) en `conexion.py` y `chat.py`.
4. Documentacion que referencia estos nombres: `README.md` y `PLAN.md`
   (la prosa explicativa se mantiene en español; solo se actualizan los
   identificadores/ejemplos de codigo citados para que coincidan con los
   nuevos nombres).

Fuera de alcance: `CHECKLIST.md` (es un registro historico de tareas, no
documentacion tecnica de la estructura), y cualquier cambio funcional
(no se agrega ni quita comportamiento, es un renombrado puro).

## Mapeo de claves de config.json

| Español (actual) | Ingles (nuevo) | Ambito |
| --- | --- | --- |
| `proveedor_por_defecto` | `default_provider` | raiz |
| `timeout_segundos` | `timeout_seconds` | raiz |
| `max_tokens` | `max_tokens` (sin cambio) | raiz |
| `instruccion_sistema` | `system_prompt` | raiz |
| `proveedores` | `providers` | raiz |
| `tipo` | `type` | por proveedor |
| `modelo` | `model` | por proveedor |
| `url` | `url` (sin cambio) | por proveedor |
| `variable_api_key` | `api_key_env` | por proveedor |
| `version_api` | `api_version` | por proveedor (solo Anthropic) |
| `campo_max_tokens` | `max_tokens_field` | por proveedor (solo Mammouth) |

## Mapeo del formato interno de mensajes

| Español (actual) | Ingles (nuevo) |
| --- | --- |
| clave `"rol"` | clave `"role"` |
| clave `"texto"` | clave `"text"` |
| valor `"usuario"` | valor `"user"` |
| valor `"asistente"` | valor `"assistant"` |

Nota: los valores de rol para APIs externas (`"user"`/`"assistant"`/`"model"`)
ya estaban en ingles porque son el formato que exige cada proveedor; ahora
coinciden literalmente con el formato interno para OpenAI/Anthropic (deja de
haber traduccion en esos dos adaptadores).

## Archivos a modificar

### `config.json`
Reescribir con las claves nuevas, mismo contenido/valores.

### `conexion.py`
- `load_config`: cambiar las claves validadas (`"proveedores"` →
  `"providers"`, `"proveedor_por_defecto"` → `"default_provider"`, campos
  requeridos por proveedor `("tipo", "modelo", "url", "variable_api_key")` →
  `("type", "model", "url", "api_key_env")`).
- `list_providers`, `has_api_key`, `get_provider`: actualizar todos los
  accesos a `config["proveedores"]`, `data["tipo"]`, `data["variable_api_key"]`,
  etc.
- `Provider.__init__`: `provider_config["modelo"]` → `["model"]`.
- `Provider.__init__`: parametro/atributo `config.get("timeout_segundos", ...)`
  → `("timeout_seconds", ...)`, `config.get("max_tokens", ...)` sin cambio.
- `OpenAIProvider.send`, `AnthropicProvider.send`, `GeminiProvider.send`:
  cambiar `message["rol"] == "asistente"` → `message["role"] == "assistant"`,
  `message["texto"]` → `message["text"]`, y `self.config.get("campo_max_tokens", ...)`
  → `self.config.get("max_tokens_field", ...)`, `self.config.get("version_api", ...)`
  → `self.config.get("api_version", ...)`.
- Docstring de `Provider` que documenta el formato interno neutro: actualizar
  el ejemplo a `[{"role": "user"|"assistant", "text": "..."}]` (la prosa
  circundante se queda en español).

### `chat.py`
- `history.append({"rol": "usuario", "texto": user_input})` →
  `{"role": "user", "text": user_input}` (y el turno equivalente para
  `"asistente"`/`respuesta`).
- `turn = history + [{"rol": "usuario", "texto": user_input}]` → mismo cambio.
- `config["proveedor_por_defecto"]` → `config["default_provider"]`.
- `config.get("instruccion_sistema")` → `config.get("system_prompt")`.
- `config['proveedores'][name]['modelo']`, `['variable_api_key']` →
  `config['providers'][name]['model']`, `['api_key_env']`.

### `README.md`
- Seccion "Archivos": actualizar la descripcion de `config.json` si nombra
  claves en español.
- Seccion "Configuracion": actualizar la lista de claves documentadas
  (`proveedor_por_defecto`, `timeout_segundos`, `max_tokens`,
  `instruccion_sistema`, `tipo`, `modelo`, `url`, `variable_api_key`) a sus
  nuevos nombres en ingles.
- Seccion "Como añadir un tipo de API nuevo": ya menciona `Proveedor`,
  `enviar(mensajes, sistema)`, `TIPOS` y el formato `{"rol":..., "texto":...}`,
  que estan desactualizados respecto al codigo actual (clases reales:
  `Provider`, `send`, `TYPES`). Corregir para que coincida con el codigo real
  y con el nuevo formato `{"role":..., "text":...}`.

### `PLAN.md`
- Tabla de "Formato interno neutro": actualizar el ejemplo de
  `[{"rol": "usuario" | "asistente", "texto": "..."}]` a la version en ingles.
- Referencias sueltas a `Proveedor.enviar()` (linea ~20) y a `ErrorLLM`
  (lineas ~63, ~68) que tampoco coinciden con el codigo actual (`Provider`,
  `LLMError`): corregir de paso ya que se esta tocando esta seccion, para que
  la documentacion no quede desalineada del codigo (la prosa se mantiene en
  español).

## Orden de ejecucion sugerido

1. `config.json` (base de todo lo demas).
2. `conexion.py` (capa que lee la config y valida).
3. `chat.py` (capa que consume `conexion.py`).
4. `README.md` y `PLAN.md` (documentacion, al final para reflejar el estado
   final del codigo).

## Verificacion

1. `python chat.py` arranca sin errores de configuracion (usa el proveedor
   por defecto de `config.json`, ya con claves en ingles).
2. `/estado`, `/proveedores`, `/proveedor mammouth`, `/modelo <nombre>`,
   `/limpiar` siguen funcionando igual que antes (mismo comportamiento
   observable, sin regresiones).
3. Enviar un mensaje de prueba a un proveedor con clave disponible (por
   ejemplo Mammouth, como en la prueba real de ayer) y confirmar que la
   respuesta llega y el historial se mantiene entre turnos.
4. Revisar que no queden referencias residuales a las claves antiguas:
   buscar `proveedor_por_defecto`, `proveedores`, `variable_api_key`, `"rol"`,
   `"texto"`, `"asistente"`, `campo_max_tokens`, `version_api`,
   `instruccion_sistema`, `timeout_segundos` en `.py`, `.json` y `.md` del
   proyecto (excepto `CHECKLIST.md`, fuera de alcance) y confirmar que no
   aparece ninguna.
