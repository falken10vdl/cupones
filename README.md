# 🎟️ Sistema de Cupones para Eventos

Sistema sencillo para gestionar **cupones/vouchers con QR** en bares y eventos pequeños (50–500 personas). Pensado para correr en un laptop del local sin necesidad de infraestructura cloud.

---

## ✨ Características principales

- **Cupones firmados con HMAC-SHA256** — cada código lleva una firma criptográfica para evitar falsificaciones
- **Envío por email (Gmail SMTP)** — QR embebido directamente en el cuerpo del correo, listo para mostrar desde el teléfono móvil
- **App PWA para barmans** — instalable en el móvil como app nativa, sin pasar por ninguna tienda
- **Modo online** — cualquier barman puede validar cualquier cupón en tiempo real contra el servidor
- **Modo offline** — cada barman tiene sus cupones pre-asignados en caché local; puede validarlos sin conexión y la firma HMAC se verifica en el dispositivo
- **Sincronización automática** — al recuperar la conexión los canjes offline se sincronizan con el servidor; los conflictos se detectan y reportan
- **Panel de administración web** — gestión de eventos, barmans, generación masiva de cupones y monitor en tiempo real
- **Base de datos SQLite** — sin configuración extra, el archivo `coupons.db` se crea automáticamente al iniciar

---

## 🏗️ Arquitectura

```
Admin Panel (navegador) ──┐
                          ├──► FastAPI Server (Python) ──► SQLite (coupons.db)
Barman PWA (móvil)  ──────┘            │
                                  Gmail SMTP ──► Clientes (QR por email)
```

El servidor sirve tanto la API REST como los archivos estáticos del panel admin (`/admin/`) y la PWA del barman (`/barman/`).

---

## 📋 Requisitos previos

| Requisito | Versión mínima | Notas |
|-----------|----------------|-------|
| Windows | 10 / 11 (64-bit) | |
| Python | 3.10+ | Instalar desde python.org |
| Git | 2.x | Instalar desde git-scm.com |
| Cuenta Gmail | — | Con [contraseña de aplicación](https://support.google.com/accounts/answer/185833) habilitada |

> **Nota Gmail:** La contraseña de aplicación es un código de 16 caracteres que Google genera específicamente para apps de terceros. No uses tu contraseña normal de Google.

---

## 🖥️ Instalación en Windows (paso a paso)

### 1. Instalar Python

1. Ve a **https://www.python.org/downloads/** y descarga el instalador de Python 3.10 o superior.
2. Ejecuta el instalador. **Importante:** marca la opción **"Add Python to PATH"** antes de pulsar *Install Now*.
3. Verifica la instalación abriendo **PowerShell** o **Símbolo del sistema (cmd)** y ejecutando:

```cmd
python --version
pip --version
```

Ambos comandos deben mostrar un número de versión.

---

### 2. Instalar Git

1. Ve a **https://git-scm.com/download/win** y descarga el instalador.
2. Ejecuta el instalador; puedes dejar todas las opciones por defecto.
3. Verifica la instalación:

```cmd
git --version
```

---

### 3. Clonar el repositorio

Abre **PowerShell** o **cmd**, navega a la carpeta donde quieras guardar el proyecto y ejecuta:

```cmd
git clone https://github.com/falken10vdl/cupones.git
cd cupones
```

---

### 4. Crear un entorno virtual (recomendado)

```cmd
cd server
python -m venv venv
venv\Scripts\activate
```

Tras activar el entorno verás `(venv)` al inicio del prompt. Para desactivarlo usa `deactivate`.

---

### 5. Instalar dependencias

Con el entorno virtual activo:

```cmd
pip install -r requirements.txt
```

---

### 6. Configurar el entorno

```cmd
copy .env.example .env
```

Abre `.env` con el Bloc de notas o cualquier editor de texto y completa los valores (ver sección [Configuración del .env](#️-configuración-del-env) más abajo).

---

### 7. Iniciar el servidor principal

```cmd
python app.py
```

El servidor arranca en `http://localhost:8000` con recarga automática en modo desarrollo.

> **Firewall de Windows:** la primera vez puede aparecer un aviso del Firewall de Windows Defender. Pulsa *Permitir acceso* para que los móviles de la misma red puedan conectarse a la app de barman.

### 8. (Opcional) Iniciar la página de bienvenida

Abre otra ventana de **cmd** o **PowerShell**, activa de nuevo el entorno virtual y ejecuta:

```cmd
cd server
venv\Scripts\activate
python landing.py
```

Esto levanta un servidor en `http://localhost:8080` que muestra la **IP local del servidor** (para que los barmans sepan a qué dirección conectarse) y renderiza esta documentación en HTML.

---

### 9. Acceder a las interfaces

| Interfaz | URL |
|----------|-----|
| **Página de bienvenida** (IP + docs) | http://localhost:8080/ |
| Panel de administración | http://localhost:8000/admin/ |
| App barman (PWA) | http://localhost:8000/barman/ |
| Documentación API automática | http://localhost:8000/docs |

Para que los barmans accedan desde su móvil, usa la **IP local** del ordenador en lugar de `localhost`. Puedes ver tu IP local con:

```cmd
ipconfig
```

Busca la línea **Dirección IPv4** (p. ej. `192.168.1.50`) y pide a los barmans que abran `http://192.168.1.50:8000/barman/`.

---

## ⚙️ Configuración del `.env`

```dotenv
# Clave secreta para firmar los cupones con HMAC-SHA256.
# IMPORTANTE: cambia este valor por una cadena aleatoria larga en producción.
# Puedes generar una con: python -c "import secrets; print(secrets.token_hex(32))"
COUPON_SECRET_KEY=change-me-in-production-please

# Dirección de Gmail desde la que se enviarán los cupones.
GMAIL_USER=tu_correo@gmail.com

# Contraseña de aplicación de Google (16 caracteres, sin espacios).
# Guía: https://support.google.com/accounts/answer/185833
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

# PIN numérico para proteger el panel de administración.
# Puede tener cualquier longitud; recomendado mínimo 6 dígitos en producción.
ADMIN_PIN=1234
```

> **Seguridad:** nunca subas el archivo `.env` a un repositorio público. Ya está incluido en `.gitignore`.

---

## 📖 Guía de uso rápido

1. **Abrir el panel admin** → `http://localhost:8000/admin/` → ingresar el `ADMIN_PIN` en la barra superior.

2. **Crear un evento** → pestaña *Eventos* → completar nombre y fecha → *Crear evento*.

3. **Agregar barmans** → pestaña *Barmans* → para cada barman ingresar nombre y PIN de 4–6 dígitos.

4. **Generar cupones** → pestaña *Cupones* → elegir modo:
   - **Lista**: pegar líneas con formato `email,nombre` (un cupón por línea).
   - **Anónimos**: indicar solo la cantidad; los cupones no tendrán titular asignado.

5. **Enviar emails con QR** → botón *Enviar todos los emails* (solo para cupones con email asignado y no enviados aún).

6. **Barmans: login en el móvil** → abrir `http://<ip-local>:8000/barman/` → ingresar ID de evento y PIN → opcionalmente instalar como PWA desde el menú del navegador.

7. **Escanear QR** → botón *ESCANEAR CUPÓN* → apuntar la cámara al QR del cliente.

8. **Monitor en tiempo real** → pestaña *Monitor* en el panel admin → se actualiza automáticamente cada 10 segundos.

---

## 📵 Modo offline

El sistema está diseñado para seguir funcionando aunque la WiFi del local falle.

### ¿Cómo funciona?

1. Al iniciar sesión, la app del barman descarga y guarda en caché (`localStorage` + Service Worker) todos los cupones **asignados a ese barman**, junto con la clave HMAC.
2. Los cupones se asignan en el momento de la generación usando **distribución round-robin** entre los barmans registrados para el evento.
3. Sin conexión, el barman puede escanear y validar sus cupones asignados: la firma HMAC se verifica localmente en el dispositivo.
4. Si el QR escaneado pertenece a un cupón asignado a **otro barman**, la app lo indica ("Este cupón es de [nombre del barman]") pero no puede validarlo offline — el cliente debe acercarse a ese barman o esperar que vuelva la conexión.
5. Los canjes realizados offline se almacenan en la cola local. Al recuperar la conexión (o al pulsar **SINCRONIZAR**) se envían al servidor automáticamente.
6. El servidor detecta conflictos (p. ej. el mismo cupón canjeado dos veces por barmans distintos offline) y los reporta claramente.

---

## 📁 Estructura del proyecto

```
cupones/
├── admin/
│   └── index.html          # Panel de administración (SPA en vanilla JS)
│
├── barman/
│   ├── index.html          # Interfaz PWA del barman
│   ├── app.js              # Lógica principal: login, stats, flujo de escaneo
│   ├── scanner.js          # Integración con html5-qrcode para leer QR
│   ├── offline.js          # Gestión de caché local, cola offline y sincronización
│   ├── sw.js               # Service Worker para soporte offline e instalación PWA
│   └── manifest.json       # Manifiesto PWA (nombre, iconos, colores, orientación)
│
├── server/
│   ├── app.py              # Servidor FastAPI: definición de todos los endpoints
│   ├── config.py           # Carga de variables de entorno (.env)
│   ├── database.py         # Modelos SQLAlchemy y creación de tablas (SQLite)
│   ├── coupon_utils.py     # Generación de códigos, firma HMAC y QR base64
│   ├── email_service.py    # Envío de emails via Gmail SMTP con QR embebido
│   ├── requirements.txt    # Dependencias Python
│   ├── .env                # Variables de entorno (NO subir al repo)
│   └── .env.example        # Plantilla de configuración con comentarios
│
├── .gitignore
└── README.md
```

---

## 🔌 API Endpoints

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| `GET` | `/api/events` | Lista todos los eventos con estadísticas | — |
| `POST` | `/api/events` | Crea un nuevo evento | Admin PIN |
| `GET` | `/api/events/{id}` | Detalle de un evento | — |
| `POST` | `/api/barmans` | Registra un barman en un evento | Admin PIN |
| `GET` | `/api/events/{id}/barmans` | Lista barmans de un evento | — |
| `POST` | `/api/coupons/generate` | Genera cupones (con o sin titulares) | Admin PIN |
| `GET` | `/api/events/{id}/coupons` | Lista cupones de un evento | Admin PIN (query param) |
| `POST` | `/api/coupons/send-email` | Envía el QR de un cupón específico por email | Admin PIN |
| `POST` | `/api/coupons/send-all` | Envía emails a todos los cupones pendientes del evento | Admin PIN |
| `POST` | `/api/redeem` | Canjea un cupón (modo online) | Barman PIN |
| `POST` | `/api/sync` | Sincroniza canjes realizados offline | Barman PIN |
| `POST` | `/api/barman/login` | Autenticación del barman | Barman PIN |
| `GET` | `/api/barman/{id}/coupons` | Descarga los cupones asignados al barman (para caché offline) | Barman PIN (query param) |
| `GET` | `/` | Redirección a `/admin/` | — |

> La documentación interactiva completa (Swagger UI) está disponible en `http://localhost:8000/docs`.

---

## 🔒 Seguridad

- **Cupones firmados con HMAC-SHA256** — la firma vincula el código con el ID del evento; modificar cualquier campo invalida el cupón.
- **PINs para barmans y admin** — toda acción de escritura requiere autenticación.
- **HTTPS recomendado en producción** — sin HTTPS, los PINs viajan en texto plano; usa un reverse proxy con TLS (ver sección de despliegue).
- **Cambiar `COUPON_SECRET_KEY` en producción** — el valor por defecto es público; cualquiera podría generar cupones válidos si lo conoce.
- **No exponer `.env`** — añadido a `.gitignore`; nunca lo subas al repositorio ni lo sirvas como archivo estático.

---

## 🌐 Despliegue en producción

### Servidor

```bash
# Múltiples workers para mayor rendimiento
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Reverse proxy con HTTPS (ejemplo con Caddy)

```
tudominio.com {
    reverse_proxy localhost:8000
}
```

Caddy obtiene y renueva automáticamente el certificado de Let's Encrypt.

### Conectividad en el evento

- Los barmans necesitan estar en la **misma red local** que el servidor (o acceder vía Internet si el servidor es público).
- Considera usar un **router 4G** como backup de conectividad: enchufa el router a corriente, conéctalo a la SIM y conéctate a su WiFi. Así el servidor sigue accesible aunque falle el WiFi del local.
- En el peor caso (sin red en absoluto), el **modo offline** garantiza que cada barman siga validando sus cupones asignados.

### Variables de entorno adicionales recomendadas

```dotenv
# PIN robusto de al menos 8 caracteres
ADMIN_PIN=un_pin_seguro_largo

# Clave generada aleatoriamente
COUPON_SECRET_KEY=<salida de: python -c "import secrets; print(secrets.token_hex(32))">
```

---

## 📦 Dependencias principales

| Paquete | Uso |
|---------|-----|
| `fastapi` | Framework web y definición de la API REST |
| `uvicorn[standard]` | Servidor ASGI para ejecutar FastAPI |
| `sqlalchemy` | ORM y gestión de la base de datos SQLite |
| `qrcode[pil]` | Generación de imágenes QR |
| `python-dotenv` | Carga de variables desde el archivo `.env` |
| `python-multipart` | Soporte para formularios (requerido por FastAPI) |

---

## 📄 Licencia

MIT — libre para usar, modificar y distribuir.
