# backend/Dockerfile - Container optimizado para Marruecos

FROM python:3.11-slim

# Información del maintainer
LABEL maintainer="Sistema Judicial Digital - Marruecos"
LABEL version="1.0.0"
LABEL description="Backend API para digitalización judicial en Marruecos"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Crear usuario no-root para seguridad
RUN groupadd --gid 1000 justicia && \
    useradd --uid 1000 --gid justicia --shell /bin/bash --create-home justicia

# Instalar dependencias del sistema optimizadas para Marruecos
RUN apt-get update && apt-get install -y \
    # OCR y procesamiento de imágenes
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-fra \
    tesseract-ocr-spa \
    libtesseract-dev \
    poppler-utils \
    # Procesamiento de archivos
    libmagic1 \
    libmagic-dev \
    # Dependencias de Python
    gcc \
    g++ \
    pkg-config \
    # Herramientas de red
    curl \
    wget \
    # ImageMagick para procesamiento avanzado
    imagemagick \
    libmagickwand-dev \
    # Fonts para documentos árabes
    fonts-noto \
    fonts-liberation \
    fonts-dejavu-core \
    # PKCS#11 para HSM
    libengine-pkcs11-openssl \
    opensc \
    openssl \
    # Herramientas de desarrollo
    git \
    # Limpieza
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configurar Tesseract para idiomas de Marruecos
RUN echo 'ara+fra+spa' > /etc/tesseract-ocr-config.txt

# Configurar ImageMagick policy para PDFs (si existe el archivo)
RUN if [ -f /etc/ImageMagick-6/policy.xml ]; then \
        sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml; \
    fi

# Crear directorios de la aplicación
RUN mkdir -p /app/uploads /app/logs /app/temp /app/hsm && \
    chown -R justicia:justicia /app

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Cambiar ownership al usuario justicia
RUN chown -R justicia:justicia /app

# Cambiar a usuario no-root
USER justicia

# Crear directorios necesarios para el usuario
RUN mkdir -p /home/justicia/.cache

# Configurar PATH
ENV PATH="/home/justicia/.local/bin:$PATH"

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
