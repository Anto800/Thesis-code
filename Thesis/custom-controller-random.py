from kubernetes import client, config
import requests
import time
import re

# Load Kubernetes configuration
config.load_kube_config()

# Set up the Kubernetes API client
apps_v1 = client.AppsV1Api()

# Function to get the current HAProxy metrics
def get_haproxy_metrics():
    try:
        response = requests.get('http://localhost:9101/metrics')
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching HAProxy stats: {e}")
        return None

# Function to update the HAProxy deployment resource requests and limits
def update_haproxy_resources(cpu_request, cpu_limit, memory_request, memory_limit):
    deployment_name = "haproxy-vnf"
    namespace = "default"

    # Retrieve the current deployment to get the image name
    try:
        deployment = apps_v1.read_namespaced_deployment(name=deployment_name, namespace=namespace)
        container = deployment.spec.template.spec.containers[0]
        image_name = container.image
    except client.exceptions.ApiException as e:
        print(f"Error retrieving deployment: {e}")
        return

    # Define the patch for the resources
    resource_patch = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "haproxy",
                            "image": image_name,
                            "resources": {
                                "requests": {
                                    "cpu": cpu_request,
                                    "memory": memory_request
                                },
                                "limits": {
                                    "cpu": cpu_limit,
                                    "memory": memory_limit
                                }
                            }
                        }
                    ]
                }
            }
        }
    }

    # Patch the deployment with the new resource requests and limits
    try:
        apps_v1.patch_namespaced_deployment(name=deployment_name, namespace=namespace, body=resource_patch)
        print(f"Updated {deployment_name} resources: CPU={cpu_request}/{cpu_limit}, Memory={memory_request}/{memory_limit}")
    except client.exceptions.ApiException as e:
        print(f"Error updating deployment resources: {e}")

# Function to determine resource allocation based on metrics
def determine_resource_allocation(metrics):
    import random
    schemes = [
        {"cpu_request": "250m", "cpu_limit": "500m", "memory_request": "256Mi", "memory_limit": "512Mi"},
        {"cpu_request": "500m", "cpu_limit": "1", "memory_request": "512Mi", "memory_limit": "1Gi"},
        {"cpu_request": "1", "cpu_limit": "2", "memory_request": "1Gi", "memory_limit": "2Gi"}
    ]
    return random.choice(schemes)

# Main loop to continuously fetch metrics and update resources
while True:
    metrics = get_haproxy_metrics()
    if metrics:
        current_connections = 0
        for line in metrics.split('\n'):
            match = re.match(r'haproxy_frontend_connections_total{.*} (\d+)', line)
            if match:
                current_connections = int(match.group(1))
                break

        print(f"Current connections: {current_connections}")

        # Determine new resource allocation based on metrics
        new_resources = determine_resource_allocation(metrics)
        update_haproxy_resources(
            cpu_request=new_resources['cpu_request'],
            cpu_limit=new_resources['cpu_limit'],
            memory_request=new_resources['memory_request'],
            memory_limit=new_resources['memory_limit']
        )
    
    # Wait for a while before the next iteration
    time.sleep(2) 
