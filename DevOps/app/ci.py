from flask import Flask, request, jsonify
import subprocess
import threading
import json
import os

app = Flask(__name__)

# CONFIG
BACKEND_PATHS = {
    "billing": "/Billing",  # path to billing code
    "weight": "/Weight",     # path to weight code
    "main": ""
}

DOCKER_IMAGE = "python:3.12.7"  # base image used to test inside containers

def ci_pipeline(payload):
    # Get info about user, branch and commit
    try:
        data = json.loads(payload)
        full_ref = data.get("ref", "")
        branch = full_ref.split("/")[-1]
        commit_hash = data["after"][:7]
        pusher_name = data["pusher"]["name"]
        pusher_email = data["pusher"]["email"]
        with open('test2.txt', 'a') as f:
            f.write(f"data:{data}\nfull_ref: {full_ref}\nbranch: {branch}\ncommit_hash: {commit_hash}\npush_name: {pusher_name}\npusher_email: {pusher_email}")
        print(f"\nCI Triggered")

        if branch not in BACKEND_PATHS:
            print(f"No CI setup for branch: {branch}")
            return

        code_path = BACKEND_PATHS[branch]

        print(f"Pulling latest code for '{branch}'...")
        subprocess.run(["git", "checkout", branch], cwd=code_path, check=True)
        subprocess.run(["git", "pull", "origin", branch], cwd=code_path, check=True)

        print(f"Running tests in container for '{branch}'...")

        # Create and run a container with tests

        result = subprocess.run([
            "docker", "run", "--rm",
            "-v", f"{code_path}:/app",
            "-w", "/app",
            DOCKER_IMAGE,
            "bash", "-c", "pip install -r requirements.txt && pytest"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("Tests passed. Building and deploying app...")

            subprocess.run(["docker-compose", "-f", f"{code_path}/docker-compose.yml", "build"], check=True)
            subprocess.run(["docker-compose", "-f", f"{code_path}/docker-compose.yml", "up", "-d"], check=True)

            print("Deployment complete.")
        else:
            print("Tests failed.")
            print("Test Output:")
            print(result.stdout)
            print(result.stderr)
            print(f"Notify {pusher_name} <{pusher_email}>: Tests failed.")

    except Exception as e:
        print(f"CI pipeline error: {e}")

@app.route("/trigger", methods=["POST"])
def webhook():
    # Webhook endpoint to handle GitHub push events
    event = request.headers.get("X-GitHub-Event", "")
    if event == "push":
        payload = request.get_data(as_text=True)
        threading.Thread(target=ci_pipeline, args=(payload,)).start()
        with open('test.txt', 'a') as f:
            f.write('test')
        return jsonify({"status": "CI started"}), 202
    return jsonify({"status": "Ignored"}), 200

@app.route("/health")
def health():
    return jsonify({"status": "success"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
