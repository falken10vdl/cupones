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
- **HTTPS integrado** — el servidor arranca con TLS usando un certificado autofirmado; la cámara del móvil sólo funciona en contextos seguros

---

## 🏗️ Arquitectura

```
Admin Panel (navegador) ──┐
                          ├──► FastAPI Server (Python, HTTPS :8080) ──► SQLite (coupons.db)
Barman PWA (móvil)  ──────┘            │
                                  Gmail SMTP ──► Clientes (QR por email)
```

El servidor sirve tanto la API REST como los archivos estáticos del panel admin (`/admin/`) y la PWA del barman (`/barman/`).

---

## 📋 Requisitos previos

| Requisito | Versión mínima | Notas |
|-----------|----------------|-------|
| Sistema operativo | Windows 10/11, macOS 12+, o Linux | |
| Python | 3.10+ | Preinstalado en macOS/Linux; instalador en python.org para Windows |
| Git | 2.x | Preinstalado en macOS/Linux; instalador en git-scm.com para Windows |
| OpenSSL | Cualquiera moderna | Preinstalado en macOS/Linux; incluido con Git for Windows |
| Cuenta Gmail | — | Con [contraseña de aplicación](https://support.google.com/accounts/answer/185833) habilitada |

> **Nota Gmail:** La contraseña de aplicación es un código de 16 caracteres que Google genera específicamente para apps de terceros. No uses tu contraseña normal de Google.

---

## 🔐 Certificado TLS autofirmado

El servidor **requiere HTTPS** para que la cámara del móvil funcione en la PWA del barman. Al arrancar, `app.py` busca `cert.pem` y `cert.key` en la carpeta `server/`. Si no existen, arranca en HTTP (solo para desarrollo local).

### Generar el certificado (una sola vez)

El comando exacto para generar el certificado se encuentra en el **paso de instalación correspondiente a tu sistema operativo** (ver [🚀 Instalación](#-instalación), paso *Generar el certificado TLS*). Las instrucciones varían ligeramente entre plataformas, especialmente en Windows con Git Bash.

El proceso genera dos archivos en `server/`:

| Archivo | Descripción |
|---------|-------------|
| `cert.pem` | Certificado público |
| `cert.key` | Clave privada (no compartir) |

Ambos están incluidos en `.gitignore` y no se subirán al repositorio.

### ⚠️ Advertencia de seguridad del navegador (certificado autofirmado)

Al abrir la aplicación por primera vez desde el móvil o el navegador, **aparecerá un aviso de seguridad** porque el certificado no está emitido por una autoridad de certificación reconocida. Esto es **normal y esperado** en uso en red local.

**Cómo continuar:**

- **Chrome / Android:** pulsa *"Avanzado"* → *"Continuar con \<ip\> (sitio no seguro)"*
- **Firefox:** pulsa *"Avanzado…"* → *"Aceptar el riesgo y continuar"*
- **Safari / iOS:** pulsa *"Mostrar detalles"* → *"visitar este sitio web"* → confirma en el cuadro de diálogo

> **Todos los usuarios deben hacer esto:** tanto el administrador al abrir el panel como cada barman al abrir la app en su móvil. Solo es necesario una vez por dispositivo/navegador.

---

## 🚀 Instalación

Elige tu sistema operativo:

<details>
<summary>🖥️ Windows 10 / 11</summary>

### 1. Instalar Python

1. Ve a **https://www.python.org/downloads/** y descarga el instalador de Python 3.10 o superior.
2. Ejecuta el instalador. **Importante:** marca la opción **"Add Python to PATH"** antes de pulsar *Install Now*.
3. Verifica la instalación abriendo **PowerShell** o **Símbolo del sistema (cmd)**:

```cmd
python --version
pip --version
```

### 2. Instalar Git

1. Ve a **https://git-scm.com/download/win** y descarga el instalador.
2. Ejecuta el instalador con las opciones por defecto (incluye OpenSSL).
3. Verifica:

```cmd
git --version
```

### 3. Clonar el repositorio

```cmd
git clone https://github.com/falken10vdl/cupones.git
cd cupones
```

### 4. Crear un entorno virtual

```cmd
cd server
python -m venv venv
venv\Scripts\activate
```

Verás `(venv)` al inicio del prompt. Para desactivarlo usa `deactivate`.

### 5. Instalar dependencias

```cmd
pip install -r requirements.txt
```

### 6. Configurar el entorno

```cmd
copy .env.example .env
```

Abre `.env` con el Bloc de notas y completa los valores (ver [Configuración del .env](#️-configuración-del-env)).

### 7. Generar el certificado TLS

Las instrucciones siguientes usan **Git Bash** (incluido con Git for Windows). También son posibles otras opciones como PowerShell o un OpenSSL instalado por separado. Abre Git Bash, navega a la carpeta `server/` del proyecto y sigue estos pasos:

**7a. Obtén tu IP local**

```bash
ipconfig
```

Busca la línea **Dirección IPv4** bajo tu adaptador Wi-Fi o Ethernet (p. ej. `192.168.1.10`).

**7b. Crea un archivo de configuración temporal**

Este método evita problemas de compatibilidad con la opción `-addext` en algunas versiones de OpenSSL incluidas con Git for Windows. Ejecuta el siguiente bloque completo en Git Bash (sustituyendo `<TU-IP-LOCAL>` por tu IP real):

```bash
cat > san.cnf << 'EOF'
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = localhost

[v3_req]
subjectAltName = IP:127.0.0.1,IP:<TU-IP-LOCAL>
EOF
```

Puedes añadir más IPs separando con comas, p. ej.:
```
subjectAltName = IP:127.0.0.1,IP:192.168.1.10,IP:192.168.201.53
```

**7c. Genera el certificado**

```bash
openssl req -x509 -newkey rsa:2048 -keyout cert.key -out cert.pem -days 365 -nodes -config san.cnf
```

**7d. Elimina el archivo temporal**

```bash
rm san.cnf
```

Deben quedar dos archivos nuevos en `server/`: `cert.pem` y `cert.key`.



### 8. Iniciar el servidor

```cmd
python app.py
```

> **Firewall de Windows:** la primera vez pulsa *Permitir acceso* para que los móviles de la red puedan conectarse.

### 9. Acceder a las interfaces

| Interfaz | URL |
|----------|-----|
| **Página de bienvenida** | https://localhost:8080/ |
| Panel de administración | https://localhost:8080/admin/ |
| App barman (PWA) | https://localhost:8080/barman/ |
| Documentación API | https://localhost:8080/docs |

Para acceso desde móviles, busca tu IP local con `ipconfig` (línea **Dirección IPv4**) y comparte `https://<tu-ip>:8080/barman/`.

> **Certificado autofirmado:** al abrir la URL por primera vez el navegador mostrará un aviso. Pulsa *Avanzado* → *Continuar de todos modos*. Ver sección [Advertencia de seguridad del navegador](#️-advertencia-de-seguridad-del-navegador-certificado-autofirmado).

</details>

<details>
<summary>🐧 Linux (Ubuntu, Fedora, Arch…)</summary>

### 1. Instalar dependencias del sistema

**Ubuntu / Debian:**

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git openssl
```

**Fedora / RHEL:**

```bash
sudo dnf install -y python3 python3-pip git openssl
```

**Arch Linux:**

```bash
sudo pacman -S python python-pip git openssl
```

Verifica:

```bash
python3 --version
git --version
```

### 2. Clonar el repositorio

```bash
git clone https://github.com/falken10vdl/cupones.git
cd cupones
```

### 3. Crear un entorno virtual

```bash
cd server
python3 -m venv venv
source venv/bin/activate
```

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 5. Configurar el entorno

```bash
cp .env.example .env
nano .env   # o el editor que prefieras
```

Completa los valores (ver [Configuración del .env](#️-configuración-del-env)).

### 6. Generar el certificado TLS

```bash
openssl req -x509 -newkey rsa:2048 -keyout cert.key -out cert.pem -days 365 -nodes \
  -subj "/CN=localhost" \
  -addext "subjectAltName=IP:127.0.0.1,IP:<TU-IP-LOCAL>"
```

### 7. (Opcional) Abrir el puerto en el firewall

```bash
# firewalld (Fedora/RHEL):
sudo firewall-cmd --permanent --add-port=8080/tcp && sudo firewall-cmd --reload

# ufw (Ubuntu):
sudo ufw allow 8080/tcp
```

### 8. Iniciar el servidor

```bash
python3 app.py
```

### 9. Acceder a las interfaces

| Interfaz | URL |
|----------|-----|
| **Página de bienvenida** | https://localhost:8080/ |
| Panel de administración | https://localhost:8080/admin/ |
| App barman (PWA) | https://localhost:8080/barman/ |
| Documentación API | https://localhost:8080/docs |

Para acceso desde móviles, obtén tu IP local con:

```bash
ip route get 1 | awk '{print $7; exit}'
# o:
hostname -I | awk '{print $1}'
```

Comparte `https://<tu-ip>:8080/barman/` con los barmans.

> **Certificado autofirmado:** al abrir la URL el navegador mostrará un aviso. Pulsa *Avanzado* → *Continuar de todos modos*. Ver sección [Advertencia de seguridad del navegador](#️-advertencia-de-seguridad-del-navegador-certificado-autofirmado).

</details>

<details>
<summary>🍎 macOS (Monterey 12+)</summary>

### 1. Instalar Homebrew (si no lo tienes)

Abre **Terminal** y ejecuta:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Instalar Python y Git

```bash
brew install python git
```

Verifica:

```bash
python3 --version
git --version
```

### 3. Clonar el repositorio

```bash
git clone https://github.com/falken10vdl/cupones.git
cd cupones
```

### 4. Crear un entorno virtual

```bash
cd server
python3 -m venv venv
source venv/bin/activate
```

### 5. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 6. Configurar el entorno

```bash
cp .env.example .env
nano .env   # o abre con: open -e .env
```

### 7. Generar el certificado TLS

```bash
openssl req -x509 -newkey rsa:2048 -keyout cert.key -out cert.pem -days 365 -nodes \
  -subj "/CN=localhost" \
  -addext "subjectAltName=IP:127.0.0.1,IP:<TU-IP-LOCAL>"
```

### 8. Iniciar el servidor

```bash
python3 app.py
```

> **Firewall de macOS:** si aparece un aviso de seguridad de red, pulsa *Permitir*.

### 9. Acceder a las interfaces

| Interfaz | URL |
|----------|-----|
| **Página de bienvenida** | https://localhost:8080/ |
| Panel de administración | https://localhost:8080/admin/ |
| App barman (PWA) | https://localhost:8080/barman/ |
| Documentación API | https://localhost:8080/docs |

Para acceso desde móviles, obtén tu IP local con:

```bash
ipconfig getifaddr en0   # Wi-Fi
ipconfig getifaddr en1   # Ethernet
```

Comparte `https://<tu-ip>:8080/barman/` con los barmans.

> **Certificado autofirmado:** al abrir la URL el navegador mostrará un aviso. Pulsa *Avanzado* → *Continuar de todos modos*. Ver sección [Advertencia de seguridad del navegador](#️-advertencia-de-seguridad-del-navegador-certificado-autofirmado).

</details>

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

1. **Abrir el panel admin** → `https://<ip>:8080/admin/` → aceptar el aviso del certificado → ingresar el `ADMIN_PIN`.

2. **Crear un evento** → pestaña *Eventos* → completar nombre y fecha → *Crear evento*.

3. **Agregar barmans** → pestaña *Barmans* → para cada barman ingresar nombre y PIN de 4–6 dígitos.

4. **Generar cupones** → pestaña *Cupones* → pegar líneas con formato `email,nombre` (un cupón por línea) → *Generar*.

5. **Enviar emails con QR** → botón *Enviar todos los emails* (solo para cupones con email asignado y no enviados aún).

6. **Barmans: login en el móvil** → abrir `https://<ip-local>:8080/barman/` → aceptar el aviso del certificado → ingresar ID de evento y PIN → opcionalmente instalar como PWA desde el menú del navegador.

7. **Escanear QR** → botón *ESCANEAR CUPÓN* → apuntar la cámara al QR del cliente.

8. **Monitor en tiempo real** → pestaña *Monitor* en el panel admin → se actualiza automáticamente cada 10 segundos.

---

## 📵 Modo offline

El sistema está diseñado para seguir funcionando aunque la WiFi del local falle.

### ¿Cómo funciona?

1. Al iniciar sesión, la app del barman descarga y guarda en caché (IndexedDB + Service Worker) todos los cupones **pendientes asignados a ese barman**, junto con la clave HMAC.
2. Los cupones se asignan en el momento de la generación usando **distribución round-robin** entre los barmans registrados para el evento.
3. Sin conexión, el barman puede escanear y validar sus cupones asignados: la firma HMAC se verifica localmente en el dispositivo.
4. Si el QR escaneado pertenece a un cupón asignado a **otro barman**, la app lo indica pero no puede validarlo offline — el cliente debe acercarse a ese barman o esperar que vuelva la conexión.
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
│   ├── app.py              # Servidor FastAPI: API + landing page (HTTPS, puerto 8080)
│   ├── config.py           # Carga de variables de entorno (.env)
│   ├── database.py         # Modelos SQLAlchemy y creación de tablas (SQLite)
│   ├── coupon_utils.py     # Generación de códigos, firma HMAC y QR base64
│   ├── email_service.py    # Envío de emails via Gmail SMTP con QR embebido
│   ├── requirements.txt    # Dependencias Python
│   ├── cert.pem            # Certificado TLS autofirmado (NO subir al repo)
│   ├── cert.key            # Clave privada TLS (NO subir al repo)
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
| `POST` | `/api/coupons/generate` | Genera cupones con titulares | Admin PIN |
| `GET` | `/api/events/{id}/coupons` | Lista cupones de un evento | Admin PIN (query param) |
| `POST` | `/api/coupons/{code}/send-email` | Envía el QR de un cupón específico por email | Admin PIN |
| `POST` | `/api/coupons/send-all` | Envía emails a todos los cupones pendientes del evento | Admin PIN |
| `POST` | `/api/redeem` | Canjea un cupón (modo online) | Barman PIN |
| `POST` | `/api/sync` | Sincroniza canjes realizados offline | Barman PIN |
| `POST` | `/api/barman/login` | Autenticación del barman | Barman PIN |
| `GET` | `/api/barman/{id}/coupons` | Descarga cupones pendientes asignados al barman (caché offline) | Barman PIN (query param) |
| `GET` | `/` | Página de bienvenida con IP del servidor | — |

> La documentación interactiva completa (Swagger UI) está disponible en `https://localhost:8080/docs`.

---

## 🔒 Seguridad

- **HTTPS obligatorio** — el servidor arranca con TLS; la cámara del móvil sólo funciona en contextos seguros (`https://` o `localhost`).
- **Cupones firmados con HMAC-SHA256** — la firma vincula el código con el ID del evento; modificar cualquier campo invalida el cupón.
- **PINs para barmans y admin** — toda acción de escritura requiere autenticación.
- **Certificado autofirmado aceptable en red local** — para un evento en una red privada es suficiente; en producción con dominio público usa Let's Encrypt.
- **Cambiar `COUPON_SECRET_KEY` en producción** — el valor por defecto es público; cualquiera podría generar cupones válidos si lo conoce.
- **No exponer `.env`, `cert.pem` ni `cert.key`** — añadidos a `.gitignore`; nunca los subas al repositorio ni los sirvas como archivos estáticos.

---

## 🌐 Despliegue en producción

### Servidor

```bash
# Múltiples workers para mayor rendimiento
uvicorn app:app --host 0.0.0.0 --port 8080 --workers 4 \
  --ssl-certfile cert.pem --ssl-keyfile cert.key
```

### Reverse proxy con HTTPS (ejemplo con Caddy)

```
tudominio.com {
    reverse_proxy localhost:8080
}
```

Caddy obtiene y renueva automáticamente el certificado de Let's Encrypt (no necesitas `cert.pem`/`cert.key` en este caso).

### Conectividad en el evento

- Los barmans necesitan estar en la **misma red local** que el servidor (o acceder vía Internet si el servidor es público).
- Considera usar un **router 4G** como backup de conectividad.
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
| `uvicorn[standard]` | Servidor ASGI para ejecutar FastAPI con soporte TLS |
| `sqlalchemy` | ORM y gestión de la base de datos SQLite |
| `qrcode[pil]` | Generación de imágenes QR |
| `python-dotenv` | Carga de variables desde el archivo `.env` |
| `python-multipart` | Soporte para formularios (requerido por FastAPI) |

---

## 📄 Licencia

MIT — libre para usar, modificar y distribuir.


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
| Sistema operativo | Windows 10/11, macOS 12+, o Linux | |
| Python | 3.10+ | Preinstalado en macOS/Linux; instalador en python.org para Windows |
| Git | 2.x | Preinstalado en macOS/Linux; instalador en git-scm.com para Windows |
| Cuenta Gmail | — | Con [contraseña de aplicación](https://support.google.com/accounts/answer/185833) habilitada |

> **Nota Gmail:** La contraseña de aplicación es un código de 16 caracteres que Google genera específicamente para apps de terceros. No uses tu contraseña normal de Google.

---

## � Instalación

Elige tu sistema operativo:

<details>
<summary>🖥️ Windows 10 / 11</summary>

### 1. Instalar Python

1. Ve a **https://www.python.org/downloads/** y descarga el instalador de Python 3.10 o superior.
2. Ejecuta el instalador. **Importante:** marca la opción **"Add Python to PATH"** antes de pulsar *Install Now*.
3. Verifica la instalación abriendo **PowerShell** o **Símbolo del sistema (cmd)**:

```cmd
python --version
pip --version
```

### 2. Instalar Git

1. Ve a **https://git-scm.com/download/win** y descarga el instalador.
2. Ejecuta el instalador con las opciones por defecto.
3. Verifica:

```cmd
git --version
```

### 3. Clonar el repositorio

```cmd
git clone https://github.com/falken10vdl/cupones.git
cd cupones
```

### 4. Crear un entorno virtual

```cmd
cd server
python -m venv venv
venv\Scripts\activate
```

Verás `(venv)` al inicio del prompt. Para desactivarlo usa `deactivate`.

### 5. Instalar dependencias

```cmd
pip install -r requirements.txt
```

### 6. Configurar el entorno

```cmd
copy .env.example .env
```

Abre `.env` con el Bloc de notas y completa los valores (ver [Configuración del .env](#️-configuración-del-env)).

### 7. Iniciar el servidor

```cmd
python app.py
```

> **Firewall de Windows:** la primera vez pulsa *Permitir acceso* para que los móviles de la red puedan conectarse.

### 8. Acceder a las interfaces

| Interfaz | URL |
|----------|-----|
| **Página de bienvenida** (IP + docs) | http://localhost:8080/ |
| Panel de administración | http://localhost:8080/admin/ |
| App barman (PWA) | http://localhost:8080/barman/ |
| Documentación API | http://localhost:8080/docs |

Para acceso desde móviles, busca tu IP local con `ipconfig` (línea **Dirección IPv4**) y comparte `http://<tu-ip>:8080/barman/`.

</details>

<details>
<summary>🐧 Linux (Ubuntu, Fedora, Arch…)</summary>

### 1. Instalar dependencias del sistema

**Ubuntu / Debian:**

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

**Fedora / RHEL:**

```bash
sudo dnf install -y python3 python3-pip git
```

**Arch Linux:**

```bash
sudo pacman -S python python-pip git
```

Verifica:

```bash
python3 --version
git --version
```

### 2. Clonar el repositorio

```bash
git clone https://github.com/falken10vdl/cupones.git
cd cupones
```

### 3. Crear un entorno virtual

```bash
cd server
python3 -m venv venv
source venv/bin/activate
```

Verás `(venv)` al inicio del prompt. Para desactivarlo usa `deactivate`.

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 5. Configurar el entorno

```bash
cp .env.example .env
nano .env   # o el editor que prefieras
```

Completa los valores (ver [Configuración del .env](#️-configuración-del-env)).

### 6. Iniciar el servidor

```bash
python3 app.py
```

### 7. Acceder a las interfaces

| Interfaz | URL |
|----------|-----|
| **Página de bienvenida** (IP + docs) | http://localhost:8080/ |
| Panel de administración | http://localhost:8080/admin/ |
| App barman (PWA) | http://localhost:8080/barman/ |
| Documentación API | http://localhost:8080/docs |

Para acceso desde móviles, obtén tu IP local con:

```bash
ip route get 1 | awk '{print $7; exit}'
# o:
hostname -I | awk '{print $1}'
```

Comparte `http://<tu-ip>:8080/barman/` con los barmans.

</details>

<details>
<summary>🍎 macOS (Monterey 12+)</summary>

### 1. Instalar Homebrew (si no lo tienes)

Abre **Terminal** y ejecuta:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Sigue las instrucciones en pantalla. Al terminar, ejecuta los comandos `eval` que Homebrew indique para añadirlo al PATH.

### 2. Instalar Python y Git

macOS incluye Git, pero se recomienda instalar versiones actualizadas via Homebrew:

```bash
brew install python git
```

Verifica:

```bash
python3 --version
git --version
```

### 3. Clonar el repositorio

```bash
git clone https://github.com/falken10vdl/cupones.git
cd cupones
```

### 4. Crear un entorno virtual

```bash
cd server
python3 -m venv venv
source venv/bin/activate
```

Verás `(venv)` al inicio del prompt. Para desactivarlo usa `deactivate`.

### 5. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 6. Configurar el entorno

```bash
cp .env.example .env
nano .env   # o abre con: open -e .env
```

Completa los valores (ver [Configuración del .env](#️-configuración-del-env)).

### 7. Iniciar el servidor principal

```bash
python3 app.py
```

> **Firewall de macOS:** si aparece un aviso de seguridad de red, pulsa *Permitir* para que los móviles de la red puedan conectarse.

### 8. Acceder a las interfaces

| Interfaz | URL |
|----------|-----|
| **Página de bienvenida** (IP + docs) | http://localhost:8080/ |
| Panel de administración | http://localhost:8080/admin/ |
| App barman (PWA) | http://localhost:8080/barman/ |
| Documentación API | http://localhost:8080/docs |

Para acceso desde móviles, obtén tu IP local con:

```bash
ipconfig getifaddr en0
# Wi-Fi por cable (Ethernet):
ipconfig getifaddr en1
```

Comparte `http://<tu-ip>:8080/barman/` con los barmans.

</details>

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

1. **Abrir el panel admin** → `http://localhost:8080/admin/` → ingresar el `ADMIN_PIN` en la barra superior.

2. **Crear un evento** → pestaña *Eventos* → completar nombre y fecha → *Crear evento*.

3. **Agregar barmans** → pestaña *Barmans* → para cada barman ingresar nombre y PIN de 4–6 dígitos.

4. **Generar cupones** → pestaña *Cupones* → elegir modo:
   - **Lista**: pegar líneas con formato `email,nombre` (un cupón por línea).
   - **Anónimos**: indicar solo la cantidad; los cupones no tendrán titular asignado.

5. **Enviar emails con QR** → botón *Enviar todos los emails* (solo para cupones con email asignado y no enviados aún).

6. **Barmans: login en el móvil** → abrir `http://<ip-local>:8080/barman/` → ingresar ID de evento y PIN → opcionalmente instalar como PWA desde el menú del navegador.

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
│   ├── app.py              # Servidor FastAPI: API + landing page (puerto 8080)
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
| `GET` | `/` | Página de bienvenida con IP del servidor y documentación | — |
| `GET` | `/readme.md` | README en texto plano (usado por la landing) | — |

> La documentación interactiva completa (Swagger UI) está disponible en `http://localhost:8080/docs`.

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
uvicorn app:app --host 0.0.0.0 --port 8080 --workers 4
```

### Reverse proxy con HTTPS (ejemplo con Caddy)

```
tudominio.com {
    reverse_proxy localhost:8080
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
