"""Local smoke test; cloud integration still requires live AWS verification."""
import io
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

os.environ["APP_MODE"] = "local"
os.environ["SECRET_KEY"] = "test-only-not-for-deployment"

import app as app_module


class StudentRegistrationSmokeTests(unittest.TestCase):
    def test_student_registration_writes_record_and_photo(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(app_module, "DATA", Path(temp)):
                app_module.app.config.update(TESTING=True)
                image = Image.new("RGB", (4, 4), "blue")
                buf = io.BytesIO()
                image.save(buf, "PNG")
                buf.seek(0)
                with app_module.app.test_client() as client:
                    response = client.get("/")
                    self.assertEqual(response.status_code, 200)
                    with client.session_transaction() as session:
                        token = session["csrf"]

                    response = client.post(
                        "/register",
                        data={
                            "name": "Test Student",
                            "email": "test@example.invalid",
                            "course": "AWS Cloud Computing",
                            "csrf": token,
                            "photo": (buf, "test.png"),
                        },
                        content_type="multipart/form-data",
                        follow_redirects=False,
                    )
                    self.assertEqual(response.status_code, 302)
                    self.assertTrue(response.headers["Location"].endswith("/success"))
                    receipt = client.get("/success")
                    self.assertEqual(receipt.status_code, 200)

                db = sqlite3.connect(Path(temp) / "students.db")
                try:
                    row = db.execute(
                        "SELECT name, email, course, photo_url FROM students"
                    ).fetchone()
                finally:
                    db.close()
                self.assertIsNotNone(row)
                self.assertEqual(row[:3], ("Test Student", "test@example.invalid", "AWS Cloud Computing"))
                self.assertTrue((Path(temp) / row[3]).is_file())

    def test_upload_rejects_invalid_file(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(app_module, "DATA", Path(temp)):
                app_module.app.config.update(TESTING=True)
                with app_module.app.test_client() as client:
                    client.get("/")
                    with client.session_transaction() as session:
                        token = session["csrf"]
                    result = client.post(
                        "/register",
                        data={
                            "name": "Test Student",
                            "email": "test@example.invalid",
                            "course": "AWS Cloud Computing",
                            "csrf": token,
                            "photo": (io.BytesIO(b"not an image"), "invalid.png"),
                        },
                        content_type="multipart/form-data",
                    )
                    self.assertEqual(result.status_code, 400)


if __name__ == "__main__":
    unittest.main()
