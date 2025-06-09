
# 🧠 QueryCraft

**QueryCraft** es un motor SQL personalizado con una interfaz web intuitiva que permite a los usuarios cargar datos estructurados (como archivos CSV), ejecutar comandos SQL, y guardar datos persistentemente sin depender de motores de bases de datos tradicionales.

Este proyecto fue desarrollado como parte de una entrega para la clase de bases de datos y será desplegado en **OpenLabs@uninorte** para futuros estudiantes y desarrolladores.

---

## 🚀 ¿Qué puedes hacer con QueryCraft?

- 📄 Cargar bases de datos desde archivos CSV.
- 🧾 Ejecutar comandos SQL como `CREATE`, `INSERT`, `SELECT`, `UPDATE`, `DELETE`.
- 💾 Guardar datos de forma persistente en el backend (incluso si se apaga).
- 🧠 Validación y análisis de SQL usando `sqlglot`.
- 🌐 Interfaz moderna y responsiva con React y CodeMirror.

---

## 🛠️ Tecnologías utilizadas

- **Frontend:** React, CodeMirror, MUI, Ace Editor
- **Backend:** Flask (Python), SQLGlot, Google Auth, CORS
- **Persistencia:** Sistema personalizado de archivos
- **Contenedores:** Docker y Docker Compose

---

## 🧑‍💻 ¿Cómo correr el proyecto?

### ✅ Opción 1: Manual (Modo Desarrollo)

1. **Clona el repositorio y entra a cada carpeta:**
   ```bash
   git clone <url>
   cd backend
   ```

2. **Instala dependencias del backend:**
   ```bash
   pip install flask flask-cors sqlglot google-auth-oauthlib google-api-python-client
   python app.py
   ```

3. **Corre el frontend:**
   ```bash
   cd ../frontend
   npm install
   npm start
   ```

El frontend estará disponible en [http://localhost:3000](http://localhost:3000) y se comunicará con el backend en [http://localhost:5000](http://localhost:5000).

---

### 🐳 Opción 2: Con Docker (Recomendado para producción/OpenLabs)

> Requiere tener Docker y Docker Compose instalados.

1. **En la raíz del proyecto:**

   ```bash
   docker-compose build
   docker-compose up
   ```

2. **Accede a la app:**

   - Frontend: [http://localhost:3000](http://localhost:3000)
   - Backend: [http://localhost:5000](http://localhost:5000)

---

## 🧪 Funcionalidades clave

- ✅ Interfaz para cargar archivos `.csv` y visualizar contenido.
- ✅ Editor de SQL con resaltado de sintaxis y detección de errores.
- ✅ Ejecución de comandos SQL sobre datos cargados dinámicamente.
- ✅ Resultados en formato tabla.
- ✅ Persistencia de datos en el servidor.
- 🔐 Integración con Google Auth para futuras versiones.

---

## 🧱 Estructura del Proyecto

```
querycraft/
├── backend/            # Backend en Flask (API + lógica de SQL)
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/           # Frontend en React + CodeMirror
│   ├── src/
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml  # Orquestador de contenedores
```

---

## ⚠️ Nota para usuarios de Windows

Si encuentras errores de ejecución de scripts en PowerShell:

```powershell
Set-ExecutionPolicy RemoteSigned
# Luego escribe "Yes"
```

---

## 📚 Recursos adicionales

- [Documentación de React](https://reactjs.org/)
- [Guía de Flask](https://flask.palletsprojects.com/)
- [SQLGlot GitHub](https://github.com/tobymao/sqlglot)
- [Create React App Docs](https://facebook.github.io/create-react-app/)

---



## 🤝 Créditos

Este proyecto fue desarrollado por Sebastián Brito, Isabella Arrieta, Natalia Carpintero y Paula Nuñez para la clase de Bases de Datos en la Universidad del Norte - OpenLabs@uninorte.

---

## 🧑‍🔧 Mantenimiento futuro

Este repositorio está diseñado para facilitar su mantenimiento y extensión. El uso de Docker permite que futuros grupos lo levanten con facilidad. ¡Esperamos que QueryCraft siga creciendo con más funcionalidades como optimizadores, caché, y planes de ejecución!
