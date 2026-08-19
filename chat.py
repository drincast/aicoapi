"""Interfaz de consola: ciclo de entrada del usuario y respuesta del LLM.

Uso:  python chat.py

Mantiene el historial de la conversacion en memoria y lo reenvia en cada turno,
de modo que el modelo recuerda lo hablado. Escribe /ayuda para ver los comandos.
"""

import sys

from conexion import (
    ErrorLLM,
    cargar_config,
    cargar_env,
    listar_proveedores,
    obtener_proveedor,
    tiene_api_key,
)

AYUDA = """
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


def imprimir_respuesta(proveedor, texto):
    print(f"\n{proveedor.nombre}> {texto}\n")


def main():
    cargar_env()

    try:
        config = cargar_config()
    except ErrorLLM as exc:
        print(f"Error de configuracion: {exc}")
        return 1

    # Si el proveedor por defecto no se puede usar (por ejemplo, falta su clave),
    # se arranca igualmente sin proveedor activo: asi se puede cambiar a otro con
    # /proveedor en vez de tener que editar config.json y volver a lanzar.
    aviso_inicio = ""
    try:
        proveedor = obtener_proveedor(config["proveedor_por_defecto"], config)
    except ErrorLLM as exc:
        proveedor = None
        aviso_inicio = str(exc)

    sistema = config.get("instruccion_sistema")
    historial = []

    print("=" * 60)
    print("  aicoapi - cliente de consola para APIs de LLM")
    if proveedor:
        print(f"  Proveedor activo: {proveedor}")
    else:
        print("  Sin proveedor activo")
    print("=" * 60)

    if aviso_inicio:
        print(f"\nAviso: {aviso_inicio}")
        con_clave = [n for n in listar_proveedores(config) if tiene_api_key(n, config)]
        if con_clave:
            print(f"Proveedores con clave disponible: {', '.join(con_clave)}")
            print("Elige uno con:  /proveedor <nombre>")
        else:
            print("Ningun proveedor tiene su clave definida. Revisa el archivo .env")

    print(AYUDA)

    while True:
        try:
            entrada = input("tu> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.")
            return 0

        if not entrada:
            continue

        # --- Comandos -----------------------------------------------------
        if entrada.startswith("/"):
            partes = entrada.split(maxsplit=1)
            comando = partes[0].lower()
            argumento = partes[1].strip() if len(partes) > 1 else ""

            if comando == "/salir":
                print("Hasta luego.")
                return 0

            if comando == "/ayuda":
                print(AYUDA)
                continue

            if comando == "/estado":
                if proveedor:
                    print(
                        f"Proveedor: {proveedor.nombre} | Modelo: {proveedor.modelo} | "
                        f"Mensajes en historial: {len(historial)}"
                    )
                else:
                    print(
                        "Sin proveedor activo. Elige uno con /proveedor <nombre> | "
                        f"Mensajes en historial: {len(historial)}"
                    )
                continue

            if comando == "/proveedores":
                activo = proveedor.nombre if proveedor else None
                for nombre in listar_proveedores(config):
                    if nombre == activo:
                        marca = " (activo)"
                    elif not tiene_api_key(nombre, config):
                        marca = f" (sin clave: falta {config['proveedores'][nombre]['variable_api_key']})"
                    else:
                        marca = ""
                    print(f"  - {nombre}: {config['proveedores'][nombre]['modelo']}{marca}")
                continue

            if comando == "/proveedor":
                if not argumento:
                    print("Uso: /proveedor <nombre>. Ver /proveedores")
                    continue
                try:
                    proveedor = obtener_proveedor(argumento, config)
                except ErrorLLM as exc:
                    print(f"Error: {exc}")
                    continue
                historial.clear()
                print(f"Proveedor cambiado a {proveedor}. Historial limpiado.")
                continue

            if comando == "/modelo":
                if not proveedor:
                    print("No hay proveedor activo. Usa /proveedor <nombre> primero.")
                    continue
                if not argumento:
                    print("Uso: /modelo <nombre>")
                    continue
                proveedor.modelo = argumento
                print(f"Modelo cambiado a {argumento} en el proveedor {proveedor.nombre}.")
                continue

            if comando == "/limpiar":
                historial.clear()
                print("Historial limpiado.")
                continue

            print(f"Comando desconocido: {comando}. Escribe /ayuda")
            continue

        # --- Turno normal -------------------------------------------------
        if not proveedor:
            print("No hay proveedor activo. Usa /proveedor <nombre> (ver /proveedores).\n")
            continue

        # Se envia el historial mas el mensaje nuevo, pero este solo se guarda
        # si la llamada tiene exito: asi el historial nunca queda desalineado.
        turno = historial + [{"rol": "usuario", "texto": entrada}]

        print("...pensando...", end="", flush=True)
        try:
            respuesta = proveedor.enviar(turno, sistema=sistema)
        except ErrorLLM as exc:
            print("\r" + " " * 15 + "\r", end="")
            print(f"Error: {exc}\n")
            continue
        except KeyboardInterrupt:
            print("\r" + " " * 15 + "\r", end="")
            print("Peticion cancelada.\n")
            continue
        print("\r" + " " * 15 + "\r", end="")

        historial.append({"rol": "usuario", "texto": entrada})
        historial.append({"rol": "asistente", "texto": respuesta})
        imprimir_respuesta(proveedor, respuesta)


if __name__ == "__main__":
    sys.exit(main())
