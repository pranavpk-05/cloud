"""WSGI entrypoint for AWS; load RDS master credentials from Secrets Manager.

EC2's instance profile supplies temporary AWS credentials automatically. Never
put the RDS password or AWS keys in GitHub, EC2 user data, or systemd units.
"""

import json
import os

if os.environ.get("APP_MODE") == "aws":
    arn = os.environ.get("DB_SECRET_ARN")
    if arn:
        import boto3

        secret = boto3.client("secretsmanager").get_secret_value(SecretId=arn)
        credentials = json.loads(secret["SecretString"])
        os.environ["DB_USER"] = credentials["username"]
        os.environ["DB_PASSWORD"] = credentials["password"]

from app import app  # noqa: E402
