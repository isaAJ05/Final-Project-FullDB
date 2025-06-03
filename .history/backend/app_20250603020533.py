# ==========================
# IMPORTACIONES Y CONFIGURACIÓN
# ==========================
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

# ==========================
# CONSTANTES Y APP FLASK
# ==========================
app = Flask(__name__)
CORS(app)
DATA_DIR = "data"

# ==========================
# FUNCIONES UTILITARIAS
# ==========================
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


# ==========================
# CACHE DE RESULTADOS DE CONSULTAS
# ==========================
query_cache = {}

# ==========================
# CICLO DE VIDA DE UNA CONSULTA SQL
# ==========================

def parser(query):
    """Etapa 1: Parser - Analiza y valida la sintaxis SQL."""
    parsed = sqlglot.parse(query)
    if not parsed or len(parsed) == 0:
        raise ValueError("Consulta SQL vacía o inválida")
    return parsed[0]

def algebrizer(stmt):
    """Etapa 2: Algebrizer - Extrae tipo de sentencia usando sqlglot."""
    return stmt.key.upper()  # Por ejemplo: 'SELECT', 'INSERT', etc.

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

    # CREATE DATABASE
    if query.lower().startswith("create database"):
        match = re.match(r"create database (\w+)", query, re.IGNORECASE)
        if not match:
            raise ValueError('Sintaxis inválida para CREATE DATABASE')
        db_name = match.group(1)
        if not is_valid_name(db_name):
            raise ValueError('Nombre de base de datos inválido')
        db_path = os.path.join(DATA_DIR, db_name)
        if os.path.exists(db_path):
            raise ValueError(f'La base de datos {db_name} ya existe')
        os.makedirs(db_path, exist_ok=True)
        query_cache.clear()
        return {'message': f'Base de datos {db_name} creada'}

    # DROP TABLE
    if query.lower().startswith("drop table"):
        match = re.match(r"drop table (\w+\.\w+)", query, re.IGNORECASE)
        if not match:
            raise ValueError('Sintaxis inválida para DROP TABLE. Usa DROP TABLE db.tabla')
        full_table = match.group(1)
        db, table = parse_db_table(full_table)
        if not db or not is_valid_name(db) or not is_valid_name(table):
            raise ValueError('Nombre de base de datos o tabla inválido')
        table_path = os.path.join(DATA_DIR, db, f"{table}.json")
        if not os.path.exists(table_path):
            raise ValueError(f'La tabla {table} no existe en base {db}')
        os.remove(table_path)
        query_cache.clear()
        return {'message': f'Tabla {table} eliminada de la base {db}'}

    # RENAME TABLE
    if query.lower().startswith("rename table"):
        match = re.match(r"rename table (\w+\.\w+) to (\w+\.\w+)", query, re.IGNORECASE)
        if not match:
            raise ValueError('Sintaxis inválida para RENAME TABLE. Usa RENAME TABLE db.tabla TO db.nuevonombre')
        full_table, full_new = match.groups()
        db, table = parse_db_table(full_table)
        db_new, table_new = parse_db_table(full_new)
        if not db or not db_new or db != db_new or not is_valid_name(table_new):
            raise ValueError('Ambas tablas deben estar en la misma base de datos y tener nombres válidos')
        old_path = os.path.join(DATA_DIR, db, f"{table}.json")
        new_path = os.path.join(DATA_DIR, db, f"{table_new}.json")
        if not os.path.exists(old_path):
            raise ValueError(f'La tabla {table} no existe en base {db}')
        if os.path.exists(new_path):
            raise ValueError(f'La tabla {table_new} ya existe en base {db}')
        os.rename(old_path, new_path)
        query_cache.clear()
        return {'message': f'Tabla {table} renombrada a {table_new} en base {db}'}

    # CREATE TABLE
    if query.lower().startswith("create table"):
        match = re.match(r"create table (\w+\.\w+|\w+) \((.+)\)", query, re.IGNORECASE)
        if not match:
            raise ValueError('Sintaxis inválida para CREATE TABLE')
        full_table, columns = match.groups()
        db, table = parse_db_table(full_table)
        if not db or not is_valid_name(db) or not is_valid_name(table):
            raise ValueError('Nombre de base de datos o tabla inválido')
        columns = [col.strip().split()[0] for col in columns.split(',')]
        if len(set(columns)) != len(columns):
            raise ValueError('No puede haber columnas repetidas')
        table_path = os.path.join(DATA_DIR, db, f"{table}.json")
        if os.path.exists(table_path):
            raise ValueError(f'La tabla {table} ya existe en base {db}')
        save_table(db, table, {"columns": columns, "rows": []})
        query_cache.clear()
        return {'message': f'Tabla {table} creada en base {db} con columnas {columns}'}

    # INSERT
    if query.lower().startswith("insert into"):
        match = re.match(r"insert into (\w+\.\w+|\w+) \((.+)\) values \((.+)\)", query, re.IGNORECASE)
        if not match:
            raise ValueError('Sintaxis inválida para INSERT')
        full_table, columns, values = match.groups()
        db, table = parse_db_table(full_table)
        if not db or not is_valid_name(db) or not is_valid_name(table):
            raise ValueError('Nombre de base de datos o tabla inválido')
        columns = [c.strip() for c in columns.split(',')]
        values = [v.strip().strip("'") for v in values.split(',')]
        table_data = load_table(db, table)
        if not table_data:
            raise ValueError(f'Tabla {table} no existe en base {db}')
        for col in columns:
            if col not in table_data["columns"]:
                raise ValueError(f'Columna {col} no existe en la tabla {table}')
        if len(columns) != len(table_data["columns"]):
            raise ValueError('Debes insertar todas las columnas de la tabla')
        row = dict(zip(columns, values))
        table_data["rows"].append(row)
        save_table(db, table, table_data)
        query_cache.clear()
        return {'message': f'Dato insertado en {table} de {db}', 'row': row}

    # UPDATE
    if query.lower().startswith("update"):
        match = re.match(r"update (\w+\.\w+|\w+) set (.+) where (.+)", query, re.IGNORECASE)
        if not match:
            raise ValueError('Sintaxis inválida para UPDATE')
        full_table, set_part, where_part = match.groups()
        db, table = parse_db_table(full_table)
        if not db or not is_valid_name(db) or not is_valid_name(table):
            raise ValueError('Nombre de base de datos o tabla inválido')
        table_data = load_table(db, table)
        if not table_data:
            raise ValueError(f'Tabla {table} no existe en base {db}')
        backup_table(db, table, table_data)
        set_col, set_val = [x.strip() for x in set_part.split('=')]
        where_col, where_val = [x.strip() for x in where_part.split('=')]
        set_val = set_val.strip("'")
        where_val = where_val.strip("'")
        if set_col not in table_data["columns"]:
            raise ValueError(f'Columna {set_col} no existe en la tabla {table}')
        if where_col not in table_data["columns"]:
            raise ValueError(f'Columna {where_col} no existe en la tabla {table}')
        updated = 0
        for row in table_data["rows"]:
            if str(row.get(where_col)) == where_val:
                row[set_col] = set_val
                updated += 1
        save_table(db, table, table_data)
        query_cache.clear()
        return {'message': f'{updated} filas actualizadas en {table} de {db}'}

    # DELETE
    if query.lower().startswith("delete from"):
        match = re.match(r"delete from (\w+\.\w+|\w+) where (.+)", query, re.IGNORECASE)
        if not match:
            raise ValueError('Sintaxis inválida para DELETE')
        full_table, where_part = match.groups()
        db, table = parse_db_table(full_table)
        if not db or not is_valid_name(db) or not is_valid_name(table):
            raise ValueError('Nombre de base de datos o tabla inválido')
        table_data = load_table(db, table)
        if not table_data:
            raise ValueError(f'Tabla {table} no existe en base {db}')
        backup_table(db, table, table_data)
        where_col, where_val = [x.strip() for x in where_part.split('=')]
        where_val = where_val.strip("'")
        if where_col not in table_data["columns"]:
            raise ValueError(f'Columna {where_col} no existe en la tabla {table}')
        before = len(table_data["rows"])
        table_data["rows"] = [row for row in table_data["rows"] if str(row.get(where_col)) != where_val]
        deleted = before - len(table_data["rows"])
        save_table(db, table, table_data)
        query_cache.clear()
        return {'message': f'{deleted} filas eliminadas de {table} en {db}'}

    # SELECT (sin caché)
    if query.lower().startswith("select"):
        match = re.match(r"select (.+) from (\w+\.\w+|\w+)", query, re.IGNORECASE)
        if not match:
            raise ValueError('Sintaxis inválida para SELECT')
        columns, full_table = match.groups()
        db, table = parse_db_table(full_table)
        if not db or not is_valid_name(db) or not is_valid_name(table):
            raise ValueError('Nombre de base de datos o tabla inválido')
        table_data = load_table(db, table)
        if not table_data:
            raise ValueError(f'Tabla {table} no existe en base {db}')
        if columns.strip() == "*":
            result = table_data["rows"]
        else:
            cols = [c.strip() for c in columns.split(',')]
            for col in cols:
                if col not in table_data["columns"]:
                    raise ValueError(f'Columna {col} no existe en la tabla {table}')
            result = [{col: row.get(col) for col in cols} for row in table_data["rows"]]
        # Guarda en caché el resultado
        query_cache[query] = {"columns": table_data["columns"], "rows": result}
        return {"source": "executed", "columns": table_data["columns"], "rows": result}

    raise ValueError('Solo se soportan CREATE TABLE, INSERT, SELECT, UPDATE y DELETE básicos con db.tabla')

# ==========================
# ENDPOINT PRINCIPAL: EJECUCIÓN DE SQL (modularizado)
# ==========================

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
        if stmt_type not in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP']:
            return jsonify({'error': f'Tipo de consulta no soportado: {stmt_type}'}), 400
        # 3. Optimizer/Planner (incluye caché)
        plan = optimizer(stmt_type, query)
        # 4. Executor
        result = executor(plan, stmt_type, query, data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
# ==========================
# ENDPOINTS DE ADMINISTRACIÓN
# ==========================

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

# ==========================
# ENDPOINTS EXTRA
# ==========================

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

# ==========================
# INICIO DE LA APP
# ==========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)