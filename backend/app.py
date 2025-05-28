from flask import Flask, request, jsonify
import sqlparse
import json
import os
import re
import csv
from io import StringIO

from flask_cors import CORS

app = Flask(__name__)
CORS(app)
DATA_DIR = "data"

def save_table(table, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, f"{table}.json"), "w") as f:
        json.dump(data, f)

def load_table(table):
    try:
        with open(os.path.join(DATA_DIR, f"{table}.json"), "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

@app.route('/parse', methods=['POST'])
def parse_sql():
    data = request.json
    query = data.get('query', '')
    try:
        parsed = sqlparse.format(query, reindent=True, keyword_case='upper')
        return jsonify({'parsed_query': parsed})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/execute', methods=['POST'])
def execute_sql():
    data = request.json
    query = data.get('query', '').strip()
    try:
        if query.lower().startswith("create table"):
            match = re.match(r"create table (\w+) \((.+)\)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para CREATE TABLE'}), 400
            table, columns = match.groups()
            columns = [col.strip().split()[0] for col in columns.split(',')]
            save_table(table, {"columns": columns, "rows": []})
            return jsonify({'message': f'Tabla {table} creada con columnas {columns}'})

        elif query.lower().startswith("insert into"):
            match = re.match(r"insert into (\w+) \((.+)\) values \((.+)\)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para INSERT'}), 400
            table, columns, values = match.groups()
            columns = [c.strip() for c in columns.split(',')]
            values = [v.strip().strip("'") for v in values.split(',')]
            table_data = load_table(table)
            if not table_data:
                return jsonify({'error': f'Tabla {table} no existe'}), 400
            row = dict(zip(columns, values))
            table_data["rows"].append(row)
            save_table(table, table_data)
            return jsonify({'message': f'Dato insertado en {table}', 'row': row})

        elif query.lower().startswith("select"):
            match = re.match(r"select (.+) from (\w+)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para SELECT'}), 400
            columns, table = match.groups()
            table_data = load_table(table)
            if not table_data:
                return jsonify({'error': f'Tabla {table} no existe'}), 400
            if columns.strip() == "*":
                result = table_data["rows"]
            else:
                cols = [c.strip() for c in columns.split(',')]
                result = [{col: row.get(col) for col in cols} for row in table_data["rows"]]
            return jsonify({'columns': table_data["columns"], 'rows': result})

        elif query.lower().startswith("update"):
            match = re.match(r"update (\w+) set (.+) where (.+)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para UPDATE'}), 400
            table, set_part, where_part = match.groups()
            table_data = load_table(table)
            if not table_data:
                return jsonify({'error': f'Tabla {table} no existe'}), 400
            set_col, set_val = [x.strip() for x in set_part.split('=')]
            where_col, where_val = [x.strip() for x in where_part.split('=')]
            set_val = set_val.strip("'")
            where_val = where_val.strip("'")
            updated = 0
            for row in table_data["rows"]:
                if str(row.get(where_col)) == where_val:
                    row[set_col] = set_val
                    updated += 1
            save_table(table, table_data)
            return jsonify({'message': f'{updated} filas actualizadas en {table}'})

        elif query.lower().startswith("delete from"):
            match = re.match(r"delete from (\w+) where (.+)", query, re.IGNORECASE)
            if not match:
                return jsonify({'error': 'Sintaxis inválida para DELETE'}), 400
            table, where_part = match.groups()
            table_data = load_table(table)
            if not table_data:
                return jsonify({'error': f'Tabla {table} no existe'}), 400
            where_col, where_val = [x.strip() for x in where_part.split('=')]
            where_val = where_val.strip("'")
            before = len(table_data["rows"])
            table_data["rows"] = [row for row in table_data["rows"] if str(row.get(where_col)) != where_val]
            deleted = before - len(table_data["rows"])
            save_table(table, table_data)
            return jsonify({'message': f'{deleted} filas eliminadas de {table}'})

        else:
            return jsonify({'error': 'Solo se soportan CREATE TABLE, INSERT, SELECT, UPDATE y DELETE básicos'}), 400

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