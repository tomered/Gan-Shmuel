from flask import Flask, redirect, url_for, render_template, Response, request, jsonify
import os


app = Flask(__name__)

@app.route('/health', methods=['GET'])
def healthcheck():
    return ('OK', 200)


if __name__ == "__main__":
    app.run(host="0.0.0.0")