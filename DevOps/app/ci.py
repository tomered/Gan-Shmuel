from pathlib import Path
from flask import Flask, Response, request, jsonify
from logger_config import setup_logger
from dotenv import load_dotenv
import subprocess
import threading
import requests
import time
import json
import os
import psutil

load_dotenv()  # Load .env file if it exists

app = Flask(__name__)
setup_logger(app)
HTML_FILE = Path(__file__).parent / "index.html"

# CONFIG
HOST_IP = '43.205.160.125'
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
SERVICES_CONFIGURATION = {
    'billing': {
        'prod': {
            'yaml': './Billing/docker-compose.prod.yaml',
            'port': '8081',
        },
        'test': {
            'yaml': './Billing/docker-compose.test.yaml',
            'port': '8083',
        },
    },
    'weight': {
        'prod': {
            'yaml': './Weight/docker-compose.prod.yaml',
            'port': '8082',
        },
        'test': {
            'yaml': './Weight/docker-compose.test.yaml',
            'port': '8084',
        },
    },
    'main': '.'
}


def check_service_health(compose_res, service, env, port):
    app.logger.info(
        f"Running health check and pytest for `{service}` with port `{port}`")

    for i in range(10):  # Retry 10 times
        try:
            health_check_res = requests.get(
                f"http://{HOST_IP}:{port}/health", timeout=5)
            if health_check_res.status_code == 200:
                break  # Success, exit loop
        except requests.RequestException as e:
            app.logger.info(f"Connection failed, retrying... ({i+1}/5)")

        time.sleep(2 ** i)  # Exponential backoff

    if (env == 'test'):
        app.logger.info(f"Running pytests for {service}")
        pytest_res = subprocess.run(
            ["docker", "inspect", f"{service}-test",
             "--format", "{{.State.ExitCode}}"],
            capture_output=True, text=True, check=True
        )
        if compose_res.returncode == 0 and health_check_res.status_code == 200 and pytest_res.returncode == 0:
            app.logger.info(f"Tests passed and service {service} is healthy ")
            service_final_res = True
        else:
            app.logger.info(
                f"Service {service} is not healthy. compose results: `{compose_res.stderr}` health check results: `{health_check_res.status_code}`")
            service_final_res = False
    else:
        pytest_res = None
        if compose_res.returncode == 0 and health_check_res.status_code == 200:
            app.logger.info(f"Tests passed and service {service} is healthy ")
            service_final_res = True
        else:
            app.logger.info(
                f"Service {service} is not healthy. compose results: `{compose_res.stderr}` health check results: `{health_check_res.status_code}`")
            service_final_res = False

    results = {
        "returncode": compose_res.returncode,
        "stdout": compose_res.stdout.strip(),
        "stderr": compose_res.stderr.strip(),
        "health_check": health_check_res.status_code,
        "pytest": pytest_res.stdout.strip(),
        "service_final_res": service_final_res,
    }

    return results


def manage_env(action, env, branch='main'):
    valid_actions = {"up", "down"}
    if action not in valid_actions:
        app.logger.error(f"Invalid action '{action}'. Use 'up' or 'down'.")
        return ValueError(f"Invalid action '{action}'. Use 'up' or 'down'.")

    app.logger.info(
        f"Deploying: `{branch}` in `{env}` environment...")

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
            app.logger.info(
                f"Executing `{action}` on `{service}` in {env} environment...")
            yaml_path = SERVICES_CONFIGURATION[service][env]['yaml']
            port = SERVICES_CONFIGURATION[service][env]['port']
            compose_res = subprocess.run(
                ["docker", "compose", "-f", yaml_path,
                    "-p", env, action, "-d", "--build"]
                if action == "up" else ["docker", "compose", "-p", env, action],
                check=True, capture_output=True, text=True
            )

            if action == "up":
                service_health_check_res = check_service_health(
                    compose_res, service, env, port)
                results[service] = service_health_check_res

        if action == 'down':
            cleanup_result = subprocess.run(
                ["docker", "container", "prune", "-f"], check=True, capture_output=True, text=True)

            app.logger.info("Removing all stopped containers...")
            app.logger.info(f"Cleanup result: {cleanup_result.stdout.strip()}")
            return
        elif action == 'up':
            if all(service.get('service_final_res') for service in results.values()):
                app.logger.info(
                    f"Deployment of `{branch}` in {env} completed.")
                return True, results
            else:
                return False, results

    except subprocess.CalledProcessError as e:
        app.logger.error(
            f"Error executing `{action}` on `{service}`: {e.stderr.strip()}")
        send_slack_message(
            f"❌ *Action `{action}` failed for `{service}`*.\n\n*Error Output:*\n```{e.stderr.strip()}```")
        return {"error": e.stderr.strip()}

    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return e


def check_yaml_path(service):
    app.logger.info("Checking if docker-compose YAML files exist")
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
        prod_config = SERVICES_CONFIGURATION.get(
            service_to_check, {}).get('prod', {})
        prod_path = prod_config.get('yaml', None)
        if not prod_path or not os.path.isfile(prod_path):
            app.logger.error(
                f"YAML file for `{service_to_check}` in `prod` environment is missing")
            return False

        # Check for 'test' environment
        test_config = SERVICES_CONFIGURATION.get(
            service_to_check, {}).get('test', {})
        test_path = test_config.get('yaml', None)
        if not test_path or not os.path.isfile(test_path):
            app.logger.error(
                f"YAML file for `{service_to_check}` in `test` environment is missing")
            return False

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

        if branch.lower() not in SERVICES_CONFIGURATION:
            app.logger.info(f"No CI setup for branch: {branch}")
            return f"No CI setup for branch: {branch}"

        commit_hash = data["after"][:7]
        pusher_name = data["pusher"]["name"]
        pusher_email = data["pusher"]["email"]

        app.logger.info(
            f"CI triggered for branch: {branch} by {pusher_name} ({pusher_email})")

        app.logger.info(f"Pulling latest code for '{branch}'...")
        subprocess.run(["git", "checkout", branch], check=True)
        subprocess.run(
            ["git", "pull", "-q", "origin", branch], check=True)
        app.logger.info(f"Finished pulling for '{branch}'...")

        if (not check_yaml_path(branch)):
            return "Missing files"

        # Change to run tests in future
        app.logger.info(f"Running tests for '{branch}'...")
        result = manage_env('up', 'test', branch)
        app.logger.info("Finished running tests")

        if result[0]:
            send_slack_message(
                f"✅ *CI unit tests passed for `{branch}`*\nPusher: `{pusher_name}`\nCommit: `{commit_hash}`\n")
            manage_env('down', 'prod', branch)

            if branch.lower() == 'main':
                result_down = manage_env(action='down', env='prod')
                result_up = manage_env(action='up', env='prod')
                app.logger.info("Finished deploying prod")

            else:
                app.logger.info("Branch is not main. Not deploying app")

        else:
            app.logger.info("Tests failed.")
            send_slack_message(
                f"❌ *CI tests failed for `{branch}`*\nPusher: `{pusher_name}`\nCommit: `{commit_hash}`\n\n*Error Output:*\n```{result[1]}```"
            )
            manage_env('down', 'prod', branch)

    except Exception as e:
        app.logger.error(f"CI pipeline error: {e}")
        send_slack_message(f"CI error on branch `{branch}`:\n```{e}```")
        return f"Unhandled pipeline error {e}"


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


@app.route("/metrics")
def metrics():
    if "application/json" in request.headers.get("Accept", ""):
        return jsonify({
            "cpu_percent": psutil.cpu_percent(),
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage('/')._asdict(),
            "load_avg": psutil.getloadavg()
        })

    # Serve the HTML dashboard
    return Response(HTML_FILE.read_text(), mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
