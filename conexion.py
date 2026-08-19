"""Capa de conexion a las APIs de LLM (OpenAI, Anthropic, Gemini, Mammouth, etc).

Esta capa no imprime nada por consola: solo lee configuracion, hace la peticion
HTTP y devuelve texto. Cualquier fallo se propaga como ErrorLLM.

Solo usa la biblioteca estandar de Python: no requiere instalar dependencias.
"""

import json
import os
import urllib.error
import urllib.request

RUTA_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
RUTA_ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

# Necesario: algunos proveedores estan detras de Cloudflare y devuelven 403
# (error 1010) al User-Agent por defecto de urllib ("Python-urllib/x.y").
USER_AGENT = "aicoapi/1.0"


class ErrorLLM(Exception):
    """Error unico de esta capa, con mensaje legible para el usuario."""


# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------

def cargar_env(ruta=RUTA_ENV):
    """Carga pares CLAVE=valor de un archivo .env dentro de os.environ.

    No pisa variables ya definidas en el entorno del sistema: estas tienen
    prioridad sobre el archivo. Si el archivo no existe, no hace nada.
    Devuelve la lista de claves cargadas.
    """
    cargadas = []
    if not os.path.exists(ruta):
        return cargadas

    with open(ruta, "r", encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            clave = clave.strip()
            valor = valor.strip().strip('"').strip("'")
            if clave and clave not in os.environ:
                os.environ[clave] = valor
                cargadas.append(clave)
    return cargadas


def cargar_config(ruta=RUTA_CONFIG):
    """Lee y valida config.json. Lanza ErrorLLM con un mensaje claro si falla."""
    if not os.path.exists(ruta):
        raise ErrorLLM(f"No se encuentra el archivo de configuracion: {ruta}")

    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            config = json.load(archivo)
    except json.JSONDecodeError as exc:
        raise ErrorLLM(f"El archivo {ruta} no es un JSON valido: {exc}") from exc
    except OSError as exc:
        raise ErrorLLM(f"No se pudo leer {ruta}: {exc}") from exc

    if not isinstance(config, dict):
        raise ErrorLLM(f"El contenido de {ruta} debe ser un objeto JSON.")

    proveedores = config.get("proveedores")
    if not isinstance(proveedores, dict) or not proveedores:
        raise ErrorLLM(f"Falta la seccion 'proveedores' en {ruta} o esta vacia.")

    por_defecto = config.get("proveedor_por_defecto")
    if por_defecto not in proveedores:
        raise ErrorLLM(
            f"'proveedor_por_defecto' ({por_defecto!r}) no existe en 'proveedores'. "
            f"Disponibles: {', '.join(sorted(proveedores))}"
        )

    for nombre, datos in proveedores.items():
        if not isinstance(datos, dict):
            raise ErrorLLM(f"La configuracion del proveedor '{nombre}' debe ser un objeto.")
        for campo in ("tipo", "modelo", "url", "variable_api_key"):
            if not datos.get(campo):
                raise ErrorLLM(f"Al proveedor '{nombre}' le falta el campo '{campo}' en {ruta}.")

    return config


def listar_proveedores(config):
    """Nombres de proveedores configurados, ordenados."""
    return sorted(config["proveedores"])


def tiene_api_key(nombre, config):
    """True si la variable de entorno con la clave de ese proveedor esta definida."""
    datos = config["proveedores"].get(nombre)
    if not datos:
        return False
    return bool(os.environ.get(datos.get("variable_api_key", "")))


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _peticion_json(url, cabeceras, cuerpo, timeout):
    """POST de JSON y respuesta decodificada como dict. Unico punto de salida HTTP."""
    datos = json.dumps(cuerpo).encode("utf-8")
    cabeceras = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
        **cabeceras,
    }
    peticion = urllib.request.Request(url, data=datos, headers=cabeceras, method="POST")

    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            texto = respuesta.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        # El cuerpo del error es donde los proveedores explican el fallo real.
        detalle = ""
        try:
            detalle = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:  # noqa: BLE001 - el detalle es opcional
            pass
        mensaje = f"La API respondio {exc.code} ({exc.reason})."
        if detalle:
            mensaje += f" Detalle: {detalle[:800]}"
        raise ErrorLLM(mensaje) from exc
    except TimeoutError as exc:
        raise ErrorLLM(f"Tiempo de espera agotado ({timeout}s) al llamar a {url}") from exc
    except urllib.error.URLError as exc:
        raise ErrorLLM(f"No se pudo conectar con {url}: {exc.reason}") from exc

    try:
        return json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ErrorLLM(f"La API devolvio una respuesta que no es JSON: {texto[:300]}") from exc


# ---------------------------------------------------------------------------
# Proveedores
# ---------------------------------------------------------------------------

class Proveedor:
    """Base comun. El historial se recibe siempre en formato interno neutro:

        [{"rol": "usuario" | "asistente", "texto": "..."}]

    Cada subclase lo traduce al formato que espera su API.
    """

    def __init__(self, nombre, config_proveedor, api_key, timeout=60, max_tokens=4096):
        self.nombre = nombre
        self.config = config_proveedor
        self.api_key = api_key
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.modelo = config_proveedor["modelo"]
        self.url = config_proveedor["url"]

    def enviar(self, mensajes, sistema=None):
        raise NotImplementedError

    def __str__(self):
        return f"{self.nombre} ({self.modelo})"


class ProveedorOpenAI(Proveedor):
    """Formato /v1/chat/completions. Sirve para OpenAI y para Mammouth AI."""

    def enviar(self, mensajes, sistema=None):
        historial = []
        if sistema:
            historial.append({"role": "system", "content": sistema})
        for mensaje in mensajes:
            rol = "assistant" if mensaje["rol"] == "asistente" else "user"
            historial.append({"role": rol, "content": mensaje["texto"]})

        # Los modelos recientes de OpenAI usan 'max_completion_tokens'; las APIs
        # compatibles mas antiguas (y Mammouth) esperan 'max_tokens'. Configurable.
        campo_tokens = self.config.get("campo_max_tokens", "max_completion_tokens")
        cuerpo = {
            "model": self.modelo,
            "messages": historial,
            campo_tokens: self.max_tokens,
        }
        cabeceras = {"Authorization": f"Bearer {self.api_key}"}
        respuesta = _peticion_json(self.url, cabeceras, cuerpo, self.timeout)

        try:
            return respuesta["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ErrorLLM(
                f"Respuesta inesperada de {self.nombre}: {json.dumps(respuesta)[:400]}"
            ) from exc


class ProveedorAnthropic(Proveedor):
    """Formato /v1/messages: 'system' va aparte y 'max_tokens' es obligatorio."""

    def enviar(self, mensajes, sistema=None):
        historial = [
            {
                "role": "assistant" if m["rol"] == "asistente" else "user",
                "content": m["texto"],
            }
            for m in mensajes
        ]

        cuerpo = {
            "model": self.modelo,
            "max_tokens": self.max_tokens,
            "messages": historial,
        }
        if sistema:
            cuerpo["system"] = sistema

        cabeceras = {
            "x-api-key": self.api_key,
            "anthropic-version": self.config.get("version_api", "2023-06-01"),
        }
        respuesta = _peticion_json(self.url, cabeceras, cuerpo, self.timeout)

        try:
            partes = [b["text"] for b in respuesta["content"] if b.get("type") == "text"]
        except (KeyError, TypeError) as exc:
            raise ErrorLLM(
                f"Respuesta inesperada de {self.nombre}: {json.dumps(respuesta)[:400]}"
            ) from exc
        if not partes:
            raise ErrorLLM(f"{self.nombre} no devolvio texto en la respuesta.")
        return "".join(partes)


class ProveedorGemini(Proveedor):
    """Formato generateContent: 'contents' con partes y rol 'model'."""

    def enviar(self, mensajes, sistema=None):
        contenidos = [
            {
                "role": "model" if m["rol"] == "asistente" else "user",
                "parts": [{"text": m["texto"]}],
            }
            for m in mensajes
        ]

        cuerpo = {
            "contents": contenidos,
            "generationConfig": {"maxOutputTokens": self.max_tokens},
        }
        if sistema:
            cuerpo["systemInstruction"] = {"parts": [{"text": sistema}]}

        url = f"{self.url.rstrip('/')}/models/{self.modelo}:generateContent"
        cabeceras = {"x-goog-api-key": self.api_key}
        respuesta = _peticion_json(url, cabeceras, cuerpo, self.timeout)

        try:
            partes = respuesta["candidates"][0]["content"]["parts"]
            texto = "".join(p["text"] for p in partes if "text" in p)
        except (KeyError, IndexError, TypeError) as exc:
            raise ErrorLLM(
                f"Respuesta inesperada de {self.nombre}: {json.dumps(respuesta)[:400]}"
            ) from exc
        if not texto:
            raise ErrorLLM(f"{self.nombre} no devolvio texto en la respuesta.")
        return texto


TIPOS = {
    "openai": ProveedorOpenAI,
    "anthropic": ProveedorAnthropic,
    "gemini": ProveedorGemini,
}


def obtener_proveedor(nombre, config):
    """Construye el proveedor pedido a partir de la configuracion cargada."""
    proveedores = config["proveedores"]
    if nombre not in proveedores:
        raise ErrorLLM(
            f"El proveedor '{nombre}' no esta configurado. "
            f"Disponibles: {', '.join(listar_proveedores(config))}"
        )

    datos = proveedores[nombre]
    tipo = datos["tipo"]
    if tipo not in TIPOS:
        raise ErrorLLM(
            f"Tipo de API desconocido '{tipo}' en el proveedor '{nombre}'. "
            f"Tipos validos: {', '.join(sorted(TIPOS))}"
        )

    variable = datos["variable_api_key"]
    api_key = os.environ.get(variable)
    if not api_key:
        raise ErrorLLM(
            f"Falta la API key de '{nombre}': define la variable {variable} "
            f"en el archivo .env (usa .env.example como plantilla)."
        )

    return TIPOS[tipo](
        nombre=nombre,
        config_proveedor=datos,
        api_key=api_key,
        timeout=config.get("timeout_segundos", 60),
        max_tokens=config.get("max_tokens", 4096),
    )
