#!/usr/bin/env python3
"""
Script para iniciar la aplicación FastAPI del sistema de reservas de hotel.
"""

import uvicorn
import sys
from pathlib import Path
from config import Settings

# Agregar el directorio app al path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

settings = Settings()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
    )
