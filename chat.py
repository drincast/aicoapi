"""Interfaz de consola: ciclo de entrada del usuario y respuesta del LLM.

Uso:  python chat.py

Mantiene el historial de la conversacion en memoria y lo reenvia en cada turno,
de modo que el modelo recuerda lo hablado. Escribe /ayuda para ver los comandos.
"""

import sys

from conexion import (
    LLMError,
    load_config,
    load_env,
    list_providers,
    get_provider,
    has_api_key,
)

HELP = """
Comandos disponibles:
  /ayuda                 muestra esta ayuda
  /estado                proveedor y modelo activos, y turnos en memoria
  /proveedores           lista los proveedores configurados
  /proveedor <nombre>    cambia de proveedor (limpia el historial)
  /modelo <nombre>       cambia el modelo del proveedor actual
  /limpiar               borra el historial de la conversacion
  /salir                 termina el programa

Cualquier otro texto se envia al modelo.
"""


def print_response(provider, text):
    print(f"\n{provider.name}> {text}\n")


def main():
    load_env()

    try:
        config = load_config()
    except LLMError as exc:
        print(f"Error de configuracion: {exc}")
        return 1

    # Si el proveedor por defecto no se puede usar (por ejemplo, falta su clave),
    # se arranca igualmente sin proveedor activo: asi se puede cambiar a otro con
    # /proveedor en vez de tener que editar config.json y volver a lanzar.
    startup_warning = ""
    try:
        provider = get_provider(config["proveedor_por_defecto"], config)
    except LLMError as exc:
        provider = None
        startup_warning = str(exc)

    system = config.get("instruccion_sistema")
    history = []

    print("=" * 60)
    print("  aicoapi - cliente de consola para APIs de LLM")
    if provider:
        print(f"  Proveedor activo: {provider}")
    else:
        print("  Sin proveedor activo")
    print("=" * 60)

    if startup_warning:
        print(f"\nAviso: {startup_warning}")
        with_key = [n for n in list_providers(config) if has_api_key(n, config)]
        if with_key:
            print(f"Proveedores con clave disponible: {', '.join(with_key)}")
            print("Elige uno con:  /proveedor <nombre>")
        else:
            print("Ningun proveedor tiene su clave definida. Revisa el archivo .env")

    print(HELP)

    while True:
        try:
            user_input = input("tu> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.")
            return 0

        if not user_input:
            continue

        # --- Comandos -----------------------------------------------------
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            command = parts[0].lower()
            argument = parts[1].strip() if len(parts) > 1 else ""

            if command == "/salir":
                print("Hasta luego.")
                return 0

            if command == "/ayuda":
                print(HELP)
                continue

            if command == "/estado":
                if provider:
                    print(
                        f"Proveedor: {provider.name} | Modelo: {provider.model} | "
                        f"Mensajes en historial: {len(history)}"
                    )
                else:
                    print(
                        "Sin proveedor activo. Elige uno con /proveedor <nombre> | "
                        f"Mensajes en historial: {len(history)}"
                    )
                continue

            if command == "/proveedores":
                active = provider.name if provider else None
                for name in list_providers(config):
                    if name == active:
                        mark = " (activo)"
                    elif not has_api_key(name, config):
                        mark = f" (sin clave: falta {config['proveedores'][name]['variable_api_key']})"
                    else:
                        mark = ""
                    print(f"  - {name}: {config['proveedores'][name]['modelo']}{mark}")
                continue

            if command == "/proveedor":
                if not argument:
                    print("Uso: /proveedor <nombre>. Ver /proveedores")
                    continue
                try:
                    provider = get_provider(argument, config)
                except LLMError as exc:
                    print(f"Error: {exc}")
                    continue
                history.clear()
                print(f"Proveedor cambiado a {provider}. Historial limpiado.")
                continue

            if command == "/modelo":
                if not provider:
                    print("No hay proveedor activo. Usa /proveedor <nombre> primero.")
                    continue
                if not argument:
                    print("Uso: /modelo <nombre>")
                    continue
                provider.model = argument
                print(f"Modelo cambiado a {argument} en el proveedor {provider.name}.")
                continue

            if command == "/limpiar":
                history.clear()
                print("Historial limpiado.")
                continue

            print(f"Comando desconocido: {command}. Escribe /ayuda")
            continue

        # --- Turno normal -------------------------------------------------
        if not provider:
            print("No hay proveedor activo. Usa /proveedor <nombre> (ver /proveedores).\n")
            continue

        # Se envia el historial mas el mensaje nuevo, pero este solo se guarda
        # si la llamada tiene exito: asi el historial nunca queda desalineado.
        turn = history + [{"rol": "usuario", "texto": user_input}]

        print("...pensando...", end="", flush=True)
        try:
            response = provider.send(turn, system=system)
        except LLMError as exc:
            print("\r" + " " * 15 + "\r", end="")
            print(f"Error: {exc}\n")
            continue
        except KeyboardInterrupt:
            print("\r" + " " * 15 + "\r", end="")
            print("Peticion cancelada.\n")
            continue
        print("\r" + " " * 15 + "\r", end="")

        history.append({"rol": "usuario", "texto": user_input})
        history.append({"rol": "asistente", "texto": response})
        print_response(provider, response)


if __name__ == "__main__":
    sys.exit(main())
