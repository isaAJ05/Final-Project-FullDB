from flask import Flask, request, jsonify
import sqlparse

app = Flask(__name__)

@app.route('/parse', methods=['POST'])
def parse_sql():
    data = request.json
    query = data.get('query', '')

    try:
        parsed = sqlparse.format(query, reindent=True, keyword_case='upper')
        return jsonify({'parsed_query': parsed})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
