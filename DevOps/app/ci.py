from flask import Flask, request, jsonify
import subprocess
import threading
import json
import logging
import time
import os
import requests
from dotenv import load_dotenv

load_dotenv()  # Load .env file if it exists

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# CONFIG
BACKEND_PATHS = {
    "billing": "./Billing",
    "weight": "./Weight",
    "main": ""
}

DOCKER_IMAGE = "python:3.12.7"
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


def send_slack_message(text):
    if not SLACK_WEBHOOK_URL:
        app.logger.warning("Slack webhook URL not set.")
        return

    response = requests.post(SLACK_WEBHOOK_URL, json={"text": text})
    if response.status_code != 200:
        app.logger.error(f"Slack error: {response.status_code} - {response.text}")
    else:
        app.logger.info("Slack notification sent.")


def ci_pipeline(payload):
    try:
        data = json.loads(payload)
        full_ref = data.get("ref", "")
        branch = full_ref.split("/")[-1]
        commit_hash = data["after"][:7]
        pusher_name = data["pusher"]["name"]
        pusher_email = data["pusher"]["email"]

        app.logger.info(f"CI triggered for branch: {branch} by {pusher_name} ({pusher_email})")

        if branch.lower() not in BACKEND_PATHS:
            app.logger.info(f"No CI setup for branch: {branch}")
            return jsonify({"status": "No ci setup"}), 400

        code_path = BACKEND_PATHS[branch]

        app.logger.info(f"Pulling latest code for '{branch}'...")
        subprocess.run(["git", "checkout", branch], cwd=code_path, check=True)
        subprocess.run(["git", "pull", "origin", branch], cwd=code_path, check=True)

        app.logger.info(f"Running tests in container for '{branch}'...")

        # Change to run tests in future
        result = subprocess.run([
            "docker", "run", "--rm",
            "-v", f"/Gan-Shmuel/{branch}:/app",
            "-w", "/app",
            "hello-world",
        ], capture_output=True, text=True)

        if result.returncode == 0:
            app.logger.info("Tests passed.")

            if branch == 'main':
                subprocess.run(["docker", "compose", "-f", f"{code_path}/docker-compose.prod.yaml", "-f",
                                f"/ci/docker-compose.override.prod.yaml", "up", "-d", "--build"], check=True, capture_output=True)

                app.logger.info("Deployment complete.")
                time.sleep(5)
                subprocess.run(["docker", "compose", "-f",
                                f"{code_path}/docker-compose.prod.yaml", "-f", f"/ci/docker-compose.override.prod.yaml", "down"])

            send_slack_message(
                f"✅ *CI passed for `{branch}`*\nPusher: `{pusher_name}`\nCommit: `{commit_hash}`\n"
            )

        else:
            app.logger.info("Tests failed.")
            send_slack_message(
                f"❌ *CI failed for `{branch}`*\nPusher: `{pusher_name}`\nCommit: `{commit_hash}`\n\n*Error Output:*\n```{result.stderr.strip()}```"
            )

    except Exception as e:
        app.logger.error(f"CI pipeline error: {e}")
        send_slack_message(f"CI error on branch `{branch}`:\n```{e}```")


@app.route("/trigger", methods=["POST"])
def webhook():
    event = request.headers.get("X-GitHub-Event", "")
    if event == "push":
        payload = request.get_data(as_text=True)
        threading.Thread(target=ci_pipeline, args=(payload,)).start()
        return jsonify({"status": "CI started"}), 202
    return jsonify({"status": "Ignored"}), 200


@app.route("/health")
def health():
    return jsonify({"status": "success"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
