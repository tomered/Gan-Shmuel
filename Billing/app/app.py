import os 
from flask import Flask
import mysql.connector
import time

def get_db_connection():
    """Create a connection to the MySQL database"""
    # Try to connect multiple times (useful when starting up)
    for _ in range(10):
        try:
            conn = mysql.connector.connect(
                host="db",
                user="root",
                password="secret",
                database="billdb"
            )
            return conn
        except mysql.connector.Error:
            # Wait and retry
            time.sleep(3)
    
    raise Exception("Could not connect to MySQL database")



app = Flask(__name__)

#GET /health - Health check for app to db 
@app.route('/health',methods=["GET"])
def health():
    # Connect to database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
    
        # Execute "SELECT 1" on the mysqlDB 
        cursor.execute("SELECT 1")
        
        cursor.fetchall()
        cursor.close()
        conn.close()

        return "OK", 200
    # Error handling for connectivity is done in get_db_connection.
    except Exception as e:
        return "Failure", 500


if __name__ == '__main__':
    # TODO: Check if host 0.0.0.0 is the correct way to do this
    app.run(host='0.0.0.0', debug=True, port=5000)





