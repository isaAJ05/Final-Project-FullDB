import React, { useState, useEffect, useRef } from "react";
import "./App.css";
import { EditorView } from "@codemirror/view";
import { EditorState } from "@codemirror/state";
import { sql } from "@codemirror/lang-sql";
import { autocompletion } from "@codemirror/autocomplete";
import { syntaxHighlighting } from "@codemirror/language";
import { defaultHighlightStyle } from "@codemirror/language";
import { keymap } from "@codemirror/view";
import { defaultKeymap } from "@codemirror/commands";
import { oneDark } from "@codemirror/theme-one-dark";
import { lineNumbers, highlightActiveLine } from "@codemirror/view";

import { createTheme } from '@uiw/codemirror-themes';

import { tags as t } from '@lezer/highlight';

const myTheme = createTheme({
  theme: 'light',
  settings: {
    background: '#181c27',
    backgroundImage: '',
    foreground: '#75baff',
    caret: '#ffffff',
    selection: '#036dd626',
    selectionMatch: '#036dd626',
    lineHighlight: '#181c27', 
    gutterBorder: 'transparent', // Elimina la línea blanca en el gutter
    gutterBackground: '#181c27', // Cambia el fondo de la columna de enumerado
    gutterForeground: '#9b0018', // Cambia el color de los números de línea
  },
  styles: [
    { tag: t.comment, color: '#787b8099' },
    { tag: t.variableName, color: '#0080ff' },
    { tag: [t.string, t.special(t.brace)], color: '#e17e00' },
    { tag: t.number, color: '#5c6166' },
    { tag: t.bool, color: '#5c6166' },
    { tag: t.null, color: '#5c6166' },
    { tag: t.keyword, color: '#9b0018' },
    { tag: t.operator, color: '#00aed5' },
    { tag: t.className, color: '#5c6166' },
    { tag: t.definition(t.typeName), color: '#5c6166' },
    { tag: t.typeName, color: '#5c6166' },
    { tag: t.angleBracket, color: '#ffffff' },
    { tag: t.tagName, color: '#5c6166' },
    { tag: t.attributeName, color: '#5c6166' },
  ],
});


function SqlEditor({ query, setQuery }) {
  const editorRef = useRef(null);
  const viewRef = useRef(null);

  useEffect(() => {
    if (!editorRef.current) return;

    const view = new EditorView({
      state: EditorState.create({
        doc: query,
        extensions: [
          sql(),
          keymap.of(defaultKeymap),
          myTheme,
          syntaxHighlighting(defaultHighlightStyle),
          lineNumbers(), // Mostrar líneas enumeradas
          highlightActiveLine(), // Resalta la línea activa
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              setQuery(update.state.doc.toString());
            }
          }),
        ],
      }),
      parent: editorRef.current,
    });

    viewRef.current = view;

    return () => view.destroy();
  }, []);

  return <div ref={editorRef} className="sql-editor-container" />;
}

function App() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [history, setHistory] = useState([]);
  const [leftWidth, setLeftWidth] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  // Nuevo estado para bases de datos y tablas
  const [databases, setDatabases] = useState([]);
  const [tablesByDb, setTablesByDb] = useState({});
  const [expandedDb, setExpandedDb] = useState(null);
  const [isDbListOpen, setIsDbListOpen] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [selectedDb, setSelectedDb] = useState("");
  const [newDb, setNewDb] = useState("");
  const [tableName, setTableName] = useState("");
  const [csvFile, setCsvFile] = useState(null);


  // Obtener bases de datos al montar
  useEffect(() => {
    fetch('http://127.0.0.1:5000/databases')
      .then(res => res.json())
      .then(data => setDatabases(data.databases || []))
      .catch(() => setDatabases([]));
  }, []);

    // Obtener tablas de una base de datos al expandirla
  const handleExpandDb = (db) => {
    if (expandedDb === db) {
      setExpandedDb(null);
      return;
    }
    setExpandedDb(db);
    if (!tablesByDb[db]) {
      fetch(`http://127.0.0.1:5000/tables?db=${db}`)
        .then(res => res.json())
        .then(data => setTablesByDb(prev => ({ ...prev, [db]: data.tables || [] })))
        .catch(() => setTablesByDb(prev => ({ ...prev, [db]: [] })));
    }
  };
  
  const handleUploadCsv = async () => {
  const dbToUse = newDb || selectedDb;
  if (!dbToUse || !tableName || !csvFile) {
    setError("Debes seleccionar o crear una base, poner nombre de tabla y elegir archivo.");
    return;
  }
  const formData = new FormData();
  formData.append("db", dbToUse);
  formData.append("table", tableName);
  formData.append("file", csvFile);

  const res = await fetch("http://127.0.0.1:5000/upload_csv", {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) setError(data.error || "Error al subir CSV");
  else setResult(data);
  setShowUpload(false);
};

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

  const startDragging = () => setIsDragging(true);
  const stopDragging = () => setIsDragging(false);

  const handleDragging = (e) => {
    if (!isDragging) return;
    const container = document.querySelector(".main-content");
    const containerWidth = container.offsetWidth;
    const newLeftWidth = (e.clientX / containerWidth) * 100;
    if (newLeftWidth > 10 && newLeftWidth < 90) {
      setLeftWidth(newLeftWidth);
    }
  };

  useEffect(() => {
    window.addEventListener("mousemove", handleDragging);
    window.addEventListener("mouseup", stopDragging);
    return () => {
      window.removeEventListener("mousemove", handleDragging);
      window.removeEventListener("mouseup", stopDragging);
    };
  }, [isDragging]);

  return (
    <div className={`app-container ${isHistoryOpen ? "history-open" : ""}`}>
      <nav className="navbar">
        <button
          className="toggle-history-btn"
          onClick={() => setIsHistoryOpen(!isHistoryOpen)}
        >
          {isHistoryOpen ? "✖" : "☰"}
        </button>
        <h1>Consultas SQL</h1>
      </nav>

      <aside className={`side-menu ${isHistoryOpen ? "open" : ""}`}>
        {/* Título principal */}
           <div style={{ color: "#fff", marginBottom: 30 }}>
              
         <h1><span>🖥️ </span>localhost</h1>
        </div>
      

        {/* Carpeta Databases */}
        <button
          className="history-btn"
          style={{
            fontWeight: "bold",
            background: isDbListOpen ? "#22263a" : undefined,
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: "1.1em",
            marginBottom: 8
          }}
          onClick={() => setIsDbListOpen(!isDbListOpen)}
          title="Mostrar bases de datos"
        >
          <span style={{ fontSize: 18 }}>{isDbListOpen ? "📂" : "📁"}</span>
          Databases
        </button>


        {/* Lista de bases de datos y tablas */}
        {isDbListOpen && (
        <div style={{ marginLeft: 16, borderLeft: "2px solid #333", paddingLeft: 8 }}>
          {databases.length === 0 ? (
            <p style={{ fontSize: "0.95em" }}>No hay bases de datos.</p>
          ) : (
            databases.map((db) => (
              <div key={db}>
                <button
                  className="history-btn"
                  style={{
                    fontWeight: expandedDb === db ? "bold" : "normal",
                    background: expandedDb === db ? "#23263a" : undefined,
                    display: "flex",
                    alignItems: "center",
                    gap: 6
                  }}
                  onClick={() => setExpandedDb(expandedDb === db ? null : db)}
                  title={`Ver tablas de ${db}`}
                >
                  <span style={{ fontSize: 16 }}>
                    {expandedDb === db ? "📂" : "📁"}
                  </span>
                  {db}
                </button>
                {expandedDb === db && (
                  <div style={{ marginLeft: 16, borderLeft: "2px solid #333", paddingLeft: 8 }}>
                    {tablesByDb[db] && tablesByDb[db].length > 0 ? (
                      tablesByDb[db].map((table) => (
                        <button
                          key={table}
                          className="history-btn"
                          style={{
                            fontSize: "0.95em",
                            background: "#23263a",
                            margin: "3px 0",
                            display: "flex",
                            alignItems: "center",
                            gap: 6
                          }}
                          onClick={() => handleExpandDb(db)}
                          title={`Ver datos de ${d}`}
                        >
                          <span style={{ fontSize: 15 }}>🗒️</span>
                          {table}
                        </button>
                      ))
                    ) : (
                      <p style={{ fontSize: "0.9em" }}>No hay tablas.</p>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      </aside>

      <div className="main-content">
        <div className="left-panel" style={{ width: `${leftWidth}%` }}>
          <div className="query-input">
            <SqlEditor query={query} setQuery={setQuery} />
            <div className="buttons-row">
              <button onClick={handleExtract} style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 3v18l15-9-15-9z" /></svg>

              </button>
              <label   htmlFor="upload-csv"
                className="upload-btn"
                style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}
                onClick={() => setShowUpload(true)}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V4" /></svg>

              </label>
              <input
                type="file"
                id="upload-csv"
                accept=".csv"
                style={{ display: 'none' }}
                onChange={e => setCsvFile(e.target.files[0])}
              />
              
              {showUpload && (
                <div className="modal-bg">
                  <div className="modal">
                    <h3>Subir CSV</h3>
                    <div>
                      <label>Base de datos existente:</label>
                      <select value={selectedDb} onChange={e => setSelectedDb(e.target.value)}>
                        <option value="">-- Selecciona --</option>
                        {databases.map(db => <option key={db} value={db}>{db}</option>)}
                      </select>
                    </div>
                    <div>
                      <label>O crea nueva base:</label>
                      <input value={newDb} onChange={e => setNewDb(e.target.value)} placeholder="Nueva base" />
                    </div>
                    <div>
                      <label>Nombre de la tabla:</label>
                      <input value={tableName} onChange={e => setTableName(e.target.value)} placeholder="Nombre tabla" />
                    </div>
                    <div>
                      <label>Archivo CSV:</label>
                      <input type="file" accept=".csv" onChange={e => setCsvFile(e.target.files[0])} />
                    </div>
                    <button onClick={handleUploadCsv}>Subir</button>
                    <button onClick={() => setShowUpload(false)}>Cancelar</button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="resizer" onMouseDown={startDragging} />

        <div className="right-panel" style={{ width: `${100 - leftWidth}%` }}>
          <div className="top-section">
            <div className="results-panel">
              {result && result.columns && result.rows ? (
                <table>
                  <thead>
                    <tr>
                      {result.columns.map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row, idx) => (
                      <tr key={idx}>
                        {result.columns.map((col) => (
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
                "Tablas y Resultados."
              )}
            </div>

            <div className="errors-panel">{error ? error : "Output"}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;