from flask import Flask
import requests

app = Flask(__name__)

# Track which replica to send the next request to
current_index = 0

def update_backends():
    """Asks the Master how many replicas are actually running"""
    try:
        # Service Discovery: Asking the Master for the current state
        resp = requests.get("http://localhost:5000/status")
        data = resp.json()
        replicas = int(data.get('replicas', 1))
        # Create the list: [http://localhost:8080, http://localhost:8081, ...]
        return [f"http://localhost:{8080 + i}" for i in range(replicas)]
    except Exception as e:
        print(f"Service Discovery failed: {e}")
        return ["http://localhost:8080"] # Fallback

@app.route('/')
@app.route('/<path:path>')
def load_balance(path=""):
    global current_index
    
    # 1. Get the latest list of backends
    backends = update_backends()
    
    # 2. Pick the target using Round Robin logic
    target_base = backends[current_index % len(backends)]
    target_url = f"{target_base}/{path}"
    
    # 3. Increment the counter for the next request
    current_index += 1
    
    print(f" Round Robin: Routing to {target_url}")
    
    try:
        # 4. Proxy the request to the chosen replica
        resp = requests.get(target_url, timeout=2)
        return resp.content, resp.status_code
    except Exception as e:
        return f" Replica at {target_url} is unavailable. Health check will restart it soon.", 502

if __name__ == '__main__':
    print(" Smart Load Balancer started on Port 80")
    app.run(host='0.0.0.0', port=80)