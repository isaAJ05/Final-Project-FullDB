from flask import Flask, request, jsonify
import sqlparse
import json
import os
import re
import csv
from io import StringIO
import datetime
import shutil

from flask_cors import CORS

app = Flask(__name__)
CORS(app)
DATA_DIR = "data"

def save_table(db, table, data):
    os.makedirs(os.path.join(DATA_DIR, db), exist_ok=True)
    with open(os.path.join(DATA_DIR, db, f"{table}.json"), "w") as f:
        json.dump(data, f)

def is_valid_name(name):
    """Valida que el nombre solo tenga letras, números y guion bajo, y no empiece con número."""
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

@app.route('/backups', methods=['GET'])
def list_backups():
    db = request.args.get('db')
    table = request.args.get('table')
    backup_dir = os.path.join(DATA_DIR, db, "backups")
    if not os.path.exists(backup_dir):
        return jsonify({'backups': []})
    files = [f for f in os.listdir(backup_dir) if f.startswith(table)]
    return jsonify({'backups': files})

@app.route('/restore_backup', methods=['POST'])
def restore_backup():
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
    dbs = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
    return jsonify({'databases': dbs})

@app.route('/parse', methods=['POST'])
def parse_db_table(full_name):
    """Devuelve (db, table) a partir de 'db.tabla' o (None, tabla) si no hay db."""
    parts = full_name.split('.')
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, parts[0]

@app.route('/execute', methods=['POST'])
def execute_sql():
    data = request.json
    query = data.get('query', '').strip()
    try:
        # Validar sintaxis SQL con sqlparse
        parsed = sqlparse.parse(query)
        if not parsed or len(parsed) == 0:
            return jsonify({'error': 'Consulta SQL vacía o inválida'}), 400
        stmt = parsed[0]
        # Opcional: puedes validar el tipo de sentencia soportada
        if stmt.get_type() not in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP']:
            return jsonify({'error': f'Tipo de consulta no soportado: {stmt.get_type()}'}), 400
        
        # CREATE DATABASE
        if query.lower().startswith("create database"):
            match = re.match(r"create database (\w+)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para CREATE DATABASE'}), 400
            db_name = match.group(1)
            if not is_valid_name(db_name):
                return jsonify({'error': 'Nombre de base de datos inválido'}), 400
            db_path = os.path.join(DATA_DIR, db_name)
            if os.path.exists(db_path):
                return jsonify({'error': f'La base de datos {db_name} ya existe'}), 400
            os.makedirs(db_path, exist_ok=True)
            return jsonify({'message': f'Base de datos {db_name} creada'})

        # DROP TABLE db.tabla
        if query.lower().startswith("drop table"):
            match = re.match(r"drop table (\w+\.\w+)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para DROP TABLE. Usa DROP TABLE db.tabla'}), 400
            full_table = match.group(1)
            db, table = parse_db_table(full_table)
            if not db or not is_valid_name(db) or not is_valid_name(table):
                return jsonify({'error': 'Nombre de base de datos o tabla inválido'}), 400
            table_path = os.path.join(DATA_DIR, db, f"{table}.json")
            if not os.path.exists(table_path):
                return jsonify({'error': f'La tabla {table} no existe en base {db}'}), 400
            os.remove(table_path)
            return jsonify({'message': f'Tabla {table} eliminada de la base {db}'})

        # RENAME TABLE db.tabla TO db.nuevonombre
        if query.lower().startswith("rename table"):
            match = re.match(r"rename table (\w+\.\w+) to (\w+\.\w+)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para RENAME TABLE. Usa RENAME TABLE db.tabla TO db.nuevonombre'}), 400
            full_table, full_new = match.groups()
            db, table = parse_db_table(full_table)
            db_new, table_new = parse_db_table(full_new)
            if not db or not db_new or db != db_new or not is_valid_name(table_new):
                return jsonify({'error': 'Ambas tablas deben estar en la misma base de datos y tener nombres válidos'}), 400
            old_path = os.path.join(DATA_DIR, db, f"{table}.json")
            new_path = os.path.join(DATA_DIR, db, f"{table_new}.json")
            if not os.path.exists(old_path):
                return jsonify({'error': f'La tabla {table} no existe en base {db}'}), 400
            if os.path.exists(new_path):
                return jsonify({'error': f'La tabla {table_new} ya existe en base {db}'}), 400
            os.rename(old_path, new_path)
            return jsonify({'message': f'Tabla {table} renombrada a {table_new} en base {db}'})

        # CREATE TABLE db.tabla (col1, col2, ...)
        if query.lower().startswith("create table"):
            match = re.match(r"create table (\w+\.\w+|\w+) \((.+)\)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para CREATE TABLE'}), 400
            full_table, columns = match.groups()
            db, table = parse_db_table(full_table)
            if not db or not is_valid_name(db) or not is_valid_name(table):
                return jsonify({'error': 'Nombre de base de datos o tabla inválido'}), 400
            columns = [col.strip().split()[0] for col in columns.split(',')]
            if len(set(columns)) != len(columns):
                return jsonify({'error': 'No puede haber columnas repetidas'}), 400
            table_path = os.path.join(DATA_DIR, db, f"{table}.json")
            if os.path.exists(table_path):
                return jsonify({'error': f'La tabla {table} ya existe en base {db}'}), 400
            save_table(db, table, {"columns": columns, "rows": []})
            return jsonify({'message': f'Tabla {table} creada en base {db} con columnas {columns}'})

        # INSERT INTO db.tabla (col1, col2) VALUES (...)
        elif query.lower().startswith("insert into"):
            match = re.match(r"insert into (\w+\.\w+|\w+) \((.+)\) values \((.+)\)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para INSERT'}), 400
            full_table, columns, values = match.groups()
            db, table = parse_db_table(full_table)
            if not db or not is_valid_name(db) or not is_valid_name(table):
                return jsonify({'error': 'Nombre de base de datos o tabla inválido'}), 400
            columns = [c.strip() for c in columns.split(',')]
            values = [v.strip().strip("'") for v in values.split(',')]
            table_data = load_table(db, table)
            if not table_data:
                return jsonify({'error': f'Tabla {table} no existe en base {db}'}), 400
            # Validar columnas
            for col in columns:
                if col not in table_data["columns"]:
                    return jsonify({'error': f'Columna {col} no existe en la tabla {table}'}), 400
            if len(columns) != len(table_data["columns"]):
                return jsonify({'error': 'Debes insertar todas las columnas de la tabla'}), 400
            row = dict(zip(columns, values))
            table_data["rows"].append(row)
            save_table(db, table, table_data)
            return jsonify({'message': f'Dato insertado en {table} de {db}', 'row': row})

        # UPDATE db.tabla SET ... WHERE ...
        elif query.lower().startswith("update"):
            match = re.match(r"update (\w+\.\w+|\w+) set (.+) where (.+)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para UPDATE'}), 400
            full_table, set_part, where_part = match.groups()
            db, table = parse_db_table(full_table)
            if not db or not is_valid_name(db) or not is_valid_name(table):
                return jsonify({'error': 'Nombre de base de datos o tabla inválido'}), 400
            table_data = load_table(db, table)
            if not table_data:
                return jsonify({'error': f'Tabla {table} no existe en base {db}'}), 400 
            backup_table(db, table, table_data)
            set_col, set_val = [x.strip() for x in set_part.split('=')]
            where_col, where_val = [x.strip() for x in where_part.split('=')]
            set_val = set_val.strip("'")
            where_val = where_val.strip("'")
            # Validar columnas
            if set_col not in table_data["columns"]:
                return jsonify({'error': f'Columna {set_col} no existe en la tabla {table}'}), 400
            if where_col not in table_data["columns"]:
                return jsonify({'error': f'Columna {where_col} no existe en la tabla {table}'}), 400
            updated = 0
            for row in table_data["rows"]:
                if str(row.get(where_col)) == where_val:
                    row[set_col] = set_val
                    updated += 1
            save_table(db, table, table_data)
            return jsonify({'message': f'{updated} filas actualizadas en {table} de {db}'})

        # DELETE FROM db.tabla WHERE ...
        elif query.lower().startswith("delete from"):
            match = re.match(r"delete from (\w+\.\w+|\w+) where (.+)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para DELETE'}), 400
            full_table, where_part = match.groups()
            db, table = parse_db_table(full_table)
            if not db or not is_valid_name(db) or not is_valid_name(table):
                return jsonify({'error': 'Nombre de base de datos o tabla inválido'}), 400
            table_data = load_table(db, table)
            if not table_data:
                return jsonify({'error': f'Tabla {table} no existe en base {db}'}), 400
            backup_table(db, table, table_data)
            where_col, where_val = [x.strip() for x in where_part.split('=')]
            where_val = where_val.strip("'")
            # Validar columna
            if where_col not in table_data["columns"]:
                return jsonify({'error': f'Columna {where_col} no existe en la tabla {table}'}), 400
            before = len(table_data["rows"])
            table_data["rows"] = [row for row in table_data["rows"] if str(row.get(where_col)) != where_val]
            deleted = before - len(table_data["rows"])
            save_table(db, table, table_data)
            return jsonify({'message': f'{deleted} filas eliminadas de {table} en {db}'})

        # SELECT ... FROM db.tabla
        elif query.lower().startswith("select"):
            match = re.match(r"select (.+) from (\w+\.\w+|\w+)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para SELECT'}), 400
            columns, full_table = match.groups()
            db, table = parse_db_table(full_table)
            if not db or not is_valid_name(db) or not is_valid_name(table):
                return jsonify({'error': 'Nombre de base de datos o tabla inválido'}), 400
            table_data = load_table(db, table)
            if not table_data:
                return jsonify({'error': f'Tabla {table} no existe en base {db}'}), 400
            if columns.strip() == "*":
                result = table_data["rows"]
            else:
                cols = [c.strip() for c in columns.split(',')]
                # Validar columnas
                for col in cols:
                    if col not in table_data["columns"]:
                        return jsonify({'error': f'Columna {col} no existe en la tabla {table}'}), 400
                result = [{col: row.get(col) for col in cols} for row in table_data["rows"]]
            return jsonify({'columns': table_data["columns"], 'rows': result})

        else:
            return jsonify({'error': 'Solo se soportan CREATE TABLE, INSERT, SELECT, UPDATE y DELETE básicos con db.tabla'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
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
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)