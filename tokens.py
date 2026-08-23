"""Conteo de tokens de entrada/salida, sin depender de SDKs de proveedores.

Uso: from tokens import Usage, SessionTokens, estimate_tokens, estimate_messages

`Usage` representa el conteo de un turno (real, si la API lo devolvio, o
estimado por caracteres/palabras si no). `SessionTokens` acumula los `Usage`
de toda la sesion.
"""

from dataclasses import dataclass, field

CHARS_PER_TOKEN = 4
TOKENS_PER_WORD = 1.6
MESSAGE_OVERHEAD = 4


def estimate_tokens(text):
    """Estima tokens de un texto: promedio de la regla por caracteres y por
    palabras. Corrige el sesgo de la regla clasica (chars/4, pensada para
    ingles) cuando el texto esta en español.
    """
    if not text:
        return 0
    by_chars = len(text) / CHARS_PER_TOKEN
    by_words = len(text.split()) * TOKENS_PER_WORD
    return max(1, round((by_chars + by_words) / 2))


def estimate_messages(messages, system=None):
    """Estima tokens de una lista de mensajes en formato interno neutro
    ([{"role": ..., "text": ...}]), sumando un overhead fijo por mensaje
    (los delimitadores de rol que el texto plano no refleja).
    """
    total = 0
    if system:
        total += estimate_tokens(system) + MESSAGE_OVERHEAD
    for message in messages:
        total += estimate_tokens(message["text"]) + MESSAGE_OVERHEAD
    return total


@dataclass
class Usage:
    """Conteo de tokens de un turno."""

    input_tokens: int
    output_tokens: int
    estimated: bool = False

    @property
    def total(self):
        return self.input_tokens + self.output_tokens

    def __str__(self):
        prefix = "~" if self.estimated else ""
        return f"{prefix}{self.input_tokens} in / {prefix}{self.output_tokens} out"


@dataclass
class SessionTokens:
    """Acumulador de tokens de toda la sesion."""

    input_tokens: int = 0
    output_tokens: int = 0
    turns: int = 0
    last: Usage = None
    has_estimated: bool = field(default=False)

    def add(self, usage):
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.turns += 1
        self.last = usage
        if usage.estimated:
            self.has_estimated = True

    @property
    def total(self):
        return self.input_tokens + self.output_tokens

    def as_usage(self):
        return Usage(self.input_tokens, self.output_tokens, estimated=self.has_estimated)
