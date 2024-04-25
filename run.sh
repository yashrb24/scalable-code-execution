#!/bin/bash
k3d cluster delete k3s-default
k3d cluster create -p "80:80@loadbalancer" --agents 2
kubectl apply --filename kubernetes/
