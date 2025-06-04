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

import { createTheme } from '@uiw/codemirror-themes';

import { tags as t } from '@lezer/highlight';

const myTheme = createTheme({
  theme: 'light',
  settings: {
    background: '#ffffff',
    backgroundImage: '',
    foreground: '#75baff',
    caret: '#ffffff',
    selection: '#036dd626',
    selectionMatch: '#036dd626',
    lineHighlight: '#8a91991a',
    gutterBorder: '1px solid #ffffff10',
    gutterBackground: '#fff',
    gutterForeground: '#8a919966',
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
        <h3>Historial</h3>
        <button
          className="history-btn"
          onClick={() => setQuery("SELECT * FROM productos LIMIT 10")}
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
              onClick={() => setQuery(item)}
              title="Copiar consulta al área de texto"
            >
              {item.length > 30 ? item.substring(0, 27) + "..." : item}
            </button>
          ))
        )}
      </aside>

      <div className="main-content">
        <div className="left-panel" style={{ width: `${leftWidth}%` }}>
          <div className="query-input">
            <SqlEditor query={query} setQuery={setQuery} />
            <div className="buttons-row">
              <button onClick={handleExtract}>Extraer consulta</button>
              <label htmlFor="upload-csv" className="upload-btn">
                Subir CSV
              </label>
              <input type="file" id="upload-csv" accept=".csv" />
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