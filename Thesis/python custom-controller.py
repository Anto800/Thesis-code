from kubernetes import client, config, watch
import requests

config.load_kube_config()

v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

def get_haproxy_stats():
    response = requests.get('http://<haproxy-service-ip>:30081/stats;csv', auth=('username', 'password'))
    if response.status_code == 200:
        # Parse the CSV data and count the number of incoming connections
        stats = response.text.splitlines()
        connections = sum(int(line.split(',')[4]) for line in stats[1:] if line.split(',')[0])
        return connections
    else:
        return 0

def scale_deployment(deployment_name, namespace, replicas):
    body = {'spec': {'replicas': replicas}}
    apps_v1.patch_namespaced_deployment_scale(
        name=deployment_name, namespace=namespace, body=body)

def main():
    while True:
        connections = get_haproxy_stats()
        print(f"Current connections: {connections}")
        if connections > 100:  # Scale up if connections exceed 100
            scale_deployment('haproxy-vnf', 'default', 2)
        else:  # Scale down if connections are below 100
            scale_deployment('haproxy-vnf', 'default', 1)

if __name__ == '__main__':
    main()
