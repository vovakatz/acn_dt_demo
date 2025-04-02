# Microservices Python App Setup Guide

This guide provides instructions for setting up the complete microservices application on a local Kubernetes (Minikube) cluster.

## Local Development Environment Setup

Before deploying to Kubernetes, you may want to set up your local development environment:

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies for all services
pip install -r src/auth-service/requirements.txt
pip install -r src/converter-service/requirements.txt
pip install -r src/gateway-service/requirements.txt
pip install -r src/notification-service/requirements.txt

# Important: For auth-service, install psycopg2-binary
pip install psycopg2-binary
```

Note: If you encounter issues with psycopg2, use psycopg2-binary instead.

## Prerequisites

- Docker installed and running
- Minikube installed and running
- kubectl configured to work with Minikube

## Starting Minikube

```bash
# Start Minikube with sufficient resources
minikube start --memory=4096 --cpus=4

# Verify Minikube is running
minikube status
```

## Setup Script

Save the following as `setup.sh` in the root directory:

```bash
#!/bin/bash
set -e

echo "==== Starting Microservices Setup ===="

# Check if Minikube is running
if ! minikube status | grep -q "Running"; then
  echo "Minikube is not running. Please start Minikube first."
  exit 1
fi

# Build and load all service images
echo "==== Building and Loading Docker Images ===="

# Auth Service
echo "Building auth-service..."
docker build --no-cache -t auth-service:latest ./src/auth-service
minikube image load auth-service:latest


# Converter Service
echo "Building converter-service..."
docker build --no-cache -t converter-service:latest ./src/converter-service
minikube image load converter-service:latest

# Gateway Service
echo "Building gateway-service..."
docker build --no-cache -t gateway-service:latest ./src/gateway-service
minikube image load gateway-service:latest

# Notification Service
echo "Building notification-service..."
docker build --no-cache -t notification-service:latest ./src/notification-service
minikube image load notification-service:latest

# Deploy MongoDB
echo "==== Deploying MongoDB ===="
helm install mongodb ./helm_charts/MongoDB

# Deploy PostgreSQL
echo "==== Deploying PostgreSQL ===="
helm install postgres ./helm_charts/Postgres

# Deploy RabbitMQ
echo "==== Deploying RabbitMQ ===="
helm install rabbitmq ./helm_charts/RabbitMQ

# Deploy microservices
echo "==== Deploying Microservices ===="

# Deploy Auth Service
echo "Deploying auth-service..."
kubectl apply -f src/auth-service/manifest/configmap.yaml -f src/auth-service/manifest/secret.yaml -f src/auth-service/manifest/service.yaml -f src/auth-service/manifest/deployment.yaml

# Deploy Converter Service
echo "Deploying converter-service..."
kubectl apply -f src/converter-service/manifest/configmap.yaml -f src/converter-service/manifest/secret.yaml -f src/converter-service/manifest/converter-deploy.yaml

# Deploy Gateway Service
echo "Deploying gateway-service..."
kubectl apply -f src/gateway-service/manifest/configmap.yaml -f src/gateway-service/manifest/secret.yaml -f src/gateway-service/manifest/service.yaml -f src/gateway-service/manifest/gateway-deploy.yaml

# Deploy Notification Service
echo "Deploying notification-service..."
kubectl apply -f src/notification-service/manifest/configmap.yaml -f src/notification-service/manifest/secret.yaml -f src/notification-service/manifest/notification-deploy.yaml

# Wait for all pods to be ready
echo "==== Waiting for all pods to be ready ===="
kubectl wait --for=condition=ready pod --all --timeout=300s

# Create port-forward for gateway service
echo "==== Setup Port Forwarding ===="
echo "Creating port-forward for gateway service..."
echo "In a new terminal, run: kubectl port-forward service/gateway 8081:8080"

# Display all resources
echo "==== Deployment Complete ===="
echo "Deployed pods:"
kubectl get pods
echo ""
echo "Deployed services:"
kubectl get services
echo ""
echo "Access the application at: http://localhost:8081 (after starting port-forwarding)"
echo "OR use Minikube tunnel and access at: http://localhost:8080"
echo ""
echo "To start tunnel, run in a separate terminal: minikube tunnel"
```

## Setting Up the Application

1. Make the script executable and run it:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. For accessing the gateway service, you have two options:

   a. Use port forwarding (in a separate terminal):
   ```bash
   kubectl port-forward service/gateway 8081:8080
   ```
   Then access the application at: http://localhost:8081
   
   b. Use Minikube tunnel (in a separate terminal):
   ```bash
   minikube tunnel
   ```
   Then access the application at: http://localhost:8080

## Accessing Other Services

- MongoDB is accessible internally at: `mongodb:27017`
- PostgreSQL is accessible internally at: `db:5432`
- RabbitMQ is accessible internally at: `rabbitmq:5672`
- Auth service is accessible internally at: `auth:5000`

## Monitoring Pods

```bash
# Get all pods
kubectl get pods

# View logs for a specific pod
kubectl logs <pod-name>

# Get detailed information about a pod
kubectl describe pod <pod-name>
```

## Troubleshooting

1. **Image Pull Errors**: If you see `ImagePullBackOff` errors, ensure you've loaded the images into Minikube:
   ```bash
   minikube image load <image-name>:latest
   ```

2. **Pod Scheduling Issues**: Check for any node affinity or resource constraints:
   ```bash
   kubectl describe pod <pod-name>
   ```

3. **Service Connectivity**: If services can't connect to each other, verify the service names and ports in the configmaps.

4. **Persistent Volumes**: If PVs aren't creating properly, check your Minikube version and storage provisioner.

## Note for Mac users.
if running minikube on exitMac and arm64 architecture, you have to run the following command to update node affinity:
```bash
kubectl patch statefulset -n dynatrace localmp3producertest-activegate --type=json
  -p='[{"op":"replace","path":"/spec/template/spec/affinity/nodeAffinity/requiredDuringSchedulingIgnoredDuringExecution/nodeSelectorTerms/0/matchExpressions/0/values","value":["amd64","arm64"]}]'
```

## Cleanup

To delete all deployed resources:

```bash
kubectl delete deployments --all
kubectl delete statefulsets --all
kubectl delete services --all
kubectl delete configmaps --all
kubectl delete secrets --all
kubectl delete pvc --all
kubectl delete pv --all
```

To stop Minikube:

```bash
minikube stop
```