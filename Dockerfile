# Usa imagen Python slim para reducir peso
FROM python:3.11-slim

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema y Chrome
RUN apt-get update && \
    apt-get install -y wget unzip curl gnupg ca-certificates fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 libc6 libcairo2 libcups2 libdbus-1-3 \
    libexpat1 libfontconfig1 libgcc1 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 libu2f-udev libx11-6 libxcomposite1 libxcursor1 libxdamage1 \
    libxrandr2 libxss1 libxtst6 lsb-release xdg-utils chromium chromium-driver && \
    rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de la aplicación
COPY . /app

# Actualizar pip y luego instalar dependencias Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Exponer el puerto de Bokeh
EXPOSE 10000

# Comando para ejecutar la app
CMD ["bokeh", "serve", "main.py", "--port", "10000", "--allow-websocket-origin=*", "--address=0.0.0.0"]
