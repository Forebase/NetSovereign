from flask import Flask, request, jsonify
import docker
import threading
import time

import requests

app = Flask(__name__)



# Initialize the Docker client
try:
    client = docker.from_env()
except Exception as e:
    print(f"Error: Could not connect to Docker. Is it running? {e}")



@app.route('/containers', methods=['GET'])
def list_containers():
    """Returns a list of all running containers managed by this orchestrator"""
    try:
        # We only count containers that have 'web-api' in their name
        managed = [
            {
                "id": c.short_id,
                "name": c.name,
                "status": c.status
            } 
            for c in client.containers.list() if "web-api" in c.name
        ]
        return jsonify(managed), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/spawn', methods=['POST'])
def spawn_container():
    data = request.get_json()
    image = data.get('image')
    # We add a timestamp to the name to keep it unique
    name = f"{data.get('service_name')}-{int(time.time())}"
    ports = data.get('port_mapping') 

    try:
        print(f"Pulling image {image}...")
        client.images.pull(image)
        
        print(f"Starting container {name}...")
        container = client.containers.run(
            image,
            name=name,
            ports=ports,
            detach=True
        )
        
        return jsonify({
            "status": "success",
            "container_id": container.short_id,
            "container_name": name
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- HEALTH MONITOR LOGIC ) ---
def health_monitor():
    print("Monitor Thread: Active and reconciling...")
    while True:
        try:
            resp = requests.get("http://localhost:5000/status")
            if resp.status_code == 200:
                state = resp.json()
                desired_replicas = int(state.get('replicas', 0))
                service_name = state.get('service_name')
                image = state.get('image')

                # 1. Get ALL containers (including those starting up or exited)
                all_containers = client.containers.list(all=True, filters={"name": service_name})
                
                # 2. Cleanup: Remove dead/exited containers so they don't block ports
                for c in all_containers:
                    if c.status not in ['running', 'restarting', 'created']:
                        print(f" Pruning dead container: {c.name}")
                        c.remove(force=True)

                # 3. Re-scan after cleanup
                active_containers = client.containers.list(filters={"name": service_name})
                actual_count = len(active_containers)

                # 4. SCALE UP logic
                if actual_count < desired_replicas:
                    # Find which ports are already taken
                    used_ports = []
                    for c in active_containers:
                        # Extract port from Docker's complex port mapping
                        p_map = c.attrs['HostConfig']['PortBindings']
                        for key in p_map:
                            used_ports.append(int(p_map[key][0]['HostPort']))

                    # Find the first available port starting from 8080
                    new_port = 8080
                    while new_port in used_ports:
                        new_port += 1

                    print(f" Scaling Up: Starting {service_name} on Port {new_port}")
                    client.containers.run(
                        image,
                        name=f"{service_name}-{int(time.time())}",
                        ports={"80/tcp": new_port},
                        detach=True
                    )
                
                # 5. SCALE DOWN logic
                elif actual_count > desired_replicas:
                    print(f" Scaling Down: Removing surplus container")
                    active_containers[0].stop()
                    active_containers[0].remove()

        except Exception as e:
            print(f"Monitor Error: {e}")
        
        time.sleep(10) # Increased to 10s to give Docker time to finish networking

# Start the monitor thread BEFORE the Flask app starts blocking
monitor_thread = threading.Thread(target=health_monitor, daemon=True)
monitor_thread.start()

if __name__ == '__main__':
    # Flask starts here and stays here
    app.run(host='0.0.0.0', port=5001, debug=False)