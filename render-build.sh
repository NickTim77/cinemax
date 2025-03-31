#!/usr/bin/env bash
# exit on error
set -o errexit

# ---- Instalar dependencias del sistema operativo ----
echo "--- Actualizando paquetes e instalando dependencias del sistema (ODBC)... ---"
apt-get update
# Instalar dependencias generales que pyodbc podría necesitar para compilarse y el driver manager
apt-get install -y --no-install-recommends unixodbc-dev gcc g++ build-essential
# Instalar driver ODBC de Microsoft (SIGUE LAS INSTRUCCIONES OFICIALES DE MICROSOFT PARA DEBIAN/UBUNTU)
# Los siguientes comandos son EJEMPLOS y PUEDEN CAMBIAR. Busca "Install the Microsoft ODBC driver for SQL Server (Linux)"
# Asegúrate de instalar la versión 17 o 18 según necesites.
# Ejemplo para v18 en Debian/Ubuntu (VERIFICA ESTO EN LA DOC DE MICROSOFT):
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/debian/$(lsb_release -rs)/prod.list > /etc/apt/sources.list.d/mssql-release.list
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql18 # O msodbcsql17 si prefieres esa versión

echo "--- Dependencias del sistema instaladas ---"

# ---- Instalar dependencias de Python ----
echo "--- Instalando dependencias de Python (requirements.txt)... ---"
pip install -r requirements.txt
echo "--- Dependencias de Python instaladas ---"