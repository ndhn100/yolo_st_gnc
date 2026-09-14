import io
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from web_app import create_app


class FakeAnalyzer:

    def __init__(self, *, fail=False, block=False):
        self.fail = fail
        self.block = block
        self.started = threading.Event()
        self.release = threading.Event()
        self.source = None
        self.output_dir = None
        self.source_bytes = None

    def metadata(self):
        return {
            "checkpoint": "checkpoints/best.pt",
            "device": "cpu",
            "threshold": 0.5,
        }

    def analyze(self, source, output_dir, progress):
        self.source = Path(source)
        self.output_dir = Path(output_dir)
        self.source_bytes = self.source.read_bytes()
        self.started.set()
        if self.block:
            if not self.release.wait(5):
                raise RuntimeError("Test analyzer was not released")
        if self.fail:
            raise ValueError("Video thử nghiệm không thể giải mã")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "frame.jpg").write_bytes(b"test-jpeg-evidence")
        (self.output_dir / "unlisted.jpg").write_bytes(b"private-intermediate")
        return {
            "verdict": "fall",
            "fall_detected": True,
            "max_fall_probability": 0.95,
            "events": [{"evidence_file": "frame.jpg"}],
        }


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.upload_root = Path(self.temp_dir.name)
        self.analyzer = FakeAnalyzer()
        self.app = create_app(analyzer=self.analyzer, upload_root=self.upload_root)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.analyzer.release.set()
        self.app.extensions["video_jobs"].shutdown()
        self.temp_dir.cleanup()

    def upload(self, payload=b"fake-video-content", filename="video.mp4", **kwargs):
        response = self.client.post(
            "/api/analyze",
            data={"video": (io.BytesIO(payload), filename)},
            content_type="multipart/form-data",
            **kwargs,
        )
        response.request.environ["wsgi.input"].close()
        return response

    def wait_for_job(self, job_id):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            response = self.client.get(f"/api/jobs/{job_id}")
            self.assertEqual(response.status_code, 200)
            body = response.get_json()
            if body["status"] in {"completed", "failed"}:
                return body
            self.assertIn(body["status"], {"queued", "processing"})
            time.sleep(0.01)
        self.fail("The test job did not finish within five seconds")

    def test_model_metadata_is_available(self):
        response = self.client.get("/api/model")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["ready"])
        self.assertIsInstance(body["model"], dict)
        self.assertIsInstance(body["limits"], dict)

    def test_success_evidence_cleanup_and_deletion(self):
        response = self.upload(filename="../../unexpected-name.mp4")
        self.assertEqual(response.status_code, 202)
        job_id = response.get_json()["job_id"]
        body = self.wait_for_job(job_id)
        self.assertEqual(body["status"], "completed")
        self.assertTrue(body["result"]["fall_detected"])
        self.assertEqual(
            body["result"]["events"][0]["evidence_url"],
            f"/api/jobs/{job_id}/evidence/frame.jpg",
        )
        self.assertEqual(self.analyzer.source_bytes, b"fake-video-content")
        self.assertTrue(self.analyzer.source.is_relative_to(self.upload_root))
        self.assertNotEqual(self.analyzer.source.name, "unexpected-name.mp4")
        self.assertFalse(self.analyzer.source.exists())

        evidence = self.client.get(f"/api/jobs/{job_id}/evidence/frame.jpg")
        self.assertEqual(evidence.status_code, 200)
        self.assertEqual(evidence.data, b"test-jpeg-evidence")
        evidence.close()
        self.assertEqual(
            self.client.get(f"/api/jobs/{job_id}/evidence/missing.jpg").status_code,
            404,
        )
        self.assertEqual(
            self.client.get(f"/api/jobs/{job_id}/evidence/unlisted.jpg").status_code,
            404,
        )
        self.assertEqual(self.client.delete(f"/api/jobs/{job_id}").status_code, 204)
        self.assertEqual(self.client.get(f"/api/jobs/{job_id}").status_code, 404)
        self.assertFalse((self.analyzer.output_dir / "frame.jpg").exists())

    def test_multimegabyte_file_upload_is_accepted(self):
        payload = b"video-data" * ((2 * 1024 * 1024) // 10)
        response = self.upload(payload=payload)
        self.assertEqual(response.status_code, 202)
        job_id = response.get_json()["job_id"]
        self.assertEqual(self.wait_for_job(job_id)["status"], "completed")
        self.assertEqual(self.analyzer.source_bytes, payload)
        self.assertFalse(self.analyzer.source.exists())

    def test_evidence_response_does_not_lock_files_during_deletion(self):
        response = self.upload()
        self.assertEqual(response.status_code, 202)
        job_id = response.get_json()["job_id"]
        self.assertEqual(self.wait_for_job(job_id)["status"], "completed")
        evidence = self.client.get(
            f"/api/jobs/{job_id}/evidence/frame.jpg", buffered=False
        )
        try:
            self.assertEqual(evidence.status_code, 200)
            self.assertEqual(self.client.delete(f"/api/jobs/{job_id}").status_code, 204)
            self.assertFalse((self.analyzer.output_dir / "frame.jpg").exists())
            self.assertEqual(evidence.data, b"test-jpeg-evidence")
        finally:
            evidence.close()

    def test_missing_and_empty_uploads_are_rejected(self):
        self.assertEqual(self.client.post("/api/analyze").status_code, 400)
        self.assertEqual(self.upload(payload=b"").status_code, 400)
        self.assertEqual(self.upload(filename="").status_code, 400)
        self.assertFalse(self.analyzer.started.is_set())

    def test_unsupported_file_type_is_rejected(self):
        self.assertEqual(self.upload(filename="script.exe").status_code, 415)
        self.assertFalse(self.analyzer.started.is_set())

    def test_oversized_upload_is_rejected(self):
        self.app.config["MAX_CONTENT_LENGTH"] = 1024
        response = self.upload(payload=b"x" * 2048)
        self.assertEqual(response.status_code, 413)
        self.assertFalse(self.analyzer.started.is_set())

    def test_failed_job_reports_error_and_removes_source(self):
        self.analyzer.fail = True
        response = self.upload()
        self.assertEqual(response.status_code, 202)
        job_id = response.get_json()["job_id"]
        body = self.wait_for_job(job_id)
        self.assertEqual(body["status"], "failed")
        self.assertTrue(body["error"])
        self.assertFalse(self.analyzer.source.exists())
        self.assertEqual(self.client.delete(f"/api/jobs/{job_id}").status_code, 204)

    def test_running_job_cannot_be_deleted(self):
        self.analyzer.block = True
        response = self.upload()
        self.assertEqual(response.status_code, 202)
        job_id = response.get_json()["job_id"]
        self.assertTrue(self.analyzer.started.wait(5))
        self.assertEqual(self.client.delete(f"/api/jobs/{job_id}").status_code, 409)
        self.analyzer.release.set()
        self.assertEqual(self.wait_for_job(job_id)["status"], "completed")

    def test_unknown_job_and_evidence_return_not_found(self):
        job_id = "00000000000000000000000000000000"
        self.assertEqual(self.client.get(f"/api/jobs/{job_id}").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/jobs/{job_id}").status_code, 404)
        self.assertEqual(
            self.client.get(f"/api/jobs/{job_id}/evidence/frame.jpg").status_code,
            404,
        )

    def test_cross_origin_upload_is_rejected(self):
        response = self.upload(headers={"Origin": "https://hostile.example"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.analyzer.started.is_set())


if __name__ == "__main__":
    unittest.main()
