# Priorum – Daily OS

Aplicación de gestión de tareas y calendario con agente IA integrado.

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | React 18 + Vite |
| Backend | Python 3.12 + FastAPI |
| Tareas | Notion API |
| Calendario | Microsoft Graph API (Outlook / Teams) |
| Agente IA | OpenAI GPT-4o |
| Contenedores | Docker + Docker Compose |
| Base de datos | MongoDB |

## Estructura del proyecto

```
Priorum/
├── frontend/                  # React + Vite
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── agent/         # Panel del agente IA
│   │   │   ├── calendar/      # Vista de calendario
│   │   │   ├── common/        # Componentes reutilizables
│   │   │   ├── layout/        # Sidebar, Topbar
│   │   │   ├── priority/      # Vista de prioridades
│   │   │   └── tasks/         # Vista de tareas
│   │   ├── constants/         # Colores y estilos
│   │   ├── hooks/             # useTasks, useCalendar, useAgent
│   │   └── services/          # Llamadas a la API
│   └── package.json
│
├── backend/                   # FastAPI (Python)
│   ├── main.py                # Punto de entrada
│   └── app/
│       ├── config.py          # Configuración (pydantic-settings)
│       ├── models/            # Pydantic models: task, event, agent
│       ├── routers/           # Endpoints: /tasks, /calendar, /agent
│       ├── services/          # Integraciones: Notion, Outlook, OpenAI
│       └── db.py              # Conexión a MongoDB
│
├── .env.example               # Plantilla de variables de entorno
├── docker-compose.yml
└── README.md
```

## Inicio rápido

### 1. Configurar variables de entorno

```bash
cp .env.example .env
# Edita .env con tus credenciales de Notion, Microsoft y OpenAI
# Añade también:
MONGO_URI=mongodb://priorum-mongodb:27017
MONGO_DB=priorum
```

### 2. Backend (Python)

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

La API estará disponible en `http://localhost:8000/api`  
Documentación interactiva: `http://localhost:8000/api/docs`

### 3. Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

La app estará disponible en `http://localhost:3000`

### 4. Levantar MongoDB con Docker Compose

1. **Instalar Docker Desktop**  
   Asegúrate de tener Docker Desktop instalado y en ejecución.

2. **Levantar el servicio MongoDB**  
   Desde la carpeta `Priorum` ejecuta:
   ```bash
   docker compose up -d mongodb
   ```

3. **Verificar estado**  
   Comprueba que el servicio está corriendo:
   ```bash
   docker compose ps
   ```
   Debes ver `priorum-mongodb` con estado `Up`.

4. **Conexión desde el backend**  
   El backend ya está configurado para conectarse automáticamente a MongoDB usando `motor`.  
   Puedes acceder a colecciones con:
   ```python
   from app.db import get_collection
   col = get_collection("mi_coleccion")
   ```

### 5. Levantar todos los servicios

```bash
docker compose up --build
```

## Funcionalidades

- **Prioridades del día**: el agente IA analiza tareas y reuniones y genera un orden recomendado
- **Tareas**: sincronizadas con Notion, filtro por día / semana / mes / año y por prioridad
- **Calendario**: sincronizado con Outlook/Teams, vista timeline con filtro de período
- **Agente IA**: chat en lenguaje natural para consultar tareas, reuniones y obtener sugerencias de horario
- **Base de datos MongoDB**: almacenamiento flexible de datos de IA y tareas

## Modo demo (sin credenciales)

Si no se configuran las variables de entorno, el backend devuelve datos de ejemplo para que puedas desarrollar el frontend sin necesidad de cuentas externas.

## Integraciones

### Notion
1. Crea una integración en https://www.notion.so/my-integrations
2. Comparte la base de datos de tareas con la integración
3. Copia el token y el ID de la base de datos en `.env`

### Microsoft Graph (Outlook)
1. Registra una app en Azure Active Directory
2. Añade el permiso `Calendars.ReadWrite` (Application)
3. Crea un client secret
4. Rellena `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET` y `MS_USER_EMAIL` en `.env`

### OpenAI
1. Obtén una API key en https://platform.openai.com/api-keys
2. Añade `OPENAI_API_KEY` en `.env`