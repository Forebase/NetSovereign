import yaml
import requests
import sys

MASTER_URL = "http://localhost:5000"

def get_status():
    try:
        # 1. Get the 'Plan' from the Master
        master_resp = requests.get(f"{MASTER_URL}/status")
        if master_resp.status_code != 200:
            print("No active deployments.")
            return

        plan = master_resp.json()
        desired = plan.get('replicas', 0)
        
        # 2. Get the 'Reality' from the Worker
        # We'll assume your Worker is on 5001 and has a /containers endpoint
        try:
            worker_resp = requests.get("http://localhost:5001/containers")
            actual = len(worker_resp.json()) if worker_resp.status_code == 200 else 0
        except:
            actual = "Unknown (Worker Offline)"

        print("\n=== ORCHESTRATOR DASHBOARD ===")
        print(f"Service: {plan.get('service_name')}")
        print(f"Image:   {plan.get('image')}")
        print(f"Status:  [{actual}/{desired}] Replicas Healthy")
        
        if actual == desired:
            print(" SYSTEM STABLE")
        else:
            print(" RECONCILING (Master and Worker are syncing...)")
            
    except Exception as e:
        print(f"Error: {e}")
def deploy(file_path):
    """Sends a YAML file to the Master"""
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        response = requests.post(f"{MASTER_URL}/deploy", json=data)
        if response.status_code == 200:
            print(" Successfully deployed!")
        else:
            print(f" Deployment failed: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
        
def scale(new_replicas):
    """Updates the number of replicas without needing to edit the YAML file"""
    try:
        # 1. Get current state from Master
        current_resp = requests.get(f"{MASTER_URL}/status")
        if current_resp.status_code != 200:
            print(" No active deployment found to scale.")
            return
        
        current_data = current_resp.json()
        
        # 2. Update only the replicas count
        current_data['replicas'] = int(new_replicas)
        
        # 3. Send the updated data back to the Master's deploy endpoint
        print(f" Requesting scale to {new_replicas} replicas...")
        response = requests.post(f"{MASTER_URL}/deploy", json=current_data)
        
        if response.status_code == 200:
            print(f" Successfully scaled to {new_replicas} replicas!")
        else:
            print(f" Scale failed: {response.text}")
            
    except Exception as e:
        print(f"Error during scaling: {e}")



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python orch.py [apply <file> | status | scale <replicas>]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "apply" and len(sys.argv) == 3:
        deploy(sys.argv[2])
    elif command == "status":
        get_status()
    elif command == "scale" and len(sys.argv) == 3:
        scale(sys.argv[2])    
    
    else:
        print("Invalid command. Use 'apply <file>', 'status', or 'scale <replicas>'.")