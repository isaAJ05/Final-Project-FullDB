const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const axios = require('axios');

const app = express();
const PORT = 3000;

app.use(cors());
app.use(bodyParser.json());

app.post('/api/sql', async (req, res) => {
  const { query } = req.body;

  try {
    // Enviar a backend-sql (Python)
    const response = await axios.post('http://backend-sql:5000/parse', { query });
    res.json(response.data);
  } catch (error) {
    console.error('Error al procesar SQL:', error.message);
    res.status(500).json({ error: 'Error procesando SQL' });
  }
});

app.listen(PORT, () => {
  console.log(`API corriendo en http://localhost:${PORT}`);
});
