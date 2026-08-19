"""Capa de conexion a las APIs de LLM (OpenAI, Anthropic, Gemini, Mammouth, etc).

Esta capa no imprime nada por consola: solo lee configuracion, hace la peticion
HTTP y devuelve texto. Cualquier fallo se propaga como LLMError.

Solo usa la biblioteca estandar de Python: no requiere instalar dependencias.
"""

import json
import os
import urllib.error
import urllib.request

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

# Necesario: algunos proveedores estan detras de Cloudflare y devuelven 403
# (error 1010) al User-Agent por defecto de urllib ("Python-urllib/x.y").
USER_AGENT = "aicoapi/1.0"


class LLMError(Exception):
    """Error unico de esta capa, con mensaje legible para el usuario."""


# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------

def load_env(path=ENV_PATH):
    """Carga pares CLAVE=valor de un archivo .env dentro de os.environ.

    No pisa variables ya definidas en el entorno del sistema: estas tienen
    prioridad sobre el archivo. Si el archivo no existe, no hace nada.
    Devuelve la lista de claves cargadas.
    """
    loaded = []
    if not os.path.exists(path):
        return loaded

    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
                loaded.append(key)
    return loaded


def load_config(path=CONFIG_PATH):
    """Lee y valida config.json. Lanza LLMError con un mensaje claro si falla."""
    if not os.path.exists(path):
        raise LLMError(f"No se encuentra el archivo de configuracion: {path}")

    try:
        with open(path, "r", encoding="utf-8") as file:
            config = json.load(file)
    except json.JSONDecodeError as exc:
        raise LLMError(f"El archivo {path} no es un JSON valido: {exc}") from exc
    except OSError as exc:
        raise LLMError(f"No se pudo leer {path}: {exc}") from exc

    if not isinstance(config, dict):
        raise LLMError(f"El contenido de {path} debe ser un objeto JSON.")

    providers = config.get("proveedores")
    if not isinstance(providers, dict) or not providers:
        raise LLMError(f"Falta la seccion 'proveedores' en {path} o esta vacia.")

    default_provider = config.get("proveedor_por_defecto")
    if default_provider not in providers:
        raise LLMError(
            f"'proveedor_por_defecto' ({default_provider!r}) no existe en 'proveedores'. "
            f"Disponibles: {', '.join(sorted(providers))}"
        )

    for name, data in providers.items():
        if not isinstance(data, dict):
            raise LLMError(f"La configuracion del proveedor '{name}' debe ser un objeto.")
        for field in ("tipo", "modelo", "url", "variable_api_key"):
            if not data.get(field):
                raise LLMError(f"Al proveedor '{name}' le falta el campo '{field}' en {path}.")

    return config


def list_providers(config):
    """Nombres de proveedores configurados, ordenados."""
    return sorted(config["proveedores"])


def has_api_key(name, config):
    """True si la variable de entorno con la clave de ese proveedor esta definida."""
    data = config["proveedores"].get(name)
    if not data:
        return False
    return bool(os.environ.get(data.get("variable_api_key", "")))


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _json_request(url, headers, body, timeout):
    """POST de JSON y respuesta decodificada como dict. Unico punto de salida HTTP."""
    data = json.dumps(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
        **headers,
    }
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        # El cuerpo del error es donde los proveedores explican el fallo real.
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:  # noqa: BLE001 - el detalle es opcional
            pass
        message = f"La API respondio {exc.code} ({exc.reason})."
        if detail:
            message += f" Detalle: {detail[:800]}"
        raise LLMError(message) from exc
    except TimeoutError as exc:
        raise LLMError(f"Tiempo de espera agotado ({timeout}s) al llamar a {url}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"No se pudo conectar con {url}: {exc.reason}") from exc

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(f"La API devolvio una respuesta que no es JSON: {text[:300]}") from exc


# ---------------------------------------------------------------------------
# Proveedores
# ---------------------------------------------------------------------------

class Provider:
    """Base comun. El historial se recibe siempre en formato interno neutro:

        [{"rol": "usuario" | "asistente", "texto": "..."}]

    Cada subclase lo traduce al formato que espera su API.
    """

    def __init__(self, name, provider_config, api_key, timeout=60, max_tokens=4096):
        self.name = name
        self.config = provider_config
        self.api_key = api_key
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.model = provider_config["modelo"]
        self.url = provider_config["url"]

    def send(self, messages, system=None):
        raise NotImplementedError

    def __str__(self):
        return f"{self.name} ({self.model})"


class OpenAIProvider(Provider):
    """Formato /v1/chat/completions. Sirve para OpenAI y para Mammouth AI."""

    def send(self, messages, system=None):
        history = []
        if system:
            history.append({"role": "system", "content": system})
        for message in messages:
            role = "assistant" if message["rol"] == "asistente" else "user"
            history.append({"role": role, "content": message["texto"]})

        # Los modelos recientes de OpenAI usan 'max_completion_tokens'; las APIs
        # compatibles mas antiguas (y Mammouth) esperan 'max_tokens'. Configurable.
        tokens_field = self.config.get("campo_max_tokens", "max_completion_tokens")
        body = {
            "model": self.model,
            "messages": history,
            tokens_field: self.max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = _json_request(self.url, headers, body, self.timeout)

        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(
                f"Respuesta inesperada de {self.name}: {json.dumps(response)[:400]}"
            ) from exc


class AnthropicProvider(Provider):
    """Formato /v1/messages: 'system' va aparte y 'max_tokens' es obligatorio."""

    def send(self, messages, system=None):
        history = [
            {
                "role": "assistant" if m["rol"] == "asistente" else "user",
                "content": m["texto"],
            }
            for m in messages
        ]

        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": history,
        }
        if system:
            body["system"] = system

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.config.get("version_api", "2023-06-01"),
        }
        response = _json_request(self.url, headers, body, self.timeout)

        try:
            parts = [b["text"] for b in response["content"] if b.get("type") == "text"]
        except (KeyError, TypeError) as exc:
            raise LLMError(
                f"Respuesta inesperada de {self.name}: {json.dumps(response)[:400]}"
            ) from exc
        if not parts:
            raise LLMError(f"{self.name} no devolvio texto en la respuesta.")
        return "".join(parts)


class GeminiProvider(Provider):
    """Formato generateContent: 'contents' con partes y rol 'model'."""

    def send(self, messages, system=None):
        contents = [
            {
                "role": "model" if m["rol"] == "asistente" else "user",
                "parts": [{"text": m["texto"]}],
            }
            for m in messages
        ]

        body = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": self.max_tokens},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        url = f"{self.url.rstrip('/')}/models/{self.model}:generateContent"
        headers = {"x-goog-api-key": self.api_key}
        response = _json_request(url, headers, body, self.timeout)

        try:
            parts = response["candidates"][0]["content"]["parts"]
            text = "".join(p["text"] for p in parts if "text" in p)
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(
                f"Respuesta inesperada de {self.name}: {json.dumps(response)[:400]}"
            ) from exc
        if not text:
            raise LLMError(f"{self.name} no devolvio texto en la respuesta.")
        return text


TYPES = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
}


def get_provider(name, config):
    """Construye el proveedor pedido a partir de la configuracion cargada."""
    providers = config["proveedores"]
    if name not in providers:
        raise LLMError(
            f"El proveedor '{name}' no esta configurado. "
            f"Disponibles: {', '.join(list_providers(config))}"
        )

    data = providers[name]
    type_ = data["tipo"]
    if type_ not in TYPES:
        raise LLMError(
            f"Tipo de API desconocido '{type_}' en el proveedor '{name}'. "
            f"Tipos validos: {', '.join(sorted(TYPES))}"
        )

    variable = data["variable_api_key"]
    api_key = os.environ.get(variable)
    if not api_key:
        raise LLMError(
            f"Falta la API key de '{name}': define la variable {variable} "
            f"en el archivo .env (usa .env.example como plantilla)."
        )

    return TYPES[type_](
        name=name,
        provider_config=data,
        api_key=api_key,
        timeout=config.get("timeout_segundos", 60),
        max_tokens=config.get("max_tokens", 4096),
    )
