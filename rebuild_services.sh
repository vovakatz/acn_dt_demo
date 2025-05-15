#!/bin/bash

# Exit on error
set -e

echo "==== Rebuilding and Redeploying Services ===="

# Delete existing deployments
echo "Deleting existing deployments..."
kubectl delete deployment auth --ignore-not-found=true
kubectl delete deployment converter --ignore-not-found=true
kubectl delete deployment gateway --ignore-not-found=true
kubectl delete deployment notification --ignore-not-found=true

# Build and load all service images
echo "==== Building and Loading Docker Images ===="

cd src

# Auth Service
echo "Building auth-service..."
docker build -t auth-service:latest -f auth-service/Dockerfile .
#minikube image load auth-service:latest
kind load docker-image auth-service:latest --name dt-test

# Converter Service
echo "Building converter-service..."
docker build -t converter-service:latest -f converter-service/Dockerfile .
#minikube image load converter-service:latest
kind load docker-image converter-service:latest --name dt-test

# Gateway Service
echo "Building gateway-service..."
docker build -t gateway-service:latest -f gateway-service/Dockerfile .
#minikube image load gateway-service:latest
kind load docker-image gateway-service:latest --name dt-test

# Notification Service
echo "Building notification-service..."
docker build -t notification-service:latest -f notification-service/Dockerfile .
#minikube image load notification-service:latest
kind load docker-image notification-service:latest --name dt-test

# Deploy microservices
echo "==== Deploying Microservices ===="

# Deploy Auth Service
echo "Deploying auth-service..."
cd auth-service
kubectl apply -f manifest/configmap.yaml -f manifest/secret.yaml -f manifest/service.yaml -f manifest/deployment.yaml
cd ..

# Deploy Converter Service
echo "Deploying converter-service..."
cd converter-service
kubectl apply -f manifest/configmap.yaml -f manifest/secret.yaml -f manifest/converter-deploy.yaml
cd ..

# Deploy Gateway Service
echo "Deploying gateway-service..."
cd gateway-service
kubectl apply -f manifest/configmap.yaml -f manifest/secret.yaml -f manifest/service.yaml -f manifest/gateway-deploy.yaml
cd ..

# Deploy Notification Service
echo "Deploying notification-service..."
cd notification-service
kubectl apply -f manifest/configmap.yaml -f manifest/secret.yaml -f manifest/notification-deploy.yaml
cd ..

# Wait for all pods to be ready
echo "==== Waiting for all pods to be ready ===="
kubectl wait --for=condition=ready pod --all --timeout=300s || echo "Warning: Not all pods are ready yet, but continuing..."

echo "==== Deployment Complete ===="
echo "Check pod status with: kubectl get pods"
