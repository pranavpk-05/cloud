# AWS CloudFormation deployment — Student Registration

This deployment belongs to **pranavpk-05/cloud**, with its Flask code under `student-registration/`.

## Important: chargeable resources

This template is **not running in AWS merely because the file exists in GitHub**. Creating the stack will launch a billable EC2 instance, RDS MySQL database, public IPv4 address, EBS volume, S3 bucket and AWS Secrets Manager secret. Check AWS Billing and the estimated recurring charges before submitting. The account's verification-in-progress status may temporarily prevent provisioning.

To avoid changing the unverified existing `project-vpc` configuration, the stack creates a **new dedicated VPC, 10.0.0.0/16**. The original VPC is untouched. No NAT Gateway or load balancer is created.

## Deploy in the AWS Console

**First merge the deployment pull request into `main`**, because EC2 clones that branch during startup.

1. Visit [CloudFormation in Mumbai](https://ap-south-1.console.aws.amazon.com/cloudformation/home?region=ap-south-1).
2. Choose **Create stack → With new resources (standard)**.
3. Choose **Upload a template file** and upload `infrastructure/aws-flask-stack.yaml` (download from this repository after merge).
4. Stack name: `ict-student-registration`. The `HttpAllowedCidr` parameter defaults to `0.0.0.0/0` for a classroom demonstration. Restrict it to your own public IP with `/32` if the page must be private.
5. Review billing implications and enable the IAM acknowledgment, then **Submit**. AWS may reject provisioning if account verification remains incomplete.
6. After **CREATE_COMPLETE**, open the CloudFormation stack's **Outputs** for the EC2 public website URL, RDS ID, S3 bucket, VPC and subnet IDs.
7. Wait for EC2 bootstrapping and then verify the URL loads. **CREATE_COMPLETE does not guarantee the app deployed successfully.**

## Verify the live infrastructure

Use **EC2 → Instances → your web instance → Connect → Session Manager** (the security group allows no inbound SSH). SSM session permissions and network access must be available.

Run:

```bash
sudo tail -n 100 /var/log/student-registration-bootstrap.log
sudo systemctl status student-registration.service --no-pager
sudo journalctl -u student-registration.service -n 80 --no-pager
curl -i http://127.0.0.1/
```

Submit a form with **fictitious** data and a test image (site is only HTTP). Then:

- **S3 → bucket → Objects → students/** should show a new JPEG.
- **RDS → Databases → DB details** should show `Publicly accessible: No`.
- **VPC → Security groups → db-sg** should show port 3306 open only from web-sg.
- **VPC → Route tables** should show an Internet Gateway route only for the public subnet.
- **IAM → Roles** should show the EC2 instance role with scoped access to the S3 prefix and database secret.
- From the EC2 SSM session, check database rows:

```bash
sudo bash -c 'set -a; . /etc/student-registration.env; set +a; cd /opt/cloud/student-registration; .venv/bin/python - <<"PY"
import aws_entrypoint
from app import connection
with connection() as db:
    with db.cursor() as cursor:
        cursor.execute("SELECT id, name, email, course, photo_url FROM students ORDER BY id DESC LIMIT 5")
        for record in cursor.fetchall():
            print(record)
PY'
```

Capture **real screenshots** from these AWS pages and the working registration form/success page for the report. Never mark tests PASS unless observed.

## Security limitations

S3 has Block Public Access enabled and stores `s3://` references rather than public URLs. The database uses AWS-generated credentials in an RDS-managed Secrets Manager secret, retrieved through the EC2 instance role. App connects using the RDS CA certificate. No inbound SSH is permitted.

**The demo uses HTTP on port 80** and is not safe for entering real personal information. A real production deployment should add HTTPS, authentication, rate limiting, durable secrets rotation handling, and monitoring.

## Cleanup

Delete the CloudFormation stack after assessment to stop most recurring EC2 and RDS costs. The versioned S3 bucket has `DeletionPolicy: Retain`, so delete all object versions and the bucket separately after saving evidence if you want to stop its charges. Verify the billable resources are gone in AWS Billing.
