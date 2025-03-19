from flask import Flask, request, jsonify
from dotenv import load_dotenv
import subprocess
import threading
import requests
import logging
import json
import os

load_dotenv()  # Load .env file if it exists

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# CONFIG
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
PROD_YAML_PATHS = {
    'billing': './Billing/docker-compose.prod.yaml',
    'weight': './Weight/docker-compose.prod.yaml',
    'main': '.'
}


def takedown_prod(param='all'):
    app.logger.info("Taking down old prod")
    if param == 'all':
        subprocess.run(['docker', 'compose', '-f',
                        PROD_YAML_PATHS['billing'], 'down'], check=True)
        subprocess.run(['docker', 'compose', '-f',
                        PROD_YAML_PATHS['weight'], 'down'], check=True)
    else:
        subprocess.run(['docker', 'compose', '-f',
                        PROD_YAML_PATHS[param], 'down'], check=True)


def deploy_prod(param='all'):
    app.logger.info("Tests passed. Deploying to prod...")
    if param == 'all':
        subprocess.run(["docker", "compose", "-f",
                        PROD_YAML_PATHS['billing'], "up", "-d", "--build"], check=True, capture_output=True)
        subprocess.run(["docker", "compose", "-f",
                        PROD_YAML_PATHS['weight'], "up", "-d", "--build"], check=True, capture_output=True)
    else:
        subprocess.run(["docker", "compose", "-f",
                        PROD_YAML_PATHS[param], "up", "-d", "--build"], check=True, capture_output=True)
    app.logger.info("Deployment complete.")


def send_slack_message(text):
    if not SLACK_WEBHOOK_URL:
        app.logger.warning("Slack webhook URL not set.")
        return

    response = requests.post(SLACK_WEBHOOK_URL, json={"text": text})
    if response.status_code != 200:
        app.logger.error(
            f"Slack error: {response.status_code} - {response.text}")
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

        app.logger.info(
            f"CI triggered for branch: {branch} by {pusher_name} ({pusher_email})")


        if branch.lower() not in PROD_YAML_PATHS:
            app.logger.info(f"No CI setup for branch: {branch}")
            return f"No CI setup for branch: {branch}"

        app.logger.info(f"Pulling latest code for '{branch}'...")
        subprocess.run(["git", "checkout", branch], check=True)
        subprocess.run(["git", "pull", "origin", branch], check=True)

        app.logger.info(f"Running tests in container for '{branch}'...")
            
        
        # Change to run tests in future
        result = subprocess.run([
            "docker", "run",
            "-v", f"/Gan-Shmuel/{branch}:/app",
            "-w", "/app",
            "hello-world",
        ], capture_output=True, text=True)

        app.logger.info("Finished running tests")

        if result.returncode == 0:
            if branch.lower() == 'main':
                if (os.path.isfile(PROD_YAML_PATHS["billing"]) and os.path.isfile(PROD_YAML_PATHS["weight"])):
                    takedown_prod()
                    deploy_prod()
            else:
                app.logger.info("Branch is not main. Not deploying app")

            send_slack_message(
                f"✅ *CI passed for `{branch}`*\nPusher: `{pusher_name}`\nCommit: `{commit_hash}`\n")
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
    # add payload action == closed and header github event to pull_request
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
