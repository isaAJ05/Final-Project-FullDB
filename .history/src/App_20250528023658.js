import React, { useState } from 'react';
import './App.css';

function App() {
  // Estado para el contenido del textarea
  const [query, setQuery] = useState('');

  // Función para extraer el contenido
  const handleExtract = () => {
    alert(query); // Puedes cambiar esto por console.log(query) o lo que necesites
  };

  return (
    <div className="app-container">
      {/* Panel principal */}
      <div className="main-content">

        {/* Zona superior (Errores + Resultado) */}
        <div className="top-section">
          <div className="errors-panel">Mensajes de error</div>
          <div className="results-panel">Aquí se mostrarán las tablas o gráficos</div>
        </div>

        {/* Input de query */}
        <div className="query-input">
          <textarea
            placeholder="Escribe tu consulta aquí..."
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
          {/* Botón para extraer el contenido */}
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