FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos del backend al contenedor
COPY . .

# Instala las dependencias
RUN pip install --no-cache-dir flask sqlparse

# Expone el puerto 5000
EXPOSE 5000

# Crea la carpeta de datos para persistencia
RUN mkdir -p /app/data

# Comando para ejecutar la app
CMD ["python", "app.py"]