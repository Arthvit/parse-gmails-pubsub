#!/bin/bash

apt-get clean
journalctl --vacuum-time=1d
find /var/log -type f -name "*.gz" -delete

# Update and install dependencies
sudo apt-get update
sudo apt-get install -y docker.io cron

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

# --- Configure Autoscaler using cron ---

# Define variables (ensure these match your MIG and region)
REGULAR_MIG="email-service-regular-template-group-without-thread-v2"
SPOT_MIG="email-service-spot-template-group-without-thread-v2"
REGION="asia-south1"

# Construct the gcloud command for autoscaler configuration
REGULAR_AUTOSCALER_COMMAND_UP="gcloud compute instance-groups managed set-autoscaling $REGULAR_MIG \
    --region=$REGION \
    --min-num-replicas=5 \
    --max-num-replicas=5 \
    --cool-down-period=3600 \
    --mode=on"
REGULAR_CRON_SCHEDULE_UP="0 0 * * * TZ='Asia/Kolkata' $REGULAR_AUTOSCALER_COMMAND_UP"
(crontab -l 2>/dev/null; echo "$REGULAR_CRON_SCHEDULE_UP") | crontab -

REGULAR_AUTOSCALER_COMMAND_DOWN="gcloud compute instance-groups managed set-autoscaling $REGULAR_MIG \
    --region=$REGION \
    --min-num-replicas=0 \
    --max-num-replicas=0 \
    --cool-down-period=3600 \
    --mode=on"
REGULAR_CRON_SCHEDULE_DOWN="0 12 * * * TZ='Asia/Kolkata' $REGULAR_AUTOSCALER_COMMAND_DOWN"
(crontab -l 2>/dev/null; echo "$REGULAR_CRON_SCHEDULE_DOWN") | crontab -

SPOT_AUTOSCALER_COMMAND_UP="gcloud compute instance-groups managed set-autoscaling $SPOT_MIG \
    --region=$REGION \
    --min-num-replicas=15 \
    --max-num-replicas=15 \
    --cool-down-period=900 \
    --mode=on"
SPOT_CRON_SCHEDULE_UP="0 0 * * * TZ='Asia/Kolkata' $SPOT_AUTOSCALER_COMMAND_UP"
(crontab -l 2>/dev/null; echo "$SPOT_CRON_SCHEDULE_UP") | crontab -

SPOT_AUTOSCALER_COMMAND_DOWN="gcloud compute instance-groups managed set-autoscaling $SPOT_MIG \
    --region=$REGION \
    --min-num-replicas=0 \
    --max-num-replicas=0 \
    --cool-down-period=900 \
    --mode=on"
SPOT_CRON_SCHEDULE_DOWN="0 12 * * * TZ='Asia/Kolkata' $SPOT_AUTOSCALER_COMMAND_DOWN"
(crontab -l 2>/dev/null; echo "$SPOT_CRON_SCHEDULE_DOWN") | crontab -