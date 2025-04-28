import os
import subprocess

REGULAR_INSTANCE_TEMPLATE = "email-service-pubsub-parse-gmail-instance-template"
REGULAR_MIG = "email-service-pubsub-parse-gmail-instance-template"
REGION = "asia-south1"


def run_command(command):
    print(f"Executing: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        exit(1)
    print(result.stdout)

def build_and_push_image():
    run_command("docker build --platform linux/amd64 -t gcr.io/rupiseva/parse-gmails-pubsub:latest .")
    run_command("docker push gcr.io/rupiseva/parse-gmails-pubsub:latest")

def delete_existing_templates():
    run_command(f"gcloud compute instance-templates delete {REGULAR_INSTANCE_TEMPLATE} --quiet")

def create_instance_templates():
    regular_template_cmd = (
        f"gcloud compute instance-templates create {REGULAR_INSTANCE_TEMPLATE} "
        "--machine-type=e2-medium "
        "--image-family=ubuntu-2204-lts "
        "--image-project=ubuntu-os-cloud "
        "--boot-disk-size=10GB "
        "--tags=http-server,ssh-server "
        "--metadata=enable-oslogin=FALSE "
        "--metadata-from-file startup-script=startup.sh "
        f"--region={REGION} "
        "--scopes=https://www.googleapis.com/auth/cloud-platform"
    )
    run_command(regular_template_cmd)


def delete_existing_migs():
    run_command(f"gcloud compute instance-groups managed delete {REGULAR_MIG} --region={REGION} --quiet")

def create_instance_groups():
    regular_group_cmd = (
        f"gcloud compute instance-groups managed create {REGULAR_MIG} "
        "--size=1 "
        f"--template={REGULAR_INSTANCE_TEMPLATE} "
        f"--region={REGION} "
        "--target-distribution-shape=ANY"
    )
    run_command(regular_group_cmd)

def configure_autoscaler():

    autoscaler_cmd = (
        f"gcloud compute instance-groups managed set-autoscaling {REGULAR_MIG} "
        f"--region={REGION} "
        "--min-num-replicas=1 "
        "--max-num-replicas=1 "
        "--cool-down-period=300 "
        "--mode=on"
    )
    run_command(autoscaler_cmd)

def configure_autoscaler_schedule():
    # Schedule to scale UP to 1 at 12:00 AM every day
    up_schedule_cmd = (
        f"gcloud compute instance-groups managed update-autoscaler {REGULAR_MIG} "
        f"--region={REGION} "
        "--update-schedule "
        "schedule=gmail-parsing-pubsub-startup-schedule "
        "--schedule-cron='30 18 * * *' "
        "--min-required-replicas=1 "
        "--description='Scale up to 1 at 12:00 AM IST'"
    )
    run_command(up_schedule_cmd)

    # Schedule to scale DOWN to 0 at 11:00 AM every day
    down_schedule_cmd = (
        f"gcloud compute instance-groups managed update-autoscaler {REGULAR_MIG} "
        f"--region={REGION} "
        "--update-schedule "
        "schedule=gmail-parsing-pubsub-shutdown-schedule "
        "--schedule-cron='30 10 * * *' "
        "--min-required-replicas=0 "
        "--description='Scale down to 0 at 11 AM IST'"
    )
    run_command(down_schedule_cmd)

def main():
    build_and_push_image()
    delete_existing_migs()
    delete_existing_templates()
    create_instance_templates()
    create_instance_groups()
    configure_autoscaler()
    configure_autoscaler_schedule()

if __name__ == "__main__":

    main()
