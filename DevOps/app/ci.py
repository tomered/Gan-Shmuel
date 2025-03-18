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

        if branch.lower() not in PROD_YAML_PATHS:
            app.logger.info(f"No CI setup for branch: {branch}")
            return jsonify({"status": "No ci setup"}), 400

        app.logger.info(f"Pulling latest code for '{branch}'...")
        subprocess.run(["git", "checkout", branch], check=True)
        subprocess.run(["git", "pull"], check=True)

        app.logger.info(f"Running tests in container for '{branch}'...")

        # Create and run a container with tests

        # Change to run tests in future
        result = subprocess.run([
            "docker", "run",
            "-v", f"/Gan-Shmuel/{branch}:/app",
            "-w", "/app",
            "hello-world",
        ], capture_output=True, text=True)

        if result.returncode == 0:
            if branch.lower() == 'main':
                if (os.path.isfile(PROD_YAML_PATHS["billing"]) and os.path.isfile(PROD_YAML_PATHS["weight"])):
                    takedown_prod()
                    deploy_prod()

            # implement maling

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
