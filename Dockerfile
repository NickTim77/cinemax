# Usar una imagen base oficial de Python
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema Y el driver ODBC
# (Necesitarías poner aquí los comandos apt-get correctos de Microsoft
#  similares a los del render-build.sh)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gnupg unixodbc-dev gcc g++ build-essential && \
    # --- Comandos oficiales de MS para instalar msodbcsql18 ---
    # curl ... | gpg ...
    # curl ... > /etc/apt/sources.list.d/mssql-release.list
    # apt-get update && \
    # ACCEPT_EULA=Y apt-get install -y msodbcsql18 && \
    # ----------------------------------------------------------
    # Limpiar caché de apt
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la aplicación
COPY . .

# Comando para ejecutar la aplicación (Gunicorn)
# Render inyectará el puerto correcto, no necesitamos -bind aquí usualmente
CMD ["gunicorn", "--workers=4", "--timeout=600", "app:app"]
