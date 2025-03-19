from flask import Flask, request, jsonify
from logger_config import setup_logger
from dotenv import load_dotenv
import subprocess
import threading
import requests
import json
import os

load_dotenv()  # Load .env file if it exists

app = Flask(__name__)
setup_logger(app)

# CONFIG
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
YAML_PATHS = {
    'billing': {
        'prod': './Billing/docker-compose.prod.yaml',
        'test': './Billing/docker-compose.test.yaml'
    },
    'weight': {
        'prod': './Weight/docker-compose.prod.yaml',
        'test': './Weight/docker-compose.test.yaml'
    },
    'main': {
        'prod': '.',
        'test': '.'
    }
}


def manage_env(action, env, branch='main'):
    valid_actions = {"up", "down"}
    if action not in valid_actions:
        app.logger.error(f"Invalid action '{action}'. Use 'up' or 'down'.")
        return ValueError(f"Invalid action '{action}'. Use 'up' or 'down'.")

    app.logger.info(f"Performing action: `{action}` on `{branch}` in `{env}` environment...")

    try:
        if branch == 'main' or branch == 'billing':
            services = ['billing', 'weight']
        else:
            services = [branch]


        res_network = subprocess.run(
            f"docker network inspect {env}_network >/dev/null 2>&1 || docker network create {env}_network",
            shell=True,
            check=True,
            capture_output=True
        )

        app.logger.info(res_network)


        results = {}
        for service in services:
            try:
                app.logger.info(f"Executing `{action}` on `{service}` in {env} environment...")

                service_path = YAML_PATHS[service][env]

                result = subprocess.run(
                    ["docker", "compose", "-f", service_path, action, "-d", "--build"]
                    if action == "up" else ["docker", "compose", "-f", service_path, action],
                    check=True, capture_output=True, text=True
                )

                results[service] = result  # Store successful process

            except subprocess.CalledProcessError as e:
                app.logger.error(f"Error executing `{action}` on `{service}`: {e.stderr.strip()}")
                send_slack_message(f"❌ *Action `{action}` failed for `{service}`*.\n\n*Error Output:*\n```{e.stderr.strip()}```")
                results[service] = e  # Store error object for later inspection

        if action == 'down':
            cleanup_result = subprocess.run(["docker", "container", "prune", "-f"], check=True, capture_output=True, text=True)

            app.logger.info("Removing all stopped containers...")
            app.logger.info(f"Cleanup result: {cleanup_result.stdout.strip()}")


        app.logger.info(f"Action `{action}` completed. Check results for any failures.")
        return results

    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return e


def check_yaml_path(service):
    services_to_check = []

    # Determine which services to check based on the input
    if service == 'billing' or service == 'main':
        services_to_check = ['billing', 'weight']
    elif service == 'weight':
        services_to_check = ['weight']
    else:
        print(f"Invalid service '{service}' provided.")
        return False

    # Check if all necessary YAML files exist for prod and test environments
    for service_to_check in services_to_check:
        # Check for 'prod' environment
        prod_path = YAML_PATHS[service_to_check].get('prod', None)
        if not prod_path or not os.path.isfile(prod_path):
            app.logger.info(f"YAML file for `{service_to_check}` in `prod` environment is missing: {prod_path}")
            return False

        # Check for 'test' environment
        # test_path = YAML_PATHS[service_to_check].get('test', None)
        # if not test_path or not os.path.isfile(test_path):
        #     app.logger.info(f"YAML file for `{service_to_check}` in `test` environment is missing: {test_path}")
        #     return False

    return True


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

        if branch.lower() not in YAML_PATHS:
            app.logger.info(f"No CI setup for branch: {branch}")
            return f"No CI setup for branch: {branch}"

        commit_hash = data["after"][:7]
        pusher_name = data["pusher"]["name"]
        pusher_email = data["pusher"]["email"]

        app.logger.info(
            f"CI triggered for branch: {branch} by {pusher_name} ({pusher_email})")
        
        app.logger.info(f"Pulling latest code for '{branch}'...")
        subprocess.run(["git", "checkout", branch], check=True)
        subprocess.run(["git", "pull", "origin", branch], check=True)

        app.logger.info("Check if docker-compose YAML files exist")
        if (not check_yaml_path(branch)):
            return "Missing files"
        


        app.logger.info(f"Running tests in container for '{branch}'...")
            
        
        # Change to run tests in future
        # result = manage_env('up', branch, 'test')
        result = subprocess.run([
            "docker", "run",
            "-v", f"/Gan-Shmuel/{branch}:/app",
            "-w", "/app",
            "hello-world",
        ], capture_output=True, text=True)

        app.logger.info("Finished running tests")

        if result.returncode == 0:
            send_slack_message(f"✅ *CI unit tests passed for `{branch}`*\nPusher: `{pusher_name}`\nCommit: `{commit_hash}`\n")
            
            if branch.lower() == 'main':
                result_down = manage_env(action='down', env='prod')
                result_up = manage_env(action='up', env='prod')
                app.logger.info("Finished deploying prod")
                
            else:
                app.logger.info("Branch is not main. Not deploying app")


        else:
            app.logger.info("Tests failed.")
            send_slack_message(
                f"❌ *CI unit tests failed for `{branch}`*\nPusher: `{pusher_name}`\nCommit: `{commit_hash}`\n\n*Error Output:*\n```{result.stderr.strip()}```"
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
