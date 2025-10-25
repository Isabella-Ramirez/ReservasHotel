# Etapa 1: construir dependencias con las herramientas necesarias
FROM python:3.11-slim AS builder

WORKDIR /build

# Instala toolchains y headers solo en la etapa de compilación
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia únicamente las dependencias declaradas
COPY requirements.txt .

# Compila e instala dependencias en /usr/local
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Etapa 2: imagen final, ligera y sin compiladores
FROM python:3.11-slim

# Configuración base de Python en el contenedor final
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Solo librería runtime para comunicarse con PostgreSQL
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copia los paquetes de Python instalados en la etapa builder
COPY --from=builder /usr/local /usr/local

# Copia el código y scripts necesarios para ejecutar la API
COPY app ./app
COPY scripts ./scripts
COPY config.py .
COPY start_server.py .
COPY alembic ./alembic
COPY alembic.ini .

# Crea usuario no root para mejorar seguridad
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

USER app

EXPOSE 8000

# Ejecuta la aplicación con uvicorn
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
