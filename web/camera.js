"use strict";

(() => {
  const byId = id => document.getElementById(id);
  const start = byId('cameraStart');
  const stop = byId('cameraStop');
  const sound = byId('cameraSound');
  const stage = byId('cameraStage');
  const image = byId('cameraPreview');
  const badge = byId('cameraLiveBadge');
  const status = byId('cameraStatus');
  const note = byId('cameraNote');
  const upload = byId('uploadWorkspace');
  let active = false, pending = false, timer = null, generation = 0, lastAlert = 0;
  let audio = null, muted = false;
  let lastLabel = '';

  function setActive(value) {
    active = value;
    upload.inert = value;
    upload.classList.toggle('camera-paused-upload', value);
    byId('cameraUploadNote').hidden = !value;
    window.dispatchEvent(new CustomEvent('fallsense-camera-state', {detail: {active: value}}));
  }

  function controls() {
    start.disabled = active || pending;
    stop.disabled = !active || pending;
    sound.disabled = !active;
    start.textContent = pending && !active ? 'Đang mở camera…' : 'Bật camera';
  }

  function show(state) {
    const label = state.label || 'Camera đang tắt';
    if (label !== lastLabel) { status.textContent = label; lastLabel = label; }
    stage.className = `camera-stage ${state.status || 'stopped'}`;
    badge.hidden = !state.running;
    const notes = {
      starting: 'Camera của máy đang chạy ứng dụng sẽ được mở.',
      warming_up: 'Đứng lùi để camera thấy rõ toàn thân. Cần khoảng 2 giây để bắt đầu phân tích.',
      no_person: 'Đưa người vào khung hình và giữ toàn thân trong tầm nhìn.',
      no_fall: 'Đang theo dõi chuyển động trực tiếp.',
      fall: 'Camera đã phát hiện dấu hiệu té ngã. Hãy kiểm tra ngay.',
      stopping: 'Đang giải phóng camera…',
      stopped: 'Bật camera để bắt đầu theo dõi. Hình ảnh được xử lý trên máy và không lưu thành video.',
      error: 'Kiểm tra camera rồi nhấn Bật camera để thử lại.'
    };
    note.textContent = notes[state.status] || '';
    if (state.status === 'fall' && state.alert_id > lastAlert) {
      lastAlert = state.alert_id;
      beep();
    }
  }

  function beep() {
    if (muted || !audio || audio.state !== 'running') return;
    for (const delay of [0, 0.3, 0.6]) {
      const oscillator = audio.createOscillator();
      const volume = audio.createGain();
      const time = audio.currentTime + delay;
      oscillator.type = 'sine'; oscillator.frequency.value = 950;
      volume.gain.setValueAtTime(0, time);
      volume.gain.linearRampToValueAtTime(.2, time + .02);
      volume.gain.linearRampToValueAtTime(0, time + .22);
      oscillator.connect(volume); volume.connect(audio.destination);
      oscillator.onended = () => { oscillator.disconnect(); volume.disconnect(); };
      oscillator.start(time); oscillator.stop(time + .24);
    }
  }

  async function request(url, method = 'GET') {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch(url, {method, signal: controller.signal});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Không thể kết nối camera.');
      return data;
    } finally { clearTimeout(timeout); }
  }

  async function poll(version) {
    if (version !== generation) return;
    try {
      const state = await request('/api/camera/status');
      if (version !== generation) return;
      show(state);
      if (!state.running) {
        setActive(false); image.removeAttribute('src'); image.hidden = true;
        controls(); return;
      }
      timer = setTimeout(() => poll(version), 400);
    } catch (_) {
      if (version !== generation) return;
      show({status: 'error', label: 'Mất kết nối camera. Đang thử kết nối lại…', running: true});
      timer = setTimeout(() => poll(version), 1500);
    }
  }

  start.addEventListener('click', async () => {
    if (active || pending) return;
    if (byId('resultPanel').getAttribute('aria-busy') === 'true') {
      show({status: 'error', label: 'Hãy chờ video phân tích xong rồi bật camera.'}); return;
    }
    pending = true; controls(); lastAlert = 0;
    show({status: 'starting', label: 'Đang mở camera…'});
    try {
      try {
        const Audio = window.AudioContext || window.webkitAudioContext;
        if (Audio && (!audio || audio.state === 'closed')) audio = new Audio();
        if (audio) audio.resume().catch(() => {});
      } catch (_) { }
      const state = await request('/api/camera/start', 'POST');
      setActive(state.running); show(state);
      if (state.running) {
        image.hidden = false;
        image.src = `/api/camera/stream?t=${Date.now()}`;
        generation += 1;
        clearTimeout(timer);
        poll(generation);
      }
    } catch (error) {
      setActive(false);
      show({status: 'error', label: error.message || 'Không bật được camera.'});
    } finally { pending = false; controls(); }
  });

  stop.addEventListener('click', async () => {
    if (!active || pending) return;
    pending = true; controls();
    generation += 1; clearTimeout(timer);
    try {
      const state = await request('/api/camera/stop', 'POST');
      show(state); setActive(state.running);
      image.removeAttribute('src'); image.hidden = true;
      if (state.running) poll(generation);
    } catch (_) {
      show({status: 'error', label: 'Chưa liên lạc được máy chủ để tắt camera. Đang kiểm tra lại…', running: true});
      poll(generation);
    } finally { pending = false; controls(); }
  });

  sound.addEventListener('click', () => {
    muted = !muted;
    sound.textContent = muted ? 'Bật tiếng báo' : 'Tắt tiếng báo';
    sound.setAttribute('aria-pressed', String(muted));
  });
  image.addEventListener('error', () => {
    if (active) note.textContent = 'Đang chờ hình ảnh từ camera…';
  });
  window.addEventListener('pagehide', () => {
    if (active) navigator.sendBeacon('/api/camera/stop', '');
    image.removeAttribute('src');
    if (audio) audio.close().catch(() => {});
  });
  controls();
})();
