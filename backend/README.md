# Hotel Reservations API

## Descripción General

**Hotel Reservations API** es una API RESTful desarrollada con **FastAPI** y **SQLAlchemy** que permite gestionar reservas de hotel de manera eficiente y automatizada. La API proporciona endpoints completos para la gestión de huéspedes, habitaciones y reservas, con validaciones automáticas y documentación interactiva.

### Problema que resuelve:
- **Automatización completa** de la gestión de reservas y disponibilidad de habitaciones
- **Prevención de conflictos** de reservas duplicadas o habitaciones no disponibles
- **Administración centralizada** de huéspedes, habitaciones y reservas
- **Cálculo automático** del costo total de las reservas
- **Validaciones robustas** de fechas y disponibilidad
- **Documentación interactiva** con Swagger UI

### Características principales:
- **API RESTful** con FastAPI
- **Base de datos** con SQLAlchemy ORM
- **Validaciones** con Pydantic
- **Documentación automática** con Swagger/OpenAPI
- **Migración automática** de base de datos
- **Datos de prueba** incluidos
- **Manejo de errores** robusto

---

## Arquitectura del Proyecto

```
03-ReservasHotel/
│
├─ app/
│   ├─ database.py            # Conexión y configuración de SQLAlchemy
│   ├─ main.py                # Inicialización de FastAPI y routers
│   ├─ models/                # Modelos de datos (SQLAlchemy + Pydantic)
│   │   ├─ guest.py          # Modelo de huéspedes
│   │   ├─ room.py           # Modelo de habitaciones
│   │   └─ reservation.py    # Modelo de reservas
│   └─ endpoints/             # Rutas de la API
│       ├─ guests.py         # Endpoints de huéspedes
│       ├─ rooms.py          # Endpoints de habitaciones
│       └─ reservations.py   # Endpoints de reservas
│
├─ scripts/
│   └─ migrate_database.py    # Script de migración y datos de prueba
│
├─ config.py                  # Configuración de la aplicación
├─ start_server.py           # Script para iniciar el servidor
├─ requirements.txt          # Dependencias del proyecto
└─ README.md                 # Este archivo
```

---

## Instalación y Configuración

### Prerrequisitos
- Python 3.8 o superior
- Base de datos SQL Server (o compatible con pyodbc)

### 1. Clonar el repositorio
```bash
git clone https://github.com/Isabella-Ramirez/MiprimerApi
cd 03-ReservasHotel
```

### 2. Crear entorno virtual
```bash
python -m venv venv
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Crear un archivo `.env` en la raíz del proyecto:
```env
DATABASE_URL=mssql+pyodbc://username:password@server:port/database?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes&Encrypt=yes
RELOAD=true
```

### 5. Ejecutar migración de base de datos
```bash
python scripts/migrate_database.py
```

### 6. Iniciar el servidor
```bash
python start_server.py
# O alternativamente:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Uso de la API

### Acceso a la documentación
Una vez iniciado el servidor, puedes acceder a:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Endpoint principal
```
GET /
```
Respuesta:
```json
{
  "message": "Bienvenido a la API de Reservas de Hotel. Visita /docs para ver la documentación.",
  "endpoints": ["/guests", "/rooms", "/reservations"]
}
```

---

## Modelos de Datos

### Huésped (Guest)
```json
{
  "id": 1,
  "name": "Juan Pérez",
  "email": "juan.perez@email.com",
  "phone": "1234567890",
  "is_active": true,
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

### Habitación (Room)
```json
{
  "id": 1,
  "room_number": "101",
  "room_type": "Single",
  "price_per_night": 50.00,
  "is_available": true,
  "is_active": true,
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

### Reserva (Reservation)
```json
{
  "id": 1,
  "guest_id": 1,
  "room_id": 1,
  "check_in_date": "2024-12-01",
  "check_out_date": "2024-12-03",
  "total_amount": 100.00,
  "status": "confirmed",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

---

## Endpoints Disponibles

### Gestión de Huéspedes (`/guests`)
- `GET /guests` - Listar todos los huéspedes
- `GET /guests/{id}` - Obtener huésped por ID
- `POST /guests` - Crear nuevo huésped
- `PUT /guests/{id}` - Actualizar huésped
- `DELETE /guests/{id}` - Eliminar huésped (soft delete)

### Gestión de Habitaciones (`/rooms`)
- `GET /rooms` - Listar todas las habitaciones
- `GET /rooms/{id}` - Obtener habitación por ID
- `GET /rooms/available` - Listar habitaciones disponibles
- `POST /rooms` - Crear nueva habitación
- `PUT /rooms/{id}` - Actualizar habitación
- `DELETE /rooms/{id}` - Eliminar habitación (soft delete)

### Gestión de Reservas (`/reservations`)
- `GET /reservations` - Listar todas las reservas
- `GET /reservations/{id}` - Obtener reserva por ID
- `GET /reservations/guest/{guest_id}` - Reservas de un huésped
- `GET /reservations/room/{room_id}` - Reservas de una habitación
- `POST /reservations` - Crear nueva reserva
- `PUT /reservations/{id}` - Actualizar reserva
- `DELETE /reservations/{id}` - Cancelar reserva

---

## Ejemplos de Uso

### Crear un huésped
```bash
curl -X POST "http://localhost:8000/guests" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "María García",
       "email": "maria.garcia@email.com",
       "phone": "0987654321"
     }'
```

### Crear una habitación
```bash
curl -X POST "http://localhost:8000/rooms" \
     -H "Content-Type: application/json" \
     -d '{
       "room_number": "301",
       "room_type": "Suite",
       "price_per_night": 150.00,
       "is_available": true
     }'
```

### Crear una reserva
```bash
curl -X POST "http://localhost:8000/reservations" \
     -H "Content-Type: application/json" \
     -d '{
       "guest_id": 1,
       "room_id": 1,
       "check_in_date": "2024-12-15",
       "check_out_date": "2024-12-17"
     }'
```

---

## Base de Datos

### Estructura de tablas
- **guests**: Información de huéspedes
- **rooms**: Información de habitaciones
- **reservations**: Información de reservas

### Datos de prueba
El script de migración incluye datos de prueba:
- 4 huéspedes de ejemplo
- 6 habitaciones (Single, Double, Suite)
- 4 reservas de ejemplo

### Estados de reserva
- `pending`: Pendiente de confirmación
- `confirmed`: Confirmada
- `cancelled`: Cancelada
- `completed`: Completada

---

## Tecnologías Utilizadas

- **FastAPI**: Framework web moderno y rápido
- **SQLAlchemy**: ORM para Python
- **Pydantic**: Validación de datos
- **Uvicorn**: Servidor ASGI
- **Python-dotenv**: Manejo de variables de entorno
- **PyODBC**: Conector para SQL Server

---

## Notas de Desarrollo

### Validaciones implementadas
- Fechas de salida posteriores a fechas de entrada
- Emails únicos para huéspedes
- Números de habitación únicos
- Precios positivos
- Longitud de campos según especificaciones



---


## Autor

Miguel Ángel Lopez Perdomo — miguellopez265477@correo.itm.edu.co
Isabella Ramirez Ciro — isabellaramirez1116480@correo.itm.edu.co

---