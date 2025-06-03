from flask import Flask, request, jsonify
import sqlparse
import json
import os
import re
import csv
from io import StringIO
import datetime

from flask_cors import CORS

app = Flask(__name__)
CORS(app)
DATA_DIR = "data"

def save_table(db, table, data):
    os.makedirs(os.path.join(DATA_DIR, db), exist_ok=True)
    with open(os.path.join(DATA_DIR, db, f"{table}.json"), "w") as f:
        json.dump(data, f)

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
        # CREATE DATABASE
        if query.lower().startswith("create database"):
            match = re.match(r"create database (\w+)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para CREATE DATABASE'}), 400
            db_name = match.group(1)
            os.makedirs(os.path.join(DATA_DIR, db_name), exist_ok=True)
            return jsonify({'message': f'Base de datos {db_name} creada'})

        # CREATE TABLE db.tabla (col1, col2, ...)
        if query.lower().startswith("create table"):
            match = re.match(r"create table (\w+\.\w+|\w+) \((.+)\)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para CREATE TABLE'}), 400
            full_table, columns = match.groups()
            db, table = parse_db_table(full_table)
            if not db:
                return jsonify({'error': 'Debes especificar la base de datos: CREATE TABLE db.tabla (...)'}), 400
            columns = [col.strip().split()[0] for col in columns.split(',')]
            save_table(db, table, {"columns": columns, "rows": []})
            return jsonify({'message': f'Tabla {table} creada en base {db} con columnas {columns}'})

        # INSERT INTO db.tabla (col1, col2) VALUES (...)
        elif query.lower().startswith("insert into"):
            match = re.match(r"insert into (\w+\.\w+|\w+) \((.+)\) values \((.+)\)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para INSERT'}), 400
            full_table, columns, values = match.groups()
            db, table = parse_db_table(full_table)
            if not db:
                return jsonify({'error': 'Debes especificar la base de datos: INSERT INTO db.tabla (...)'}), 400
            columns = [c.strip() for c in columns.split(',')]
            values = [v.strip().strip("'") for v in values.split(',')]
            table_data = load_table(db, table)
            if not table_data:
                return jsonify({'error': f'Tabla {table} no existe en base {db}'}), 400
            row = dict(zip(columns, values))
            table_data["rows"].append(row)
            save_table(db, table, table_data)
            return jsonify({'message': f'Dato insertado en {table} de {db}', 'row': row})

        # SELECT ... FROM db.tabla
        elif query.lower().startswith("select"):
            match = re.match(r"select (.+) from (\w+\.\w+|\w+)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para SELECT'}), 400
            columns, full_table = match.groups()
            db, table = parse_db_table(full_table)
            if not db:
                return jsonify({'error': 'Debes especificar la base de datos: SELECT ... FROM db.tabla'}), 400
            table_data = load_table(db, table)
            if not table_data:
                return jsonify({'error': f'Tabla {table} no existe en base {db}'}), 400
            if columns.strip() == "*":
                result = table_data["rows"]
            else:
                cols = [c.strip() for c in columns.split(',')]
                result = [{col: row.get(col) for col in cols} for row in table_data["rows"]]
            return jsonify({'columns': table_data["columns"], 'rows': result})

        # UPDATE db.tabla SET ... WHERE ...
        elif query.lower().startswith("update"):
            match = re.match(r"update (\w+\.\w+|\w+) set (.+) where (.+)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para UPDATE'}), 400
            full_table, set_part, where_part = match.groups()
            db, table = parse_db_table(full_table)
            if not db:
                return jsonify({'error': 'Debes especificar la base de datos: UPDATE db.tabla ...'}), 400
            table_data = load_table(db, table)
            if not table_data:
                return jsonify({'error': f'Tabla {table} no existe en base {db}'}), 400 
            backup_table(db, table, table_data) # <--- RESPALDO ANTES DE MODIFICAR
            set_col, set_val = [x.strip() for x in set_part.split('=')]
            where_col, where_val = [x.strip() for x in where_part.split('=')]
            set_val = set_val.strip("'")
            where_val = where_val.strip("'")
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
            if not db:
                return jsonify({'error': 'Debes especificar la base de datos: DELETE FROM db.tabla ...'}), 400
            table_data = load_table(db, table)
            if not table_data:
                    return jsonify({'error': f'Tabla {table} no existe en base {db}'}), 400
                backup_table(db, table, table_data)  # <--- RESPALDO ANTES DE MODIFICAR
            where_col, where_val = [x.strip() for x in where_part.split('=')]
            where_val = where_val.strip("'")
            before = len(table_data["rows"])
            table_data["rows"] = [row for row in table_data["rows"] if str(row.get(where_col)) != where_val]
            deleted = before - len(table_data["rows"])
            save_table(db, table, table_data)
            return jsonify({'message': f'{deleted} filas eliminadas de {table} en {db}'})

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)