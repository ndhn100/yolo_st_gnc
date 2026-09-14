import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

import cv2
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from video_inference import VideoAnalyzer, _interpolate_pose


def visible_pose():
    pose = np.zeros((17, 3), np.float32)
    pose[:, 0] = np.linspace(40, 65, 17)
    pose[:, 1] = np.linspace(20, 85, 17)
    pose[:, 2] = 0.95
    return pose


class Boxes:
    def __init__(self, visible):
        self.xyxy = torch.tensor([[30, 10, 80, 90]], dtype=torch.float32) if visible else torch.empty((0, 4))
        self.conf = torch.tensor([0.99]) if visible else torch.empty(0)

    def __len__(self):
        return len(self.conf)


class PoseModel:
    def __init__(self, visible):
        self.frame = 0
        self.visible = visible

    def __call__(self, frame, **kwargs):
        visible = self.visible(self.frame)
        self.frame += 1
        data = torch.from_numpy(visible_pose()).unsqueeze(0)
        return [SimpleNamespace(boxes=Boxes(visible), keypoints=SimpleNamespace(data=data))]


class StubAnalyzer(VideoAnalyzer):
    def __init__(self, probabilities=None, visible=lambda index: True):
        self.device = "cpu"
        self.pose_model = PoseModel(visible)
        self.probabilities = iter(probabilities or [])
        self.windows = []

    def metadata(self):
        return {"checkpoint": "checkpoints/best.pt", "scope": "Một người chính"}

    def _predict(self, window):
        self.windows.append(window.copy())
        return next(self.probabilities, 0.1)


class VideoInferenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def video(self, fps=18, duration=4):
        path = self.directory / f"sample_{fps}_{duration}.avi"
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (128, 96))
        self.assertTrue(writer.isOpened())
        for frame_number in range(round(fps * duration)):
            frame = np.full((96, 128, 3), frame_number % 200, np.uint8)
            writer.write(frame)
        writer.release()
        return path

    def analyze(self, analyzer, fps=18, duration=4):
        return analyzer.analyze(self.video(fps, duration), self.directory / "evidence")

    def test_short_video_is_not_a_negative(self):
        result = self.analyze(StubAnalyzer(), duration=1)
        self.assertEqual(result["status"], "inconclusive")
        self.assertIsNone(result["max_probability"])
        self.assertEqual(result["stats"]["windows_analyzed"], 0)

    def test_no_person_is_not_a_negative(self):
        result = self.analyze(StubAnalyzer(visible=lambda index: False))
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["stats"]["valid_frames"], 0)
        self.assertIsNone(result["max_probability"])
        self.assertTrue(all(point["probability"] is None for point in result["timeline"]))

    def test_clear_negative_and_progress_contract(self):
        updates = []
        result = StubAnalyzer().analyze(self.video(), self.directory / "evidence", updates.append)
        self.assertEqual(result["status"], "no_fall")
        self.assertEqual(result["stats"]["windows_analyzed"], 11)
        self.assertEqual(result["stats"]["frames_analyzed"], 72)
        self.assertEqual(updates[-1]["progress"], 100)
        self.assertEqual(result["events"], [])
        json.dumps(result, allow_nan=False)

    def test_overlapping_positive_windows_merge_and_save_peak_evidence(self):
        result = self.analyze(StubAnalyzer([0.91, 0.97, 0.1]))
        self.assertEqual(result["status"], "fall")
        self.assertEqual(len(result["events"]), 1)
        event = result["events"][0]
        self.assertEqual(event["start_seconds"], 0)
        self.assertAlmostEqual(event["end_seconds"], 35 / 18, places=3)
        self.assertEqual(event["peak_probability"], 0.97)
        evidence = self.directory / "evidence" / event["evidence_file"]
        self.assertIsNotNone(cv2.imread(str(evidence)))

    def test_isolated_positive_confirms_fall(self):
        result = self.analyze(StubAnalyzer([0.1, 0.9, 0.1]))
        self.assertEqual(result["status"], "fall")
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["peak_probability"], 0.9)
        self.assertIsNotNone(cv2.imread(str(self.directory / "evidence" / result["events"][0]["evidence_file"])))

    def test_single_complete_window_at_threshold_confirms_fall(self):
        result = self.analyze(StubAnalyzer([0.85]), duration=32 / 18)
        self.assertEqual(result["status"], "fall")
        self.assertEqual(result["stats"]["windows_analyzed"], 1)
        self.assertEqual(len(result["events"]), 1)

    def test_single_complete_window_below_threshold_is_negative(self):
        result = self.analyze(StubAnalyzer([0.8499]), duration=32 / 18)
        self.assertEqual(result["status"], "no_fall")
        self.assertEqual(result["events"], [])

    def test_30fps_does_not_speed_up_the_motion_windows(self):
        at_18 = self.analyze(StubAnalyzer(), fps=18)
        at_30 = self.analyze(StubAnalyzer(), fps=30)
        self.assertEqual(at_18["stats"]["frames_analyzed"], at_30["stats"]["frames_analyzed"])
        self.assertEqual(at_18["timeline"], at_30["timeline"])

    def test_low_fps_is_resampled_on_the_same_time_grid(self):
        result = self.analyze(StubAnalyzer(), fps=9)
        self.assertEqual(result["status"], "no_fall")
        self.assertEqual(result["stats"]["frames_analyzed"], 71)
        self.assertEqual(result["stats"]["sampled_fps"], 18)
        self.assertAlmostEqual(result["timeline"][0]["time_seconds"], 31 / 18, places=3)
        self.assertTrue(any("FPS thấp" in warning for warning in result["warnings"]))

    def test_long_missing_interval_prevents_negative_conclusion(self):
        result = self.analyze(StubAnalyzer(visible=lambda index: not 37 <= index < 56), duration=6)
        self.assertEqual(result["status"], "inconclusive")
        self.assertGreater(result["stats"]["track_resets"], 0)
        self.assertTrue(any(point["probability"] is None for point in result["timeline"]))

    def test_interpolation_does_not_invent_visible_joints(self):
        left, right = visible_pose(), visible_pose()
        right[0, 2] = 0.0
        right[:, :2] += 10
        interpolated = _interpolate_pose(left, right, 0.5)
        self.assertEqual(interpolated[0, 2], 0)
        np.testing.assert_allclose(interpolated[1:, :2], left[1:, :2] + 5)

    def test_corrupt_video_raises_readable_error(self):
        video = self.directory / "corrupt.mp4"
        video.write_bytes(b"not a video")
        with self.assertRaisesRegex(ValueError, "Không đọc được video"):
            StubAnalyzer().analyze(video, self.directory / "evidence")


if __name__ == "__main__":
    unittest.main()
