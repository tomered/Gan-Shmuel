from flask import Flask
import mysql.connector

app = Flask(__name__)

mydb = mysql.connector.connect(
  host="host",
  user="user",
  password="password",
  database="database"
)

@app.route('/')
def home():
    return "Hello, World!"

if __name__ == "__main__":
    app.run(host="0.0.0.0")