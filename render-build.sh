#!/usr/bin/env bash
# Indica a Render que use Bash y que falle si un comando falla
set -o errexit

echo "--- [Build Script] Actualizando paquetes e instalando dependencias base (curl, gnupg, odbc)... ---"
apt-get update -y # Actualiza la lista de paquetes disponibles
# Instala herramientas necesarias para añadir repositorios y para pyodbc
apt-get install -y --no-install-recommends curl apt-transport-https gnupg unixodbc-dev gcc g++ build-essential

echo "--- [Build Script] Instalando Driver MS ODBC 17 (¡VERIFICAR COMANDOS OFICIALES!)... ---"
# --------------------------------------------------------------------------
# --- ¡¡IMPORTANTE!! ---
# --- Busca en Google "Install Microsoft ODBC driver 18 Linux Ubuntu" ---
# --- Ve a la página OFICIAL de Microsoft y copia/pega aquí los comandos ---
# --- EXACTOS y ACTUALIZADOS para Ubuntu (o Debian si aplica).             ---
# --- Los siguientes son solo un EJEMPLO y pueden cambiar.                ---
# --- Asegúrate de incluir ACCEPT_EULA=Y donde sea necesario.            ---
# --------------------------------------------------------------------------
# Ejemplo de Comandos (¡NO USAR SIN VERIFICARLOS EN LA DOC OFICIAL!):
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
# Asegúrate que la URL de config sea para la versión correcta de Debian/Ubuntu que usa Render
curl -fsSL https://packages.microsoft.com/config/debian/11/prod.list | tee /etc/apt/sources.list.d/mssql-release.list
apt-get update -y
ACCEPT_EULA=Y apt-get install -y msodbcsql17 # O msodbcsql17 si prefieres

# --------------------------------------------------------------------------
echo "--- [Build Script] Instalación del Driver MS ODBC intentada ---"

echo "--- [Build Script] Instalando dependencias de Python (requirements.txt)... ---"
pip install -r requirements.txt
echo "--- [Build Script] Dependencias de Python instaladas ---"

echo "--- [Build Script] Script completado ---"
