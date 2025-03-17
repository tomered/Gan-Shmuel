from flask import Flask
import mysql.connector

app = Flask(__name__)

mydb = mysql.connector.connect(
  host="host",
  user="user",
  password="password",
  database="database"
)

cursor = mydb.cursor(dictionary=True)

@app.route('/')
def home():
    return "Hello, rom weight server!"

@app.route('/health', methods=['GET'])
def healthcheck():
      if mydb.is_connected():
        cursor.execute("SELECT 1;") 
        cursor.fetchall()  # Ensure all results are read
        return "OK", 200
      else:
          return "Failure", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0")