import time
import re
from kubernetes import client, config
import requests

# Initialize the Kubernetes client
config.load_kube_config()
api_instance = client.AppsV1Api()

# Define resource schemes
resource_schemes = [
    {"cpu_request": "100m", "cpu_limit": "200m", "memory_request": "128Mi", "memory_limit": "256Mi"},
    {"cpu_request": "250m", "cpu_limit": "500m", "memory_request": "256Mi", "memory_limit": "512Mi"},
    {"cpu_request": "500m", "cpu_limit": "1", "memory_request": "512Mi", "memory_limit": "1Gi"},
    {"cpu_request": "1", "cpu_limit": "2", "memory_request": "1Gi", "memory_limit": "2Gi"}
]

# Fetch HAProxy metrics
def fetch_haproxy_metrics():
    try:
        response = requests.get("http://localhost:9101/metrics")
        response.raise_for_status()
        metrics = response.text

        # Use regex to find the line that contains haproxy_frontend_current_sessions with http="stats"
        match = re.search(r'haproxy_frontend_current_sessions\{.*frontend="stats".*?\} (\d+)', metrics)
        if match:
            current_connections = int(match.group(1))
            return current_connections

        print("haproxy_frontend_current_sessions with http=\"stats\" not found in metrics")
        return None

    except Exception as e:
        print("Error fetching HAProxy stats:", e)
        return None

# Adjust the resources of the deployment
def adjust_resources(deployment_name, namespace, resource_scheme):
    try:
        deployment = api_instance.read_namespaced_deployment(deployment_name, namespace)
        deployment.spec.template.spec.containers[0].resources = client.V1ResourceRequirements(
            requests={"cpu": resource_scheme["cpu_request"], "memory": resource_scheme["memory_request"]},
            limits={"cpu": resource_scheme["cpu_limit"], "memory": resource_scheme["memory_limit"]}
        )
        api_instance.patch_namespaced_deployment(deployment_name, namespace, deployment)
        print(f"Updated {deployment_name} resources: CPU={resource_scheme['cpu_request']}/{resource_scheme['cpu_limit']}, Memory={resource_scheme['memory_request']}/{resource_scheme['memory_limit']}")
    except client.ApiException as e:
        print("Error updating deployment resources:", e)

# Main controller loop
while True:
    current_connections = fetch_haproxy_metrics()
    if current_connections is not None:
        print(f"Current connections: {current_connections}")
        
        if current_connections < 20:
            adjust_resources("haproxy-vnf", "default", resource_schemes[0])
        elif 20 <= current_connections < 40:
            adjust_resources("haproxy-vnf", "default", resource_schemes[1])
        elif 40 <= current_connections < 60:
            adjust_resources("haproxy-vnf", "default", resource_schemes[2])
        else:
            adjust_resources("haproxy-vnf", "default", resource_schemes[3])
    
    # Wait for a while before checking again
    time.sleep(2)
