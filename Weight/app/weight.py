import json
from flask import Flask, request, jsonify
from datetime import datetime
import mysql.connector

app = Flask(__name__)

mydb = mysql.connector.connect(
  host="db_gs",
  user="root",
  password="root",
  database="weight"
)

cursor = mydb.cursor(dictionary=True)

@app.route('/')
def home():
    return "Hello, From weight server!"

@app.route('/health', methods=['GET'])
def healthcheck():
      if mydb.is_connected():
        cursor.execute("SELECT 1;") 
        cursor.fetchall()  # Ensure all results are read
        return "OK", 200
      else:
          return "Failure", 500

@app.route('/weight', methods=['GET'])
def get_weight():

    from_time = request.args.get('from',datetime.now().strftime("%Y%m%d") + "000000")
    to_time = request.args.get('to', datetime.now().strftime("%Y%m%d%H%M%S"))
    filter_by = request.args.get('filter', "in,out,none").split(',')
    
    try:        
        # Construct SQL query
        query = """
        SELECT id, direction, bruto, neto, produce, containers 
        FROM transactions
        WHERE datetime BETWEEN %s AND %s
        AND direction IN ({})
        """.format(",".join(["%s"] * len(filter_by)))  # Creates placeholders dynamically
        
        params = [from_time, to_time] + filter_by
        
        cursor.execute(query, params)
        result = cursor.fetchall()

        
        return jsonify(result)
    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0")