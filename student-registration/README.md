# Student registration

Built from the supplied ICT Academy AWS Flask project guide. Includes name, email, course, photo upload, validation, and a printable registration receipt.

## Run locally (Windows)

```powershell
cd C:\Users\prana\OneDrive\project\student-registration
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. Local mode saves records to `instance/students.db` and photos to `instance/students/`. No AWS account is needed for local use. Stop with Ctrl+C. The default generated session secret changes on restart; set SECRET_KEY for stable sessions.

## AWS mode

Deploy this Python project to EC2, following the PDF's VPC, private RDS, security-group, and instance-role setup. Set the environment variables listed in `.env.example` (it is not loaded automatically). Set `APP_MODE=aws`, a strong `SECRET_KEY`, and the RDS/S3 values. Create the MySQL table using `schema.sql` from inside the VPC. Install requirements in a virtual environment.

Use a private S3 bucket with Block Public Access enabled. boto3 uses the EC2 instance role; do not place AWS access keys in the source. The role needs s3:PutObject and s3:GetObject on your bucket's students/* prefix, plus s3:DeleteObject to clean up an upload when the database insert fails. The database stores a stable s3:// URI; generate a short-lived presigned GetObject URL when building a future photo-viewing page. There is intentionally no public photo or student-list endpoint.

Run on Linux with `gunicorn --workers 3 --bind 127.0.0.1:8000 app:app`, using systemd and Nginx or a load balancer for HTTPS. Keep the secret stable across workers. Set SESSION_COOKIE_SECURE=True in app configuration once served over HTTPS. Optionally set DB_SSL_CA to the downloaded RDS CA bundle for verified database TLS. Configure infrastructure in your AWS account before running AWS mode; this project does not provision it.

The course list is editable in app.py. Branding is illustrative. Fonts use Google Fonts, with local sans-serif fallbacks. The form limits photos to 5 MB, verifies image content, re-encodes images as JPEG, and uses random object names. Browser and server validation are both included.
