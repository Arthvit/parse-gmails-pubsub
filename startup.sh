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

# Set variables
REGION="asia-south1"
REGULAR_MIG="email-service-regular-template-group-without-thread-v2"
SPOT_MIG="email-service-spot-template-group-without-thread-v2"

# --- Prepare cron entries ---
CRON_JOBS=$(cat <<EOF
# Regular MIG scale UP at 12 AM IST
0 0 * * * . \$HOME/.bashrc; TZ='Asia/Kolkata' gcloud compute instance-groups managed set-autoscaling $REGULAR_MIG --region=$REGION --min-num-replicas=5 --max-num-replicas=5 --cool-down-period=3600 --mode=on >> /tmp/regular_up.log 2>&1

# Regular MIG scale DOWN at 10 AM IST
0 10 * * * . \$HOME/.bashrc; TZ='Asia/Kolkata' gcloud compute instance-groups managed set-autoscaling $REGULAR_MIG --region=$REGION --min-num-replicas=0 --max-num-replicas=0 --cool-down-period=3600 --mode=on >> /tmp/regular_down.log 2>&1

# Spot MIG scale UP at 12 AM IST
0 0 * * * . \$HOME/.bashrc; TZ='Asia/Kolkata' gcloud compute instance-groups managed set-autoscaling $SPOT_MIG --region=$REGION --min-num-replicas=15 --max-num-replicas=15 --cool-down-period=900 --mode=on >> /tmp/spot_up.log 2>&1

# Spot MIG scale DOWN at 10 AM IST
0 10 * * * . \$HOME/.bashrc; TZ='Asia/Kolkata' gcloud compute instance-groups managed set-autoscaling $SPOT_MIG --region=$REGION --min-num-replicas=0 --max-num-replicas=0 --cool-down-period=900 --mode=on >> /tmp/spot_down.log 2>&1
EOF
)

# --- Install new crontab ---
( crontab -l 2>/dev/null; echo "$CRON_JOBS" ) | crontab -

echo "✅ Crontab updated with autoscaler schedules."