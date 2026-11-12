# Intranet Patagonia – mejoras

Se mantiene: logo (config/logo.png), título "Patagonia", tipografía, foto de fondo y el mismo formato de services.yaml / settings.yaml.

## Diseño (línea de patagonia-ar.com)
- Barra negra de avisos arriba (settings.yaml → announcement).
- Foto de campaña de fondo en toda la página, saludo según la hora y fecha.
- Tarjetas translúcidas (vidrio esmerilado); al pasar el mouse se ponen blancas, se elevan y las cruza un brillo. No se muestran las direcciones.
- Buscador de sitios ("/" lo enfoca, Enter abre el primero, Esc limpia).
- Menú de áreas fijo y pie de página translúcido.

## Cargar sitios desde la web (NUEVO)
- Abajo a la derecha está el botón "🔒 Editar": pide la clave y recién ahí aparecen los botones de edición,
  solo en las áreas que esa clave puede modificar. "Salir de edición" vuelve al modo consulta.
- Cada área tiene una tarjeta "+ Agregar": nombre, link, descripción, ícono y si se abre en pestaña nueva.
- Al pasar el mouse por un sitio aparecen: ← → (cambiar orden), ✎ (editar) y ✕ (borrar).
- Botón "+ Nueva área" al final. Un área vacía muestra "Borrar área".
- Todo se guarda en config/services.yaml (se puede seguir editando a mano).
- Antes de cada cambio se guarda una copia de respaldo (últimas 50) en el volumen intranet-backups.

### Claves (docker-compose.yml → servicio intranet-api)
- ADMIN_PIN: clave general. Sirve para todas las áreas y es la única que crea o borra áreas.
  ¡Cambiá "cambiar-esta-clave" antes de desplegar!
- AREA_PINS: clave propia de cada área, ej. "ADMINISTRACIÓN=1111;DEPÓSITO=2222;MAYORISTA=3333".
  Cada área edita solo lo suyo. Un área sin clave propia se edita con la clave general.
- Si dejás las dos vacías, cualquiera en la red puede editar (no recomendado).
- La clave se pide al entrar en modo edición y se recuerda hasta cerrar el navegador.
- Para confirmar qué claves tomó el servidor: docker logs intranet-api (primera línea).
- Después de cambiar claves: docker compose up -d

## Despliegue
1. IMPORTANTE: antes del primer despliegue, poné TU services.yaml actual dentro de la carpeta config
   (el que viene acá es de ejemplo). La primera vez se copia al volumen; después manda lo que se cargue desde la web.
2. docker compose up -d --build
3. Para editar el archivo a mano en el servidor:
   docker exec -it intranet-api vi /data/services.yaml
   Para ver los respaldos: docker exec intranet-api ls /backups

Si se despliega sin el servicio intranet-api, la página funciona igual pero sin los botones de edición.
