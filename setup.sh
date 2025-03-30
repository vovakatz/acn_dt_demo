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
cd src/auth-service
docker build -t auth-service:latest .
minikube image load auth-service:latest
cd ../..

# Converter Service
echo "Building converter-service..."
cd src/converter-service
docker build -t converter-service:latest .
minikube image load converter-service:latest
cd ../..

# Gateway Service
echo "Building gateway-service..."
cd src/gateway-service
docker build -t gateway-service:latest .
minikube image load gateway-service:latest
cd ../..

# Notification Service
echo "Building notification-service..."
cd src/notification-service
docker build -t notification-service:latest .
minikube image load notification-service:latest
cd ../..

# Update the notification deployment file to use the local image
sed -i.bak 's|image: nasi101/notification|image: notification-service:latest\n          imagePullPolicy: IfNotPresent|g' src/notification-service/manifest/notification-deploy.yaml

# Deploy MongoDB
echo "==== Deploying MongoDB ===="
cd Helm_charts/MongoDB
kubectl apply -f templates/storageclass.yaml
kubectl apply -f templates/configmap.yaml
kubectl apply -f templates/secret.yaml
kubectl apply -f templates/pv.yaml
kubectl apply -f templates/pvc.yaml
kubectl apply -f templates/service.yaml
kubectl apply -f templates/statefulset.yaml
cd ../..

# Deploy PostgreSQL
echo "==== Deploying PostgreSQL ===="
cd Helm_charts/Postgres
kubectl apply -f templates/postgres-service.yaml
kubectl apply -f templates/postgres-deploy.yaml
cd ../..

# Deploy RabbitMQ
echo "==== Deploying RabbitMQ ===="
cd Helm_charts/RabbitMQ
kubectl apply -f templates/storageclasses.yaml
kubectl apply -f templates/configmap.yaml
kubectl apply -f templates/secret.yaml
kubectl apply -f templates/pv.yaml
kubectl apply -f templates/pvc.yaml
kubectl apply -f templates/service.yaml
kubectl apply -f templates/statefulset.yaml
cd ../..

# Deploy microservices
echo "==== Deploying Microservices ===="

# Deploy Auth Service
echo "Deploying auth-service..."
cd src/auth-service
kubectl apply -f manifest/configmap.yaml -f manifest/secret.yaml -f manifest/service.yaml -f manifest/deployment.yaml
cd ../..

# Deploy Converter Service
echo "Deploying converter-service..."
cd src/converter-service
kubectl apply -f manifest/configmap.yaml -f manifest/secret.yaml -f manifest/converter-deploy.yaml
cd ../..

# Deploy Gateway Service
echo "Deploying gateway-service..."
cd src/gateway-service
kubectl apply -f manifest/configmap.yaml -f manifest/secret.yaml -f manifest/service.yaml -f manifest/gateway-deploy.yaml
cd ../..

# Deploy Notification Service
echo "Deploying notification-service..."
cd src/notification-service
kubectl apply -f manifest/configmap.yaml -f manifest/secret.yaml -f manifest/notification-deploy.yaml
cd ../..

# Wait for all pods to be ready
echo "==== Waiting for all pods to be ready ===="
kubectl wait --for=condition=ready pod --all --timeout=300s || echo "Warning: Not all pods are ready yet, but continuing..."

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

# Instructions for Dynatrace (optional)
echo ""
echo "==== Optional: Deploy Dynatrace ===="
echo "To deploy Dynatrace monitoring, run:"
echo "kubectl apply -f dynakube.yaml"
echo "If the ActiveGate pod stays in Pending state, run:"
echo "kubectl patch statefulset connector-activegate -n dynatrace --type json -p '[{\"op\": \"remove\", \"path\": \"/spec/template/spec/affinity\"}]'"