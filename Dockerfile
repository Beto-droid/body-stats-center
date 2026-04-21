FROM python:3.13-slim

# Dependencias del sistema para Bluetooth (bleak) y compilación
RUN apt-get update && apt-get install -y \
    bluetooth \
    bluez \
    libglib2.0-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código
COPY . .

# Puerto de Streamlit
EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Arrancar el dashboard (incluye el scanner BLE en background)
CMD ["streamlit", "run", "gui.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]

