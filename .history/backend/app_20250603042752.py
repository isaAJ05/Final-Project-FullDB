#==========================
#IMPORTACIONES Y CONFIGURACIÓN
#==========================
from flask import Flask, request, jsonify
import sqlglot
import json
import os
import re
import csv
from io import StringIO
import datetime
import shutil
from flask_cors import CORS

#==========================
CONSTANTES Y APP FLASK
==========================
app = Flask(name)
CORS(app)
DATA_DIR = "data"

==========================
FUNCIONES UTILITARIAS
==========================
def save_table(db, table, data):
os.makedirs(os.path.join(DATA_DIR, db), exist_ok=True)
with open(os.path.join(DATA_DIR, db, f"{table}.json"), "w") as f:
json.dump(data, f)

def is_valid_name(name):
return re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name) is not None

def load_table(db, table):
try:
with open(os.path.join(DATA_DIR, db, f"{table}.json"), "r") as f:
return json.load(f)
except FileNotFoundError:
return []

def backup_table(db, table, data):
backup_dir = os.path.join(DATA_DIR, db, "backups")
os.makedirs(backup_dir, exist_ok=True)
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = os.path.join(backup_dir, f"{table}_{timestamp}.json")
with open(backup_file, "w") as f:
json.dump(data, f)

def parse_db_table(full_name):
parts = full_name.split('.')
if len(parts) == 2:
return parts[0], parts[1]
return None, parts[0]

==========================
CACHE DE RESULTADOS DE CONSULTAS
==========================
query_cache = {}

==========================
CICLO DE VIDA DE UNA CONSULTA SQL
==========================
def parser(query):
"""Etapa 1: Parser - Analiza y valida la sintaxis SQL."""
parsed = sqlglot.parse(query)
if not parsed or len(parsed) == 0:
raise ValueError("Consulta SQL vacía o inválida")
return parsed[0]

def algebrizer(stmt):
"""Etapa 2: Algebrizer - Extrae tipo de sentencia usando sqlglot."""
return stmt.key.upper() # Por ejemplo: 'SELECT', 'INSERT', etc.

def optimizer(stmt_type, query):
"""Etapa 3: Optimizer/Planner - Usa caché para SELECT, plan simple para otros."""
if stmt_type == "SELECT" and query in query_cache:
return {"plan": "cache", "cached_result": query_cache[query]}
return {"plan": "execute", "query": query}

def executor(plan, stmt_type, query, data):
"""Etapa 4: Executor - Ejecuta el plan (toda tu lógica real aquí)."""
# SELECT con caché
if plan.get("plan") == "cache":
return {"source": "cache", **plan["cached_result"]}

==========================
ENDPOINT PRINCIPAL: EJECUCIÓN DE SQL (modularizado)
==========================
@app.route('/execute', methods=['POST'])
def execute_sql():
"""
Recibe una consulta SQL y ejecuta todas las etapas del ciclo de vida:
Parser -> Algebrizer -> Optimizer/Planner -> Executor (con caché)
"""
data = request.json
query = data.get('query', '').strip()
try:
# 1. Parser
stmt = parser(query)
# 2. Algebrizer
stmt_type = algebrizer(stmt)
if stmt_type not in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'COMMAND']:
return jsonify({'error': f'Tipo de consulta no soportado: {stmt_type}'}), 400
# 3. Optimizer/Planner (incluye caché)
plan = optimizer(stmt_type, query)
# 4. Executor
result = executor(plan, stmt_type, query, data)
return jsonify(result)
except Exception as e:
return jsonify({'error': str(e)}), 400

==========================
ENDPOINTS DE ADMINISTRACIÓN
==========================
@app.route('/backups', methods=['GET'])
def list_backups():
"""Lista los respaldos de una tabla."""
db = request.args.get('db')
table = request.args.get('table')
backup_dir = os.path.join(DATA_DIR, db, "backups")
if not os.path.exists(backup_dir):
return jsonify({'backups': []})
files = [f for f in os.listdir(backup_dir) if f.startswith(table)]
return jsonify({'backups': files})

@app.route('/restore_backup', methods=['POST'])
def restore_backup():
"""Restaura un respaldo de una tabla."""
data = request.json
db = data.get('db')
table = data.get('table')
backup_file = data.get('backup_file')
backup_path = os.path.join(DATA_DIR, db, "backups", backup_file)
if not os.path.exists(backup_path):
return jsonify({'error': 'Backup no encontrado'}), 404
with open(backup_path, "r") as f:
backup_data = json.load(f)
save_table(db, table, backup_data)
return jsonify({'message': f'Respaldo restaurado para {table} en {db}'})

@app.route('/databases', methods=['GET'])
def list_databases():
"""Lista todas las bases de datos."""
dbs = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
return jsonify({'databases': dbs})

@app.route('/drop_database', methods=['POST'])
def drop_database():
"""Elimina una base de datos y todas sus tablas."""
data = request.json
db = data.get('db')
db_path = os.path.join(DATA_DIR, db)
if not db or not is_valid_name(db):
return jsonify({'error': 'Nombre de base de datos inválido'}), 400
if not os.path.exists(db_path):
return jsonify({'error': f'La base de datos {db} no existe'}), 400
shutil.rmtree(db_path)
query_cache.clear()
return jsonify({'message': f'Base de datos {db} eliminada'})

@app.route('/tables', methods=['GET'])
def list_tables():
"""Lista todas las tablas de una base de datos."""
db = request.args.get('db')
db_path = os.path.join(DATA_DIR, db)
if not db or not is_valid_name(db):
return jsonify({'error': 'Nombre de base de datos inválido'}), 400
if not os.path.exists(db_path):
return jsonify({'error': f'La base de datos {db} no existe'}), 400
tables = [f[:-5] for f in os.listdir(db_path) if f.endswith('.json') and f != "backups"]
return jsonify({'tables': tables})

==========================
ENDPOINTS EXTRA
==========================
@app.route('/upload_csv', methods=['POST'])
def upload_csv():
"""Carga datos desde un archivo CSV a una tabla existente."""
table = request.form.get('table')
file = request.files.get('file')
if not table or not file:
return jsonify({'error': 'Falta el nombre de la tabla o el archivo'}), 400
table_data = load_table(table)
if not table_data:
return jsonify({'error': f'Tabla {table} no existe'}), 400
reader = csv.DictReader(StringIO(file.read().decode('utf-8')))
count = 0
for row in reader:
# Solo agrega columnas que existen en la tabla
filtered_row = {col: row[col] for col in table_data["columns"] if col in row}
table_data["rows"].append(filtered_row)
count += 1
save_table(table, table_data)
return jsonify({'message': f'{count} filas agregadas a {table} desde CSV'})

@app.route('/health', methods=['GET'])
def health():
"""Endpoint de salud para verificar si el backend está corriendo."""
return jsonify({'status': 'ok'})

==========================
INICIO DE LA APP
==========================
if name == 'main':
app.run(host='0.0.0.0', port=5000)