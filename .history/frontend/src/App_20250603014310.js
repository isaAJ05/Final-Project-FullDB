import React, { useState } from 'react';
import './App.css';

function App() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  // Función para enviar la consulta al backend
const handleExtract = async () => {
  setError('');
  setResult(null);
  // Divide por ; y filtra vacíos
  const queries = query
    .split(';')
    .map(q => q.trim())
    .filter(q => q.length > 0);

  let lastResult = null;
  for (let q of queries) {
    try {
      const response = await fetch('http://127.0.0.1:5000/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: q })
      });
      const data = await response.json();
      if (!response.ok) {
        setError(data.error || 'Error desconocido');
        break; // Detén si hay error
      } else {
        lastResult = data;
      }
    } catch (err) {
      setError('No se pudo conectar con el backend');
      break;
    }
  }
  setResult(lastResult);
};

  return (
    <div className="app-container">
      {/* Panel principal */}
      <div className="main-content">

        {/* Zona superior (Errores + Resultado) */}
        <div className="top-section">
          <div className="errors-panel">
            {error ? error : 'Mensajes de error'}
          </div>
          <div className="results-panel">
          {result && result.columns && result.rows ? (
            <table>
              <thead>
                <tr>
                  {result.columns.map(col => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row, idx) => (
                  <tr key={idx}>
                    {result.columns.map(col => (
                      <td key={col}>{row[col]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : result && result.message ? (
            <div style={{ color: 'green', fontWeight: 'bold', padding: '10px' }}>
              {result.message}
            </div>
          ) : result ? (
                  <pre>{JSON.stringify(result, null, 2)}</pre>
                  {result ? <pre>{JSON.stringify(result, null, 2)}</pre> : null}
          ) : (
            'Aquí se mostrarán las tablas o gráficos'
          )}
        </div>
        </div>

        {/* Input de query */}
        <div className="query-input">
          <textarea
            placeholder="Escribe tu consulta aquí..."
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
          <button onClick={handleExtract} style={{ marginTop: '8px' }}>
            Extraer consulta
          </button>
        </div>

        {/* Pestañas y botones */}
        <div className="tab-bar">
          <div className="tabs">Pestañas</div>
          <div className="buttons">
            <button>+</button>
            <button>📂</button>
          </div>
        </div>
      </div>

      {/* Menú lateral derecho */}
      <div className="side-menu">
        <h3>Historial</h3>
        <ul>
          <li>SELECT * FROM usuarios</li>
          <li>DELETE FROM clientes WHERE ...</li>
          <li>UPDATE productos SET ...</li>
        </ul>
      </div>
    </div>
  );
}

export default App;