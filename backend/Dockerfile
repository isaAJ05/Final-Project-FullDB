# Imagen base oficial de Python
FROM python:3.10-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar los archivos de la app
COPY . .

# Instalar las dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar las dependencias de Python
RUN pip install --upgrade pip

# Crear requirements.txt automáticamente si no existe
# Puedes saltarte esto si ya tienes un requirements.txt
# Si no tienes uno, puedes usar este comando en local:
# pip freeze > requirements.txt

COPY requirements.txt .

RUN pip install -r requirements.txt

# Exponer el puerto por el que Flask corre por defecto
EXPOSE 5000

# Comando para correr la app
CMD ["python", "app.py"]
