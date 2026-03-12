# 🔒 Secam - Smart Security Camera SaaS

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Python-3.11-blue?style=flat&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Next.js-14-black?style=flat&logo=next.js" alt="Next.js">
  <img src="https://img.shields.io/badge/FastAPI-Framework-009688?style=flat&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-Containerized-2496ED?style=flat&logo=docker" alt="Docker">
</p>

> **Plataforma multi-tenant de videovigilancia inteligente** con reconocimiento facial en tiempo real.

---

## ✨ Características Principales

| Característica | Descripción |
|----------------|-------------|
| 🎥 **Gestión de Cámaras** | CRUD completo de cámaras RTSP, configuración de calidad y detección |
| 👤 **Reconocimiento Facial** | Registro y detección de personas en tiempo real |
| 📊 **Panel Admin** | Dashboard multi-tenant para gestionar clientes y métricas globales |
| 📅 **Eventos y Timeline** | Historial de eventos con filtros por cámara, persona y fecha |
| 🌐 **Acceso Remoto** | API RESTful + WebSocket para integración |
| 🔐 **Seguridad** | JWT, Argon2, encriptación de URLs RTSP, rate limiting |

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PANEL ADMIN                                 │
│         Gestionar tenants, usuarios, métricas globales              │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CLOUD CORE API                                 │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐              │
│  │  FastAPI    │   │  PostgreSQL │   │    Redis    │              │
│  │  Backend    │   │  (Multi-    │   │  (Cache +   │              │
│  │             │   │   tenant)   │   │   Queue)    │              │
│  └─────────────┘   └─────────────┘   └─────────────┘              │
│                                                                     │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐              │
│  │  Next.js    │   │  WebSocket  │   │    AI/ML    │              │
│  │  Frontend   │   │  Streaming  │   │  Processing │              │
│  └─────────────┘   └─────────────┘   └─────────────┘              │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        EDGE AGENT                                   │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐              │
│  │   RTSP     │   │   OpenCV    │   │   Face      │              │
│  │   Stream   │──▶│   Processing│──▶│   Recognition│              │
│  └─────────────┘   └─────────────┘   └─────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerrequisitos

- Docker y Docker Compose
- Git
- Python 3.11 si vas a ejecutar `apps/cloud-api` fuera de Docker

### 1. Clonar el repositorio

```bash
git clone https://github.com/ErikING-Chile/secam.git
cd secam
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

### 3. Generar secretos seguros

```bash
# JWT Secret
openssl rand -hex 32

# PostgreSQL Password
openssl rand -base64 32

# Encryption Key para URLs RTSP
openssl rand -hex 32
```

### 4. Levantar servicios

```bash
docker-compose up -d
```

### 5. Acceder a la aplicación

| Servicio | URL |
|----------|-----|
| 🌐 **Web UI** | http://localhost:3000 |
| 📚 **API Docs** | http://localhost:8000/docs |
| 🗄️ **PostgreSQL** | localhost:5432 |
| ⚡ **Redis** | localhost:6380 |

---

## 📁 Estructura del Proyecto

```
secam/
├── apps/
│   ├── cloud-api/          # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py          # Entry point
│   │   │   ├── db.py            # Database config
│   │   │   ├── models.py        # SQLAlchemy models
│   │   │   ├── schemas.py       # Pydantic schemas
│   │   │   ├── auth.py          # JWT authentication
│   │   │   ├── security.py      # Security utilities
│   │   │   ├── routers/         # API endpoints
│   │   │   │   ├── auth.py       # Login/Register
│   │   │   │   ├── cameras.py   # Camera management
│   │   │   │   ├── events.py    # Events timeline
│   │   │   │   ├── persons.py   # Face registration
│   │   │   │   ├── admin.py     # Admin panel
│   │   │   │   └── webrtc.py    # WebRTC streaming
│   │   │   └── config.py        # Configuration
│   │   ├── requirements.txt    # Python dependencies
│   │   └── Dockerfile
│   │
│   ├── web/                # Next.js frontend
│   │   ├── src/
│   │   │   ├── app/            # App router
│   │   │   │   ├── login/      # Login page
│   │   │   │   ├── register/  # Registration page
│   │   │   │   ├── dashboard/ # User dashboard
│   │   │   │   └── admin/      # Admin panel
│   │   │   ├── components/     # React components
│   │   │   └── lib/            # Utilities
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   └── edge-agent/        # Python RTSP + AI (futuro)
│
├── infra/
│   ├── docker/
│   ├── nginx/
│   │   ├── nginx.conf
│   │   └── ssl/
│   └── k8s/
│
├── packages/
│   ├── shared-types/       # TypeScript types
│   └── face-ml/           # ML models
│
├── docs/                   # Documentación
├── data/                   # Datos (uploads, faces)
├── docker-compose.yml      # Orquestación
├── .env.example           # Variables de entorno
└── README.md
```

---

## 🛠️ Tecnologías

### Backend
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=flat&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat&logo=redis&logoColor=white)

### Frontend
![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat&logo=next.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.1-3178C6?style=flat&logo=typescript&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=flat&logo=tailwind-css&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)

### AI/ML
![OpenCV](https://img.shields.io/badge/OpenCV-5-5C3EE8?style=flat&logo=opencv&logoColor=white)
![face_recognition](https://img.shields.io/badge-face__recognition-FF6B6B?style=flat)

---

## 🔐 Seguridad

- ✅ **JWT** con access y refresh tokens
- ✅ **Argon2** para hashing de contraseñas
- ✅ **Encriptación Fernet** para URLs RTSP
- ✅ **Rate limiting** en endpoints de autenticación
- ✅ **CORS** estricto
- ✅ **Audit logs** de acciones

---

## 📝 API Endpoints

### Autenticación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Registrar usuario |
| POST | `/api/v1/auth/login` | Iniciar sesión |
| POST | `/api/v1/auth/refresh` | Refresh token |
| POST | `/api/v1/auth/logout` | Cerrar sesión |

### Cámaras
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/cameras` | Listar cámaras |
| POST | `/api/v1/cameras` | Crear cámara |
| GET | `/api/v1/cameras/{id}` | Ver cámara |
| PUT | `/api/v1/cameras/{id}` | Actualizar cámara |
| DELETE | `/api/v1/cameras/{id}` | Eliminar cámara |
| POST | `/api/v1/cameras/{id}/test` | Diagnóstico RTSP saneado para troubleshooting |

### Personas
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/persons` | Listar personas |
| POST | `/api/v1/persons` | Registrar persona |
| POST | `/api/v1/persons/{id}/face` | Agregar rostro |
| DELETE | `/api/v1/persons/{id}` | Eliminar persona |

### Eventos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/events` | Listar eventos |
| GET | `/api/v1/events/{id}` | Ver evento |

---

## 🖥️ Uso desde otra máquina (Red Local)

1. **Configurar IP en `.env`:**
   ```bash
   SERVER_IP=192.168.1.100  # Tu IP local
   NEXT_PUBLIC_API_URL=http://192.168.1.100:8000/api/v1
   NEXT_PUBLIC_WS_URL=ws://192.168.1.100:8000/ws
   ```

2. **Actualizar CORS:**
   ```
   CORS_ORIGINS=http://localhost:3000,http://TU_IP:3000,http://TU_IP:8000
   ```

3. **Reiniciar servicios:**
   ```bash
   docker-compose down && docker-compose up -d
   ```

4. **Acceder:** `http://TU_IP:3000`

---

## ✅ Verificacion local de vista en vivo RTSP

Usa esta rutina corta cuando quieras volver a validar el flujo de live view sin rearmar el contexto del cambio.

### Backend (`apps/cloud-api`)

- Usa Python 3.11 para crear o activar tu entorno virtual antes de instalar dependencias o correr pruebas.
- El backend ahora espera `DATABASE_URL` con el driver explicito `postgresql+psycopg://...` para que local, Docker y SQLAlchemy 2 usen el mismo contrato.

```bash
cd apps/cloud-api
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
DATABASE_URL=postgresql+psycopg://secam:password@localhost:5432/secam pytest
```

PowerShell:

```powershell
Set-Location apps/cloud-api
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DATABASE_URL = "postgresql+psycopg://secam:password@localhost:5432/secam"
pytest
```

### Frontend (`apps/web`)

Ejecuta estas comprobaciones ligeras en este orden:

```bash
npm test
npm run typecheck
npm run build
```

- `npm run lint` no entra en la verificacion repetible por ahora: `next lint` sigue siendo interactivo si falta la configuracion de ESLint local.
- Si necesitas correr lint despues, agrega primero la configuracion de ESLint para evitar el prompt interactivo.

### Diagnostico RTSP host vs Docker

- Si la vista en vivo falla, el modal sigue intentando primero el stream MJPEG y despues pide `POST /api/v1/cameras/{id}/test` para mostrar un diagnostico RTSP accionable.
- El backend devuelve solo datos saneados del target (`host`, `port`, flags de path/query/credenciales) y nunca expone la URL RTSP desencriptada.
- Cuando el backend corre dentro de Docker, una URL RTSP con `localhost` o `127.0.0.1` se reporta explicitamente como problema de loopback del contenedor.
- Puedes ajustar el timeout del probe con `RTSP_DIAGNOSTIC_SOCKET_TIMEOUT_SECONDS`, `RTSP_DIAGNOSTIC_OPEN_TIMEOUT_MS` y `RTSP_DIAGNOSTIC_READ_TIMEOUT_MS`.

---

## 📦 Roadmap

- [x] Fase 1: Autenticación + Multi-tenant
- [x] Fase 2: Gestión de Cámaras (CRUD + RTSP)
- [x] Fase 3: Eventos + Timeline
- [x] Fase 4: Registro Facial
- [x] Fase 5: Edge Agent básico
- [x] Fase 6: Panel Admin
- [ ] Fase 7: Producción (K8s + SSL + Monitoring)

---

## 📄 Licencia

**Proprietario** - Secam © 2026

---

## 👤 Autor

**ErikING-Chile**
- GitHub: [@ErikING-Chile](https://github.com/ErikING-Chile)

---

<p align="center">
  <sub>Construido con ❤️ y Python</sub>
</p>
