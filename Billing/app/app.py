import os 
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

db = SQLAlchemy(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


class Provider(db.Model):
    # TODO: Check if im able to set my own id
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255))


if __name__ == '__main__':
    db.create_all()
    # TODO: Check if host 0.0.0.0 is the correct way to do this
    app.run(host='0.0.0.0', debug=True, port=4000)
