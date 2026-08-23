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
    "Luego hasta ;)",    
    # Ingles, casuales
    "Bye!",
    "See you later.",
    "Take care!",
    "Catch you later.",
    "bit off",
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
