# Checklist de desarrollo — aicoapi

## v1 — cliente de consola con historial en memoria

- [x] 1. Estructura de carpeta y archivos base
- [x] 2. `config.json` + `.env.example` + `.gitignore`
- [x] 3. `conexion.py`: `cargar_env` / `cargar_config`
- [x] 4. `conexion.py`: `_peticion_json` + `ErrorLLM`
- [x] 5. `conexion.py`: `ProveedorOpenAI` (sirve tambien para Mammouth)
- [x] 6. `conexion.py`: `ProveedorAnthropic`
- [x] 7. `conexion.py`: `ProveedorGemini`
- [x] 8. `conexion.py`: fabrica `obtener_proveedor`
- [x] 9. `chat.py`: bucle, comandos e historial
- [x] 10. `README.md` con instrucciones de uso
- [x] 11. Prueba sin claves: los errores salen claros, sin traceback
- [x] 12. Prueba real con al menos un proveedor
      (Mammouth + `kimi-k2.6`: respuesta correcta y historial recordado entre turnos)
- [x] 12b. Cabecera `User-Agent` propia en `_peticion_json`: sin ella, Cloudflare
      devuelve `403 error code: 1010` al User-Agent por defecto de urllib.
- [x] 12c. Arranque tolerante: si el proveedor por defecto no tiene clave, el programa
      arranca igualmente, avisa, lista los proveedores con clave y deja cambiar con
      `/proveedor`. `/proveedores` marca cuales no tienen clave.
- [ ] 12d. Prueba real de los otros tres proveedores (falta API key de cada uno)

## v2 — pendiente

- [ ] 13. Persistencia de conversaciones en SQLite
      (`conversacion(id, inicio, proveedor, modelo)` y
       `mensaje(id, conversacion_id, orden, rol, texto, creado)`;
       comandos `/guardar`, `/historial`, `/cargar <id>`)
- [ ] 14. Streaming token a token (`stream: true` + parseo SSE por proveedor)

## Ideas para mas adelante

- [ ] Revisar opciones de seguridad para las claves (DPAPI / keyring de Windows)
- [ ] Contador de tokens y coste aproximado por conversacion
- [ ] Reintentos automaticos ante errores 429 / 5xx
