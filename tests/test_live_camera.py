import io
from pathlib import Path
import tempfile
import time
import unittest

import numpy as np

from test_video_inference import StubAnalyzer
from live_camera import CameraMonitor, LiveFallDetector
from web_app import create_app


class LiveDetectorTests(unittest.TestCase):
    def setUp(self):
        self.frame = np.zeros((96, 128, 3), np.uint8)

    def feed(self, detector, count, start=0):
        for idx in range(start, start + count):
            state = detector.process(self.frame, idx / 18)
        return state

    def test_warmup_then_clear_negative(self):
        detector = LiveFallDetector(StubAnalyzer())
        self.assertEqual(self.feed(detector, 1)['status'], 'warming_up')
        result = self.feed(detector, 35, start=1)
        self.assertEqual(result['status'], 'no_fall')
        self.assertEqual(result['label'], 'Không phát hiện té ngã')

    def test_one_positive_window_triggers_alert_then_recovers(self):
        detector = LiveFallDetector(StubAnalyzer([.94, .1]))
        result = self.feed(detector, 32)
        self.assertEqual(result['status'], 'fall')
        self.assertEqual(result['alert_id'], 1)
        self.assertEqual(result['probability'], .94)
        self.assertEqual(self.feed(detector, 12, start=32)['status'], 'fall')
        self.assertEqual(self.feed(detector, 80, start=44)['status'], 'no_fall')

    def test_no_person_does_not_claim_negative(self):
        detector = LiveFallDetector(StubAnalyzer(visible=lambda _: False))
        result = self.feed(detector, 40)
        self.assertEqual(result['status'], 'no_person')
        self.assertIsNone(result['probability'])

    def test_person_leaving_clears_stale_negative(self):
        detector = LiveFallDetector(StubAnalyzer(visible=lambda idx: idx < 36))
        self.assertEqual(self.feed(detector, 36)['status'], 'no_fall')
        self.assertEqual(self.feed(detector, 1, start=36)['status'], 'no_person')

    def test_capture_gap_resets_window(self):
        detector = LiveFallDetector(StubAnalyzer())
        self.feed(detector, 36)
        result = detector.process(self.frame, 5)
        self.assertEqual(result['status'], 'warming_up')
        self.assertEqual(result['buffer_frames'], 1)


class FakeCapture:
    def __init__(self, opened=True):
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        time.sleep(.01)
        return True, np.zeros((96, 128, 3), np.uint8)

    def release(self):
        self.released = True


class CameraAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.analyzer = StubAnalyzer()
        self.capture = FakeCapture()
        self.camera = CameraMonitor(self.analyzer, capture_factory=lambda: self.capture)
        self.app = create_app(self.analyzer, Path(self.temp.name), camera=self.camera)
        self.client = self.app.test_client()

    def tearDown(self):
        self.app.extensions['video_jobs'].shutdown()
        self.temp.cleanup()

    def test_start_stream_stop_releases_camera(self):
        started = self.client.post('/api/camera/start')
        self.assertEqual(started.status_code, 202)
        self.assertTrue(started.json['running'])
        stream = self.client.get('/api/camera/stream', buffered=False)
        frame = next(iter(stream.response))
        self.assertIn(b'Content-Type: image/jpeg', frame)
        stream.close()
        self.assertTrue(self.client.get('/api/camera/status').json['running'])
        self.assertFalse(self.client.post('/api/camera/stop').json['running'])
        self.assertTrue(self.capture.released)
        self.assertIsNone(self.camera.jpeg)
        self.assertEqual(self.client.get('/api/camera/stream').status_code, 409)

    def test_upload_is_blocked_while_camera_uses_model(self):
        self.client.post('/api/camera/start')
        response = self.client.post('/api/analyze', data={'video': (io.BytesIO(b'video'), 'clip.mp4')})
        self.assertEqual(response.status_code, 429)

    def test_camera_is_blocked_while_video_is_queued(self):
        jobs = self.app.extensions['video_jobs']
        with jobs.lock:
            jobs.jobs['queued-test'] = {'status': 'queued'}
        self.assertEqual(self.client.post('/api/camera/start').status_code, 409)
        self.assertFalse(self.camera.is_running())

    def test_camera_permission_or_device_error_is_visible(self):
        self.capture.opened = False
        self.client.post('/api/camera/start')
        self.camera.thread.join(timeout=1)
        result = self.client.get('/api/camera/status').json
        self.assertEqual(result['status'], 'error')
        self.assertIn('Không mở được camera', result['label'])
        self.assertTrue(self.capture.released)

    def test_foreign_origin_cannot_turn_on_camera(self):
        response = self.client.post('/api/camera/start', headers={'Origin': 'https://foreign.invalid'})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.camera.is_running())

    def test_abandoned_view_releases_device(self):
        self.camera.start()
        self.camera.last_seen = time.monotonic() - 20
        self.camera.thread.join(timeout=1)
        self.assertFalse(self.camera.is_running())
        self.assertTrue(self.capture.released)


if __name__ == '__main__':
    unittest.main()
