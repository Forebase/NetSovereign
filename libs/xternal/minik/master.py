from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)
STATE_FILE = "cluster_state.json"

@app.route('/deploy', methods=['POST'])
def deploy():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data received"}), 400

    print(f"Updating Desired State for: {data.get('service_name')}")

    # SAVE THE DESIRED STATE (The Source of Truth)
    with open(STATE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

    # We return success immediately. 
    # The Worker's background thread will see this new file and fix the containers.
    return jsonify({
        "status": "success",
        "message": "Desired state updated. The Worker will reconcile changes shortly.",
        "desired_replicas": data.get('replicas')
    }), 200

@app.route('/status', methods=['GET'])
def get_status():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({"message": "No active deployments found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)