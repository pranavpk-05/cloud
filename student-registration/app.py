import io
import os
import re
import secrets
import sqlite3
from pathlib import Path
from uuid import uuid4

from flask import Flask, redirect, render_template, request, session, url_for
from PIL import Image, UnidentifiedImageError

app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
                  MAX_CONTENT_LENGTH=6 * 1024 * 1024,
                  SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
AWS_MODE = os.environ.get('APP_MODE', 'local') == 'aws'
if AWS_MODE and not os.environ.get('SECRET_KEY'):
    raise RuntimeError('Set SECRET_KEY in AWS mode.')
COURSES = ['AWS Cloud Computing', 'Python & Flask Development', 'Data Science',
           'Full Stack Web Development', 'Cybersecurity']
DATA = Path(app.instance_path)
DATA.mkdir(exist_ok=True)


def connection():
    if AWS_MODE:
        import pymysql
        settings = dict(host=os.environ['DB_HOST'], user=os.environ['DB_USER'],
                        password=os.environ['DB_PASSWORD'], database=os.environ.get('DB_NAME', 'studentdb'),
                        connect_timeout=10, read_timeout=10, write_timeout=10)
        if os.environ.get('DB_SSL_CA'):
            settings['ssl'] = {'ca': os.environ['DB_SSL_CA'], 'check_hostname': True}
        return pymysql.connect(**settings)
    db = sqlite3.connect(DATA / 'students.db')
    db.execute('CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY, name TEXT, email TEXT, course TEXT, photo_url TEXT)')
    return db


@app.get('/')
def index():
    session.setdefault('csrf', secrets.token_urlsafe(32))
    return render_template('index.html', courses=COURSES, csrf=session['csrf'],
                           local=not AWS_MODE, values={}, error=None)


@app.post('/register')
def register():
    values = {key: request.form.get(key, '').strip() for key in ('name', 'email', 'course')}
    def invalid(message, status=400):
        return render_template('index.html', courses=COURSES, csrf=session.get('csrf', ''),
                               local=not AWS_MODE, values=values, error=message), status
    if not session.get('csrf') or not secrets.compare_digest(request.form.get('csrf', ''), session['csrf']):
        return invalid('Your session expired. Refresh the page and try again.')
    if not 2 <= len(values['name']) <= 100:
        return invalid('Enter your full name (2–100 characters).')
    if len(values['email']) > 150 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', values['email']):
        return invalid('Enter a valid email address.')
    if values['course'] not in COURSES:
        return invalid('Choose a course from the list.')
    photo = request.files.get('photo')
    if not photo or not photo.filename:
        return invalid('Please upload a student photo.')
    raw = photo.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        return invalid('Your photo must be smaller than 5 MB.')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in ('JPEG', 'PNG', 'WEBP') or image.width * image.height > 20000000:
                return invalid('Use a JPG, PNG, or WebP photo under 20 megapixels.')
            image.load()
            image = image.convert('RGB')
            image.thumbnail((1200, 1200))
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=90)
            raw = output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return invalid('This file is not a readable photo. Choose a JPG, PNG, or WebP image.')
    key = f'students/{uuid4().hex}.jpg'
    client = None
    local_path = None
    db = None
    stored = False
    try:
        if AWS_MODE:
            import boto3
            client = boto3.client('s3')
            bucket = os.environ['S3_BUCKET_NAME']
            client.put_object(Bucket=bucket, Key=key, Body=raw, ContentType='image/jpeg')
            stored = True
            # Store a stable URI; presigned viewing URLs expire and must not be persisted.
            photo_url = f's3://{bucket}/{key}'
        else:
            local_path = DATA / key
            local_path.parent.mkdir(exist_ok=True)
            local_path.write_bytes(raw)
            photo_url = key
        db = connection()
        placeholder = '%s' if AWS_MODE else '?'
        with_cursor = db.cursor()
        with_cursor.execute(f'INSERT INTO students (name, email, course, photo_url) VALUES ({", ".join([placeholder] * 4)})',
                            (values['name'], values['email'], values['course'], photo_url))
        registration_id = with_cursor.lastrowid
        db.commit()
        with_cursor.close()
    except Exception:
        app.logger.exception('Registration failed')
        if db:
            db.rollback()
        if local_path:
            local_path.unlink(missing_ok=True)
        if client and stored:
            try:
                client.delete_object(Bucket=bucket, Key=key)
            except Exception:
                app.logger.exception('Could not clean up uploaded photo')
        return invalid('Registration could not be saved. Please try again later.', 503)
    finally:
        if db:
            db.close()
    session['receipt'] = dict(values, id=registration_id)
    session['csrf'] = secrets.token_urlsafe(32)
    return redirect(url_for('success'))


@app.get('/success')
def success():
    receipt = session.get('receipt')
    if not receipt:
        return redirect(url_for('index'))
    return render_template('success.html', receipt=receipt, local=not AWS_MODE)


@app.errorhandler(413)
def too_large(error):
    return 'Upload too large. Use a photo under 5 MB. Return to the registration form.', 413


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
