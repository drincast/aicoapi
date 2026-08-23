# Plan: contador de tokens (entrada/salida) — v1

## Contexto

Hoy el chat no da ninguna señal de consumo: se envia el historial completo en
cada turno (`chat.py`, turno normal) y no hay forma de saber cuantos tokens
cuesta eso ni cuanto lleva gastado la sesion. Con historial en memoria que
crece turno a turno, el costo sube sin que se note.

Se quiere un contador de tokens de entrada y salida que **no dependa de SDKs ni
librerias de los proveedores** (`tiktoken`, `google-genai`, etc.), coherente
con la decision de diseño del proyecto de usar solo la biblioteca estandar
(`PLAN.md`, decision 1).

Punto clave que habilita el enfoque elegido: **las tres APIs ya devuelven el
conteo exacto en el JSON de respuesta** que `_json_request()` ya parsea. Leer
ese campo no es depender del SDK del proveedor — es el mismo trabajo de
traduccion de formatos que cada adaptador ya hace.

**Enfoque elegido (hibrido):** usar el `usage` real cuando la API lo manda
(exacto, es el numero facturado) y caer en una estimacion local cuando no
viene. La estimacion se marca en pantalla con `~` para que nunca se confunda
un numero aproximado con uno real.

Cambio limpio, sin compatibilidad hacia atras para el contrato de `send()`
(mismo criterio que los dos planes anteriores): es un proyecto local de un
solo usuario.

## Alcance

1. Nuevo modulo reutilizable `tokens.py`: estimacion local de tokens y las
   estructuras `Usage` / `SessionTokens`.
2. `connection.py`: los tres adaptadores (`OpenAIProvider`, `AnthropicProvider`,
   `GeminiProvider`) leen el `usage` real de cada API y `send()` pasa de
   devolver `str` a devolver un objeto `Response` (`text` + `usage`).
3. `chat.py`: consumir `Response`, mostrar una linea de tokens por turno,
   acumular en `SessionTokens` y nuevo comando `/tokens`.
4. `README.md` y `PLAN.md`: reflejar el nuevo archivo, el nuevo comando y el
   contrato actualizado de `send()`.

Fuera de alcance (posible v2): costo en dinero, aviso automatico por umbral de
contexto, recorte automatico de historial, persistencia entre sesiones.

## Decisiones tomadas

| Tema | Decision |
| --- | --- |
| Fuente | Hibrido: `usage` real de la API, con fallback a estimacion local |
| Formula de estimacion | Promedio de `chars/4` y `palabras*1.6` (corrige el sesgo del español) |
| Visualizacion | Linea discreta tras cada respuesta + comando `/tokens` con el desglose |
| Contrato de `send()` | Pasa de devolver `str` a devolver un objeto `Response` |

## Mapeo del campo `usage` por API

| Adaptador | Entrada | Salida |
| --- | --- | --- |
| `OpenAIProvider` (OpenAI, Mammouth) | `usage.prompt_tokens` | `usage.completion_tokens` |
| `AnthropicProvider` | `usage.input_tokens` | `usage.output_tokens` |
| `GeminiProvider` | `usageMetadata.promptTokenCount` | `usageMetadata.candidatesTokenCount` |

Si cualquiera de los dos campos falta o llega `None`, ese turno se estima
entero (no se mezcla un valor real con uno estimado: seria un numero
enganoso).

## Parte 1 — Nuevo modulo `tokens.py`

Modulo plano y reutilizable, mismo criterio que `farewells.py`: sin
dependencias externas y sin acoplarse a `chat.py`.

Contenido:

- Constantes de calibracion en la cabecera (`CHARS_PER_TOKEN = 4`,
  `TOKENS_PER_WORD = 1.6`, `MESSAGE_OVERHEAD = 4`), para poder ajustar la
  formula sin tocar la logica.
- `estimate_tokens(text)` — promedio de las dos reglas, minimo 1 para texto no
  vacio, 0 para vacio/`None`.
- `estimate_messages(messages, system=None)` — recorre el formato interno
  neutro `[{"role": ..., "text": ...}]`, suma `MESSAGE_OVERHEAD` por mensaje
  (los delimitadores de rol que el texto plano no refleja) y suma el `system`
  si viene.
- `Usage` (dataclass: `input_tokens`, `output_tokens`, `estimated=False`) con
  propiedad `total` y un `__str__` que antepone `~` cuando `estimated` es
  `True` → `"18 in / 12 out"` vs `"~16 in / ~40 out"`.
- `SessionTokens` — acumulador de la sesion: `add(usage)`, contadores
  `input_tokens` / `output_tokens` / `turns`, y una marca de si algun turno
  del acumulado fue estimado (para poder marcar el total como aproximado).

## Parte 2 — `connection.py`: exponer el `usage` real

El contrato de `send()` cambia de `-> str` a `-> Response`. Es un cambio
pequeño pero cruza toda la capa, asi que conviene hacerlo de una vez y no con
un atributo de efecto lateral tipo `self.last_usage`, que obliga a leer estado
despues de la llamada y se rompe en cuanto haya concurrencia.

1. Añadir `from tokens import Usage, estimate_messages, estimate_tokens` y una
   dataclass `Response` (campos `text` y `usage`) junto a `LLMError`.
2. En la clase base `Provider`, un helper compartido que evita repetir el
   fallback tres veces:

   ```python
   def _usage(self, raw_input, raw_output, messages, system, text):
       """Usage real si la API lo devolvio; si no, estimacion local."""
       if raw_input is not None and raw_output is not None:
           return Usage(int(raw_input), int(raw_output))
       return Usage(
           estimate_messages(messages, system),
           estimate_tokens(text),
           estimated=True,
       )
   ```

3. En cada uno de los tres `send()`, tras extraer el texto: leer los dos
   campos de la tabla de arriba con `.get()` encadenado tolerante
   (`(response.get("usage") or {}).get("prompt_tokens")`) y devolver
   `Response(text, self._usage(...))` en lugar del `str` pelado.
4. Actualizar el docstring de `Provider` para documentar el nuevo retorno.

Archivos: `connection.py` (las 3 clases `*Provider` + base + imports).

## Parte 3 — `chat.py`: mostrar y acumular

1. `from tokens import SessionTokens`; crear `session = SessionTokens()` junto
   a `history = []`.
2. En el turno normal: `result = provider.send(turn, system=system)` →
   `session.add(result.usage)`, `print_response(provider, result.text)` y una
   linea discreta `  tokens: {result.usage}` debajo de la respuesta. El
   historial sigue guardando `result.text` (string), sin cambios de formato.
3. Nuevo comando `/tokens` con el desglose:

   ```
   Ultimo turno:  18 in / 12 out
   Sesion:        18 in / 12 out
   Total:         30 tokens
   Turnos:        1
   ```

   Antes del primer turno: mensaje de "todavia no hay turnos en esta sesion".
4. Añadir `/tokens` al bloque `HELP`.
5. **`/clear` y `/provider` no resetean el acumulado**: limpian el historial,
   pero los tokens ya se gastaron. El acumulado es de la sesion completa.
   Dejarlo dicho en la descripcion de `/tokens` en `HELP` para que no
   sorprenda.

## Parte 4 — Documentacion

- `README.md`: fila de `/tokens` en la tabla de comandos, fila de `tokens.py`
  en la tabla de archivos, y una nota breve en "Como añadir un tipo de API
  nuevo" porque el contrato citado ahi (`send(messages, system) -> str`)
  queda desactualizado.
- `PLAN.md`: el diagrama de arquitectura y la seccion de formato interno, para
  reflejar que `send()` ahora devuelve `Response`.

## Orden de ejecucion

1. `tokens.py` (base independiente, no rompe nada).
2. `connection.py` (helper en la base + los 3 adaptadores).
3. `chat.py` (consumo, linea por turno, `/tokens`, `HELP`).
4. `README.md` y `PLAN.md`.

## Verificacion

1. Unitario rapido de la formula, sin red:
   `python -c "from tokens import estimate_tokens; print(estimate_tokens('Hola, como estas?'))"`
   → debe dar ~5 (real 6).
2. Arranque limpio: `printf "/help\n/tokens\n/exit\n" | python chat.py` —
   `/tokens` debe avisar que aun no hay turnos, sin reventar.
3. Turno real contra **mammouth** (es el proveedor por defecto y el que tiene
   clave disponible): enviar un mensaje corto y confirmar que la linea de
   tokens aparece **sin** `~` (usage exacto de la API).
4. Segundo turno seguido: confirmar que el `in` del segundo turno es mayor que
   el del primero (el historial se reenvia y crece) y que `/tokens` acumula
   bien.
5. Fallback de estimacion: forzarlo temporalmente devolviendo `None` en la
   extraccion del `usage` de `OpenAIProvider`, confirmar que la linea sale con
   `~`, y revertir. Sirve ademas para calibrar: comparar el estimado contra el
   exacto del paso 3 y ajustar `TOKENS_PER_WORD` si el error es grande.
6. `/clear` seguido de `/tokens`: el historial queda en 0 pero el acumulado se
   mantiene (comportamiento intencional).
