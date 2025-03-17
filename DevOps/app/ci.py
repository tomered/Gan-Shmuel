from flask import Flask, request, jsonify
import subprocess
import threading
import json
import logging
import time
import os

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)


# CONFIG
BACKEND_PATHS = {
    "billing": "./Billing",  # path to billing code
    "weight": "./Weight",     # path to weight code
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
        app.logger.info(
            f"data:{data}\nfull_ref: {full_ref}\nbranch: {branch}\ncommit_hash: {commit_hash}\npush_name: {pusher_name}\npusher_email: {pusher_email}")
        app.logger.info(f"\nCI Triggered")

        if branch.lower() not in BACKEND_PATHS:
            app.logger.info(f"No CI setup for branch: {branch}")
            return jsonify({"status": "No ci setup"}), 400

        code_path = BACKEND_PATHS[branch]

        app.logger.info(f"Pulling latest code for '{branch}'...")
        subprocess.run(["git", "checkout", branch], cwd=code_path, check=True)
        subprocess.run(["git", "pull", "origin", branch],
                       cwd=code_path, check=True)

        app.logger.info(f"Running tests in container for '{branch}'...")

        # Create and run a container with tests

        result = subprocess.run([
            "docker", "run", "--rm",
            "-v", f"/Gan-Shmuel/{branch}:/app",
            "-w", "/app",
            "hello-world",
        ], capture_output=True, text=True)

        if result.returncode == 0:
            app.logger.info("Tests passed. Building and deploying app...")

            # subprocess.run(["docker", "compose", "-f", f"{code_path}/docker-compose.prod.yaml",
            #                "-f", f"{code_path}/docker-compose.override.prod.yaml" "build"], check=True)
            subprocess.run(["docker", "compose", "-f", f"{code_path}/docker-compose.prod.yaml", "-f",
                           f"/ci//docker-compose.override.prod.yaml", "up", "-d", "--build"], check=True, capture_output=True)

            app.logger.info("Deployment complete.")
            time.sleep(5)
            subprocess.run(["docker", "compose", "-f",
                           f"{code_path}/docker-compose.prod.yaml", "-f", f"/ci//docker-compose.override.prod.yaml", "down"])
        else:
            app.logger.info("Tests failed.")
            app.logger.info("Test Output:")
            app.logger.info(result.stdout)
            app.logger.info(result.stderr)
            app.logger.info(
                f"Notify {pusher_name} <{pusher_email}>: Tests failed.")

    except Exception as e:
        app.logger.info(f"CI pipeline error: {e}")


@app.route("/trigger", methods=["POST"])
def webhook():
    # Webhook endpoint to handle GitHub push events
    event = request.headers.get("X-GitHub-Event", "")
    if event == "push":
        payload = request.get_data(as_text=True)
        threading.Thread(target=ci_pipeline, args=(payload,)).start()
        app.logger.info("testing trigger")
        return jsonify({"status": "CI started"}), 202
    return jsonify({"status": "Ignored"}), 200


@app.route("/health")
def health():
    return jsonify({"status": "success"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
