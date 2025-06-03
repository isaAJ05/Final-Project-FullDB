import React, { useState, useEffect } from 'react';
import './App.css';
import AceEditor from "react-ace";

// Importar modo SQL y tema
import "ace-builds/src-noconflict/mode-sql";
import "ace-builds/src-noconflict/theme-monokai";

function App() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [history, setHistory] = useState([]);
  const [leftWidth, setLeftWidth] = useState(50); // in percent
  const [isDragging, setIsDragging] = useState(false);

  const handleExtract = async () => {
    setError('');
    setResult(null);
    try {
      const response = await fetch('http://127.0.0.1:5000/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query })
      });
      const data = await response.json();
      if (!response.ok) {
        setError(data.error || 'Error desconocido');
      } else {
        setResult(data);
        if (query.trim() !== '') {
          setHistory(prev => {
            if (prev.length === 0 || prev[prev.length - 1] !== query) {
              return [...prev, query];
            }
            return prev;
          });
        }
      }
    } catch (err) {
      setError('No se pudo conectar con el backend');
    }
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;
    if (!file.name.endsWith('.csv')) {
      alert('Por favor, selecciona un archivo CSV válido.');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target.result;
      const lines = text.trim().split('\n');
      const columns = lines[0].split(',');
      const rows = lines.slice(1).map(line => {
        const values = line.split(',');
        const rowObj = {};
        columns.forEach((col, idx) => {
          rowObj[col.trim()] = values[idx]?.trim() || '';
        });
        return rowObj;
      });
      setResult({ columns, rows });
    };
    reader.readAsText(file);
  };

  const handleHistoryClick = (item) => {
    setQuery(item);
    setIsHistoryOpen(false);
  };

  // Resizer handlers
  const startDragging = () => setIsDragging(true);
  const stopDragging = () => setIsDragging(false);

  const handleDragging = (e) => {
    if (!isDragging) return;
    const container = document.querySelector('.main-content');
    const containerWidth = container.offsetWidth;
    const newLeftWidth = (e.clientX / containerWidth) * 100;
    if (newLeftWidth > 10 && newLeftWidth < 90) {
      setLeftWidth(newLeftWidth);
    }
  };

  useEffect(() => {
    window.addEventListener('mousemove', handleDragging);
    window.addEventListener('mouseup', stopDragging);
    return () => {
      window.removeEventListener('mousemove', handleDragging);
      window.removeEventListener('mouseup', stopDragging);
    };
  }, [isDragging]);

  return (
    <div className={`app-container ${isHistoryOpen ? 'history-open' : ''}`}>
      {/* Navbar */}
      <nav className="navbar">
        <button className="toggle-history-btn" onClick={() => setIsHistoryOpen(!isHistoryOpen)}>
          {isHistoryOpen ? '✖' : '☰'}
        </button>
        <h1>Consultas SQL</h1>
      </nav>

      {/* Sidebar - Historial */}
      <aside className={`side-menu ${isHistoryOpen ? 'open' : ''}`}>
        <h3>Historial</h3>
        <button
          className="history-btn"
          onClick={() => handleHistoryClick('SELECT * FROM productos LIMIT 10')}
        >
          Query de prueba
        </button>
        {history.length === 0 ? (
          <p>No hay consultas en el historial.</p>
        ) : (
          history.map((item, idx) => (
            <button
              key={idx}
              className="history-btn"
              onClick={() => handleHistoryClick(item)}
              title="Copiar consulta al área de texto"
            >
              {item.length > 30 ? item.substring(0, 27) + '...' : item}
            </button>
          ))
        )}
      </aside>

      {/* Contenido principal */}
      <div className="main-content">
        <div className="left-panel" style={{ width: `${leftWidth}%` }}>
          <div className="query-input">
            <textarea
              placeholder="Escribe tu consulta aquí..."
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
            <div className="buttons-row">
              <button onClick={handleExtract}>Extraer consulta</button>
              <label htmlFor="upload-csv" className="upload-btn" title="Subir archivo CSV">
                Subir CSV
              </label>
              <input
                type="file"
                id="upload-csv"
                accept=".csv"
                onChange={handleFileUpload}
              />
            </div>
          </div>
        </div>

        <div
          className="resizer"
          onMouseDown={startDragging}
        />

        <div className="right-panel" style={{ width: `${100 - leftWidth}%` }}>
          <div className="top-section">
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
                <div className="message-success">{result.message}</div>
              ) : result ? (
                <pre>{JSON.stringify(result, null, 2)}</pre>
              ) : (
                'Tablas y Resultados.'
              )}
            </div>

            <div className="errors-panel">
              {error ? error : 'Output'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
