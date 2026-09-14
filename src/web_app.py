from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import logging
from pathlib import Path
import re
import shutil
import threading
import time
from uuid import uuid4

from flask import Flask, Response, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAX_UPLOAD_MB = 250
MAX_DURATION_SECONDS = 600
RETENTION_SECONDS = 3600
ALLOWED_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}
JOB_ID = re.compile(r'^[a-f0-9]{32}$')
LOG = logging.getLogger(__name__)


class VideoJobs:

    def __init__(self, analyzer, root: Path, camera=None):
        self.analyzer = analyzer
        self.camera = camera
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.jobs = {}
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='video')
        self.stop = threading.Event()
        self.cleaner = threading.Thread(target=self._clean_loop, daemon=True)
        self.cleanup()
        self.cleaner.start()

    def _remove_directory(self, directory: Path):
        resolved = directory.resolve()
        if directory.is_symlink() or resolved.parent != self.root or not JOB_ID.fullmatch(directory.name):
            raise ValueError('Đường dẫn lưu video không hợp lệ.')
        if resolved.exists():
            shutil.rmtree(resolved)

    def _clean_loop(self):
        while not self.stop.wait(60):
            try:
                self.cleanup()
            except OSError:
                LOG.exception('Could not clean expired video files')

    def cleanup(self):
        with self.lock:
            now = time.time()
            expired = [key for key, job in self.jobs.items()
                       if job['status'] in ('completed', 'failed')
                       and now - job['_finished'] > RETENTION_SECONDS]
            for key in expired:
                self._remove_directory(self.root / key)
                del self.jobs[key]
            for path in self.root.iterdir():
                if (JOB_ID.fullmatch(path.name) and path.is_dir() and not path.is_symlink()
                        and path.name not in self.jobs and now - path.stat().st_mtime > RETENTION_SECONDS):
                    self._remove_directory(path)

    def submit(self, upload):
        with self.lock:
            active = sum(job['status'] in ('queued', 'processing') for job in self.jobs.values())
            if active >= 2 or (self.camera and self.camera.is_running()):
                return None
            terminal = [key for key, job in self.jobs.items() if job['status'] in ('completed', 'failed')]
            while len(self.jobs) >= 12 and terminal:
                key = terminal.pop(0)
                self._remove_directory(self.root / key)
                del self.jobs[key]
            key = uuid4().hex
            directory = self.root / key
            directory.mkdir()
            source = directory / ('input' + Path(upload.filename).suffix.lower())
            try:
                upload.save(source)
                if source.stat().st_size == 0:
                    raise ValueError('Video rỗng. Vui lòng chọn một video có nội dung.')
                if source.stat().st_size > MAX_UPLOAD_MB * 1024 * 1024:
                    raise ValueError(f'Video vượt quá giới hạn {MAX_UPLOAD_MB} MB.')
                self.jobs[key] = {'job_id': key, 'status': 'queued', 'progress': 0,
                                  'stage': 'Đang chờ phân tích video', '_created': time.time()}
                self.executor.submit(self._run, key, source, directory)
            except Exception:
                self.jobs.pop(key, None)
                self._remove_directory(directory)
                raise
            return key

    def _run(self, key, source, directory):
        def update(value):
            with self.lock:
                job = self.jobs[key]
                job.update({name: value[name] for name in ('stage', 'frames_analyzed') if name in value})
                job['progress'] = min(99, max(job['progress'], float(value.get('progress', 0))))

        with self.lock:
            self.jobs[key].update(status='processing', stage='Đang đọc video')
        try:
            result = self.analyzer.analyze(source, directory, progress=update)
            for event in result.get('events', []):
                name = event.pop('evidence_file', None)
                if name and Path(name).name == name and name.lower().endswith('.jpg'):
                    event['evidence_url'] = f'/api/jobs/{key}/evidence/{name}'
            outcome = dict(status='completed', progress=100, stage='Phân tích hoàn tất', result=result)
        except ValueError as exc:
            outcome = dict(status='failed', stage='Không thể phân tích video', error=str(exc))
        except Exception:
            LOG.exception('Video analysis failed for %s', key)
            outcome = dict(status='failed', stage='Phân tích gặp lỗi',
                           error='Không thể xử lý video này. Hãy thử video khác hoặc xem nhật ký máy chủ.')
        finally:
            try:
                source.unlink(missing_ok=True)
                directory.touch(exist_ok=True)
            except OSError:
                LOG.exception('Could not remove temporary source video for %s', key)
            finally:
                with self.lock:
                    self.jobs[key].update(outcome, _finished=time.time())

    def snapshot(self, key):
        with self.lock:
            job = self.jobs.get(key)
            return deepcopy({k: v for k, v in job.items() if not k.startswith('_')}) if job else None

    def delete(self, key):
        with self.lock:
            job = self.jobs.get(key)
            if job is None:
                return 404
            if '_finished' not in job:
                return 409
            self._remove_directory(self.root / key)
            del self.jobs[key]
            return 204

    def shutdown(self):
        self.stop.set()
        if self.camera:
            self.camera.stop()
        self.executor.shutdown(wait=True)
        self.cleaner.join(timeout=2)


def create_app(analyzer=None, upload_root=None, camera=None):
    app = Flask(__name__, static_folder=str(PROJECT_ROOT / 'web'), static_url_path='/static')
    app.config.update(MAX_CONTENT_LENGTH=(MAX_UPLOAD_MB * 1024 * 1024) + 1024 * 1024,
                      MAX_FORM_PARTS=4, MAX_FORM_MEMORY_SIZE=512 * 1024,
                      TRUSTED_HOSTS=['127.0.0.1', 'localhost', '[::1]'])
    app.json.ensure_ascii = False
    model_error = None
    if analyzer is None:
        try:
            from video_inference import VideoAnalyzer
            analyzer = VideoAnalyzer()
        except Exception:
            LOG.exception('Could not load local model')
            model_error = ('Không nạp được mô hình. Kiểm tra checkpoints/best.pt, '
                           'yolov8n-pose.pt và các thư viện trong môi trường Python.')
    if camera is None and analyzer is not None:
        from live_camera import CameraMonitor
        camera = CameraMonitor(analyzer)
    jobs = VideoJobs(analyzer, Path(upload_root) if upload_root else PROJECT_ROOT / 'web_uploads', camera)
    app.extensions['video_jobs'] = jobs
    app.extensions['live_camera'] = camera

    @app.before_request
    def same_origin():
        if request.method in ('POST', 'DELETE', 'PUT', 'PATCH'):
            origin = request.headers.get('Origin')
            if request.headers.get('Sec-Fetch-Site') == 'cross-site' or (
                    origin and origin.rstrip('/') != request.host_url.rstrip('/')):
                return jsonify(error='Yêu cầu phải được gửi từ giao diện trên máy này.'), 403

    @app.after_request
    def response_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.errorhandler(HTTPException)
    def http_error(exc):
        messages = {413: f'Video vượt quá giới hạn {MAX_UPLOAD_MB} MB.',
                    404: 'Không tìm thấy video hoặc kết quả đã hết hạn.',
                    400: 'Yêu cầu không hợp lệ. Vui lòng chọn lại video.'}
        return jsonify(error=messages.get(exc.code, 'Không thể thực hiện yêu cầu.')), exc.code

    @app.get('/')
    def index():
        return send_from_directory(PROJECT_ROOT / 'web', 'index.html')

    @app.get('/api/model')
    def model_info():
        return jsonify(ready=analyzer is not None, model=analyzer.metadata() if analyzer else None,
                       error=model_error, limits={'max_upload_mb': MAX_UPLOAD_MB,
                                                 'max_duration_seconds': MAX_DURATION_SECONDS})

    @app.post('/api/analyze')
    def analyze():
        if analyzer is None:
            return jsonify(error=model_error), 503
        upload = request.files.get('video')
        if upload is None or not upload.filename:
            return jsonify(error='Vui lòng chọn video để phân tích.'), 400
        if Path(upload.filename).suffix.lower() not in ALLOWED_EXTENSIONS:
            return jsonify(error='Định dạng chưa hỗ trợ. Chọn MP4, MOV, AVI, MKV, WebM hoặc M4V.'), 415
        try:
            key = jobs.submit(upload)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        if key is None:
            return jsonify(error='Mô hình đang bận. Hãy tắt camera hoặc chờ video khác xử lý xong rồi thử lại.'), 429
        return jsonify(job_id=key), 202

    @app.post('/api/camera/start')
    def camera_start():
        if camera is None:
            return jsonify(error=model_error), 503
        with jobs.lock:
            if any(job['status'] in ('queued', 'processing') for job in jobs.jobs.values()):
                return jsonify(error='Đang phân tích video. Hãy chờ hoàn tất trước khi bật camera.'), 409
            return jsonify(camera.start()), 202

    @app.post('/api/camera/stop')
    def camera_stop():
        if camera is None:
            return jsonify(running=False, status='stopped', label='Camera đang tắt')
        return jsonify(camera.stop())

    @app.get('/api/camera/status')
    def camera_status():
        if camera is None:
            return jsonify(running=False, status='error', label=model_error, error=model_error)
        return jsonify(camera.snapshot())

    @app.get('/api/camera/stream')
    def camera_stream():
        if camera is None or not camera.is_running():
            return jsonify(error='Camera chưa được bật.'), 409
        return Response(camera.stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

    @app.get('/api/jobs/<key>')
    def get_job(key):
        job = jobs.snapshot(key)
        return jsonify(job) if job else (jsonify(error='Không tìm thấy kết quả hoặc kết quả đã hết hạn.'), 404)

    @app.delete('/api/jobs/<key>')
    def delete_job(key):
        status = jobs.delete(key)
        if status == 204:
            return '', 204
        return jsonify(error='Video đang được xử lý.' if status == 409 else 'Không tìm thấy kết quả.'), status

    @app.get('/api/jobs/<key>/evidence/<name>')
    def evidence(key, name):
        with jobs.lock:
            job = jobs.snapshot(key)
            allowed = {e.get('evidence_url', '').rsplit('/', 1)[-1]
                       for e in (job or {}).get('result', {}).get('events', [])}
            if not JOB_ID.fullmatch(key) or name not in allowed or not name.endswith('.jpg'):
                return jsonify(error='Không tìm thấy ảnh minh chứng.'), 404
            try:
                content = (jobs.root / key / name).read_bytes()
            except FileNotFoundError:
                return jsonify(error='Không tìm thấy ảnh minh chứng.'), 404
        return Response(content, mimetype='image/jpeg')

    return app


def main():
    parser = argparse.ArgumentParser(description='Giao diện phát hiện té ngã từ video')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    app = create_app()
    print(f'\nMở giao diện: http://127.0.0.1:{args.port}\n')
    try:
        app.run(host='127.0.0.1', port=args.port, debug=False, threaded=True, use_reloader=False)
    finally:
        app.extensions['video_jobs'].shutdown()


if __name__ == '__main__':
    main()
