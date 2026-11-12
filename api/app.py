"""
API mínima de la intranet Patagonia.
Lee y guarda config/services.yaml para que cada área administre sus sitios desde la web.
Sin dependencias salvo PyYAML. Guarda una copia de respaldo antes de cada cambio.
"""
import hmac, json, os, re, shutil, threading, time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import yaml

CONFIG_DIR = os.environ.get("CONFIG_DIR", "/data")
SEED_DIR = os.environ.get("SEED_DIR", "/seed")
BACKUP_DIR = os.environ.get("BACKUP_DIR", "/backups")
SERVICES = os.path.join(CONFIG_DIR, "services.yaml")
KEEP_BACKUPS = int(os.environ.get("KEEP_BACKUPS", "50"))

ADMIN_PIN = os.environ.get("ADMIN_PIN", "").strip()
# AREA_PINS="ADMINISTRACIÓN=1111;DEPÓSITO=2222"
AREA_PINS = {}
for part in os.environ.get("AREA_PINS", "").split(";"):
    if "=" in part:
        k, v = part.split("=", 1)
        if k.strip() and v.strip():
            AREA_PINS[k.strip().upper()] = v.strip()

HEADER = """# Intranet Patagonia - sitios por área
# Este archivo se puede editar a mano o desde la web (botón "Agregar").
#
# - NOMBRE DEL ÁREA:
#     - Nombre del sitio:
#         href: http://direccion-del-sitio
#         description: Texto corto     # opcional
#         icon: "📦"                    # opcional (un emoji)
#         target: _blank               # opcional (_self = misma pestaña)

"""

LOCK = threading.Lock()
FAILS = {}  # ip -> (cantidad, desde)

HREF_RE = re.compile(r"^(https?://|/)", re.I)


class ApiError(Exception):
    def __init__(self, status, msg):
        super().__init__(msg)
        self.status, self.msg = status, msg


# ---------- archivo ----------
def seed():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if os.path.isdir(SEED_DIR):
        for f in os.listdir(SEED_DIR):
            dst = os.path.join(CONFIG_DIR, f)
            if not os.path.exists(dst):
                shutil.copy2(os.path.join(SEED_DIR, f), dst)


def load():
    if not os.path.exists(SERVICES):
        return []
    with open(SERVICES, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or []
    if not isinstance(data, list):
        raise ApiError(500, "services.yaml no tiene el formato esperado")
    return data


def save(data):
    if os.path.exists(SERVICES):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        shutil.copy2(SERVICES, os.path.join(BACKUP_DIR, f"services-{stamp}.yaml"))
        olds = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith("services-"))
        for f in olds[:-KEEP_BACKUPS]:
            os.remove(os.path.join(BACKUP_DIR, f))
    tmp = SERVICES + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(HEADER)
        for group in data:
            fh.write(yaml.safe_dump([group], allow_unicode=True, sort_keys=False,
                                    default_flow_style=False, width=1000, indent=2))
            fh.write("\n")
    os.replace(tmp, SERVICES)


def find_area(data, area):
    for g in data:
        if isinstance(g, dict) and area in g:
            if g[area] is None:
                g[area] = []
            return g
    raise ApiError(404, f"No existe el área {area}")


def site_name(item):
    return next(iter(item)) if isinstance(item, dict) and item else None


# ---------- validación ----------
def clean_site(body):
    name = str(body.get("name", "")).strip()
    href = str(body.get("href", "")).strip()
    desc = str(body.get("description", "") or "").strip()
    icon = str(body.get("icon", "") or "").strip()
    target = body.get("target") or "_blank"
    if not name or len(name) > 60:
        raise ApiError(400, "El nombre es obligatorio (máximo 60 caracteres)")
    if not HREF_RE.match(href) or len(href) > 2000 or any(c in href for c in " \n\r\t\"<>"):
        raise ApiError(400, "El link tiene que empezar con http:// o https://")
    if len(desc) > 160:
        raise ApiError(400, "La descripción puede tener hasta 160 caracteres")
    if len(icon) > 8:
        raise ApiError(400, "El ícono tiene que ser un solo emoji")
    if target not in ("_blank", "_self"):
        target = "_blank"
    cfg = {"href": href}
    if desc:
        cfg["description"] = desc
    if icon:
        cfg["icon"] = icon
    cfg["target"] = target
    return name, cfg


def clean_area(name):
    name = str(name or "").strip().upper()
    if not name or len(name) > 40:
        raise ApiError(400, "El nombre del área es obligatorio (máximo 40 caracteres)")
    return name


# ---------- permisos ----------
def check_pin(ip, area, pin, admin_only=False):
    n, since = FAILS.get(ip, (0, 0))
    if n >= 8 and time.time() - since < 300:
        raise ApiError(429, "Demasiados intentos. Probá de nuevo en 5 minutos")
    needed = [] if admin_only else ([AREA_PINS[area.upper()]] if area and area.upper() in AREA_PINS else [])
    if ADMIN_PIN:
        needed.append(ADMIN_PIN)
    if not needed:
        return  # sin claves configuradas: edición libre
    pin = str(pin or "")
    if any(hmac.compare_digest(pin, p) for p in needed):
        FAILS.pop(ip, None)
        return
    FAILS[ip] = (n + 1, since if n else time.time())
    raise ApiError(401, "Clave incorrecta" if pin else "Ingresá la clave del área")


def needs_pin(area=None, admin_only=False):
    if ADMIN_PIN:
        return True
    return (not admin_only) and bool(area and area.upper() in AREA_PINS)


# ---------- acciones ----------
def handle(method, path, body, ip):
    if method == "GET" and path == "/api/health":
        return {"ok": True}
    if method == "GET" and path == "/api/meta":
        areas = [site_name(g) for g in load() if isinstance(g, dict)]
        return {"ok": True,
                "pin": {a: needs_pin(a) for a in areas},
                "pin_admin": needs_pin(admin_only=True)}

    with LOCK:
        data = load()
        if method == "POST" and path == "/api/sites":
            area = str(body.get("area", ""))
            check_pin(ip, area, body.get("pin"))
            g = find_area(data, area)
            name, cfg = clean_site(body)
            if any(site_name(i) == name for i in g[area]):
                raise ApiError(409, f"Ya existe un sitio llamado {name} en {area}")
            g[area].append({name: cfg})
        elif method in ("PUT", "DELETE") and path == "/api/sites":
            area = str(body.get("area", ""))
            check_pin(ip, area, body.get("pin"))
            g = find_area(data, area)
            idx, orig = body.get("index"), body.get("original")
            if not isinstance(idx, int) or not (0 <= idx < len(g[area])) or site_name(g[area][idx]) != orig:
                raise ApiError(409, "Alguien modificó esta área mientras tanto. Recargá la página")
            if method == "DELETE":
                g[area].pop(idx)
            else:
                name, cfg = clean_site(body)
                if name != orig and any(site_name(i) == name for i in g[area]):
                    raise ApiError(409, f"Ya existe un sitio llamado {name} en {area}")
                g[area][idx] = {name: cfg}
                move = body.get("move")
                if move in (-1, 1) and 0 <= idx + move < len(g[area]):
                    g[area][idx], g[area][idx + move] = g[area][idx + move], g[area][idx]
        elif method == "POST" and path == "/api/areas":
            check_pin(ip, None, body.get("pin"), admin_only=True)
            name = clean_area(body.get("name"))
            if any(isinstance(x, dict) and name in x for x in data):
                raise ApiError(409, f"Ya existe el área {name}")
            data.append({name: []})
        elif method == "DELETE" and path == "/api/areas":
            check_pin(ip, None, body.get("pin"), admin_only=True)
            area = str(body.get("name", ""))
            g = find_area(data, area)
            if g[area]:
                raise ApiError(409, "Primero borrá los sitios del área")
            data.remove(g)
        else:
            raise ApiError(404, "No encontrado")
        save(data)
        return {"ok": True}


class Handler(BaseHTTPRequestHandler):
    server_version = "intranet-api"

    def _go(self, method):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > 20000:
                raise ApiError(413, "Pedido demasiado grande")
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw or b"{}")
            except ValueError:
                raise ApiError(400, "Datos inválidos")
            if not isinstance(body, dict):
                raise ApiError(400, "Datos inválidos")
            ip = (self.headers.get("X-Real-IP") or self.client_address[0])
            out, status = handle(method, urlparse(self.path).path, body, ip), 200
        except ApiError as e:
            out, status = {"ok": False, "error": e.msg}, e.status
        except Exception as e:  # noqa
            out, status = {"ok": False, "error": "Error interno: " + str(e)}, 500
        payload = json.dumps(out, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self): self._go("GET")
    def do_POST(self): self._go("POST")
    def do_PUT(self): self._go("PUT")
    def do_DELETE(self): self._go("DELETE")

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


if __name__ == "__main__":
    seed()
    print("Intranet API en :8000 | clave admin:", "sí" if ADMIN_PIN else "no",
          "| áreas con clave:", ", ".join(AREA_PINS) or "ninguna", flush=True)
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8000"))), Handler).serve_forever()
