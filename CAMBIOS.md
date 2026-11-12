# Intranet Patagonia – mejoras

Se mantiene: logo (config/logo.png), título "Patagonia", tipografía, foto de fondo y el mismo formato de services.yaml / settings.yaml (los archivos viejos siguen funcionando).

Nuevo, siguiendo la línea de patagonia-ar.com:
- Barra negra de avisos arriba (settings.yaml → announcement).
- Encabezado con la foto de campaña, logo, saludo según la hora y fecha.
- Buscador de sitios: escribí para filtrar, Enter abre el primero, la tecla "/" lo enfoca, Esc lo limpia.
- Menú de áreas fijo (LOCAL, ADMINISTRACIÓN, DEPÓSITO…) que marca la sección visible.
- Sitios como tarjetas blancas; al pasar el mouse se ponen negras (como los botones del sitio público).
- Opcional por sitio: description (texto corto) e icon (emoji). Se muestra la dirección de cada sitio (show_address).
- Pie negro con texto de marca y enlaces (footer_text, footer, footer_links).
- Mejor lectura en celulares, navegación con teclado y accesibilidad.
- nginx: compresión, cabeceras de seguridad y caché de la librería.

Cambio de comportamiento: por defecto los sitios se abren en pestaña nueva (settings.yaml → target: _blank). Para volver al comportamiento anterior, borrá esa línea.

Despliegue: igual que antes → docker compose up -d --build
