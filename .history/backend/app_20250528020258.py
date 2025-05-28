from flask import Flask, request, jsonify
import sqlparse
import json
import os
import re

app = Flask(__name__)
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
    # Ejemplo muy simple: solo soporta CREATE TABLE, INSERT y SELECT
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

        else:
            return jsonify({'error': 'Solo se soportan CREATE TABLE, INSERT y SELECT básicos'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)