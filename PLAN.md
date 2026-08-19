# Plan de desarrollo — aicoapi

## Objetivo

Centralizar la conexion a varias APIs de LLM (OpenAI, Claude, Gemini, Mammouth AI)
detras de una interfaz comun, con una UI de consola que mantenga un ciclo de
conversacion.

## Entorno

Python 3.14.5 (`D:\Desarrollo\python\py314\python.exe`), pip 26.1.2.
Paquetes instalados en el sistema: `pip`, `pipx`, `click`, `colorama`, `packaging`,
`platformdirs`, `argcomplete`, `userpath`. No hay `requests`, `httpx` ni SDKs.

## Decisiones

1. **Sin dependencias externas.** Se usa `urllib.request` + `json` de la stdlib.
   Las cuatro APIs son REST/HTTP planas, y Python 3.14 es muy reciente (riesgo de
   que los SDKs oficiales aun no tengan wheels). Si mas adelante conviene migrar a
   los SDKs, la interfaz `Proveedor.enviar()` no cambia.
2. **`config.json` versionable + `.env` para las claves.** Separa secretos de
   configuracion desde el primer dia. Las variables del entorno del sistema tienen
   prioridad sobre el archivo `.env`.
3. **v1: historial en memoria**, respuesta completa, comandos de consola.
4. **v2: SQLite y streaming.** Fuera del alcance actual.

## Arquitectura

```
chat.py       UI: ciclo de entrada, comandos, historial. Es el unico que imprime.
   |
   v
conexion.py   Config + HTTP + traduccion de formatos. No imprime nada.
   |
   v
config.json + .env
```

### Formato interno neutro

El historial viaja siempre asi entre las dos capas:

```python
[{"rol": "usuario" | "asistente", "texto": "..."}]
```

Cada subclase de `Proveedor` lo traduce al formato de su API. Añadir un proveedor
nuevo no obliga a tocar `chat.py`.

### Diferencias entre APIs que resuelve cada adaptador

| | OpenAI / Mammouth | Anthropic | Gemini |
| --- | --- | --- | --- |
| Endpoint | `/v1/chat/completions` | `/v1/messages` | `/models/{modelo}:generateContent` |
| Auth | `Authorization: Bearer` | `x-api-key` + `anthropic-version` | `x-goog-api-key` |
| Sistema | un mensaje `role: system` | campo `system` aparte | campo `systemInstruction` |
| Rol del modelo | `assistant` | `assistant` | `model` |
| Limite de tokens | `max_completion_tokens` (`max_tokens` en Mammouth) | `max_tokens` (obligatorio) | `generationConfig.maxOutputTokens` |
| Texto en respuesta | `choices[0].message.content` | `content[*].text` | `candidates[0].content.parts[*].text` |

### Manejo de errores

Todo fallo de la capa de conexion sale como `ErrorLLM` con mensaje legible: falta
de configuracion, API key ausente, error HTTP (incluyendo el cuerpo de la
respuesta, que es donde los proveedores explican el fallo real), timeout, fallo de
red o respuesta con forma inesperada.

En `chat.py` un `ErrorLLM` se imprime y **el bucle continua**: no se pierde la
conversacion. Si la llamada falla, el turno del usuario **no** se añade al
historial, para que no quede desalineado.

## Estado

Ver `CHECKLIST.md`.

## v2

- **SQLite** (`sqlite3`, stdlib): tablas `conversacion(id, inicio, proveedor, modelo)`
  y `mensaje(id, conversacion_id, orden, rol, texto, creado)`; comandos `/guardar`,
  `/historial`, `/cargar <id>`.
- **Streaming token a token**: `stream: true` y lectura de la respuesta linea a
  linea. El formato de los eventos SSE difiere entre OpenAI, Anthropic y Gemini,
  asi que cada adaptador necesita su propio parseo. Por eso no entra en v1.
