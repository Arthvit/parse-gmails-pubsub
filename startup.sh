#!/bin/bash

apt-get clean
journalctl --vacuum-time=1d
find /var/log -type f -name "*.gz" -delete

# Update and install dependencies
sudo apt-get update
sudo apt-get install -y docker.io

# Configure Docker to use GCP credentials
gcloud auth configure-docker

# Pull the container from GCR
docker pull gcr.io/rupiseva/parse-gmails-pubsub:latest


NUM_CONTAINERS=1  # Change this based on available CPU/memory

# Run multiple containers
for i in $(seq 1 $NUM_CONTAINERS); do
    if docker ps -a | grep -q "email-service-$i"; then
        docker rm -f "email-service-$i"
    fi
    docker run -d --name email-service-$i gcr.io/rupiseva/parse-gmails-pubsub:latest
done
