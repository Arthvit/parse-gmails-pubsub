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

def main():
    build_and_push_image()
    delete_existing_migs()
    delete_existing_templates()
    create_instance_templates()
    create_instance_groups()

if __name__ == "__main__":

    main()
