// backend-api/server.js
const express = require('express');
const axios = require('axios');
const cors = require('cors');

const app = express();
const PORT = 8000;

app.use(cors());
app.use(express.json());

// Ruta principal que recibe la consulta SQL
app.post('/execute', async (req, res) => {
  const { query } = req.body;

  try {
    // Llama al backend de Python (asume que corre en http://backend-sql:5000)
    const response = await axios.post('http://backend-sql:5000/parse', { query });

    res.json(response.data); // Enviar resultado al frontend
  } catch (error) {
    console.error('Error comunicando con backend-sql:', error.message);
    res.status(500).json({ error: 'Error procesando la consulta' });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 API server running at http://localhost:${PORT}`);
});
