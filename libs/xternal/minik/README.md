Mini-K8s: Custom Container Orchestrator
A lightweight, declarative container orchestration system built in Python. This project simulates the core mechanics of Kubernetes, including a Control Plane, Data Plane, Self-Healing, and Dynamic Scaling.

Key Features
Declarative Configuration: Use YAML files to define the desired state of your cluster.

Centralized Master (Control Plane): A Flask-based API that manages the "Source of Truth" for the cluster state.

Autonomous Worker (Data Plane): An agent that interacts with the Docker SDK to manage container lifecycles.

Self-Healing (Reconciliation Loop): A background monitor that detects container failures and automatically restarts them to maintain the desired replica count.

Dynamic Scaling: Scale up or down instantly via CLI without modifying code or manually stopping containers.

Load Balancing & Service Discovery: A Round-Robin Load Balancer that dynamically discovers new replicas and provides a single entry point (Port 80).

 Architecture
The system is composed of four decoupled components:

CLI (orch.py): The user interface for deploying, scaling, and monitoring.

Master (master.py): The "Brain" that stores the desired cluster state.

Worker (worker.py): The "Muscle" that runs the reconciliation loop and talks to Docker.

Load Balancer (lb.py): The "Traffic Cop" that distributes incoming requests across healthy replicas.

🛠 Prerequisites
Python 3.10+

Docker Desktop (must be running)

Virtual Environment (recommended)

  ```` Bash
  pip install flask docker pyyaml requests
  ````

## Getting Started

### 1. Start the Orchestrator
Open four separate terminals and run the components in order:

**Terminal 1:** Master

````bash
python master.py
````
**Terminal 2: Worker**

````Bash
python worker.py
````

Terminal 3: Load Balancer
````Bash
python lb.py
````

### 2. Use the CLI

**Terminal 4:** _User Commands_

**Deploy**: Initialize the cluster using a YAML file.

````Bash
python orch.py apply deployment.yaml
````
Status: View the health and replica count of your service.

Bash
python orch.py status

Scale: Change the number of replicas on the fly.
Bash

python orch.py scale 5

 Demonstration of Self-Healing
Deploy 3 replicas: python orch.py apply deployment.yaml

Manually kill a container: docker stop <container_id>

Watch the Worker Terminal: It will detect the "drift" in state and re-spawn a replacement within 10 seconds.

Verify with python orch.py status.
