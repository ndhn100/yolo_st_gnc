"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const elements = Object.fromEntries([
    "systemStatus", "systemStatusText", "modelCheckpoint", "modelF1", "modelMessage", "modelRetry", "fileInput", "dropZone", "uploadLimits", "previewWrap", "videoPreview", "previewWarning", "fileName", "fileMeta", "resetButton", "uploadError", "analyzeButton", "analyzeButtonText", "resultPanel", "resultBadge", "emptyResult", "processingResult", "processingStage", "progressValue", "progressTrack", "progressFill", "completedResult", "verdict", "verdictIcon", "verdictLabel", "verdictSummary", "maxProbability", "thresholdValue", "timelineChart", "chartCaption", "eventCount", "eventList", "analysisStats", "resultWarnings", "failedResult", "analysisError", "retryButton", "screenReaderStatus",
  ].map((id) => [id, $(id)]));
  const allowedExtensions = new Set(["mp4", "mov", "avi", "mkv", "webm", "m4v"]);
  for (const id of ["confirmedEvents", "decisionExplanation", "peakReviewButton"]) elements[id] = $(id);
  const resultViews = ["emptyResult", "processingResult", "completedResult", "failedResult"];
  const numberFormat = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 });
  let selectedFile = null;
  let previewUrl = null;
  let jobId = null;
  let modelReady = false;
  let busy = false;
  let cameraActive = false;
  let modelLoading = false;
  let maxUploadMb = 250;
  let maxDurationSeconds = 600;
  let pollTimer = null;
  let pollFailures = 0;
  let pollGeneration = 0;
  let lastStage = "";

  const isNumber = (value) => typeof value === "number" && Number.isFinite(value);
  const percent = (value) => isNumber(value) ? `${numberFormat.format(value * 100)}%` : "—";
  const modelScore = (value) => isNumber(value) ? `${numberFormat.format(value * 100)} / 100` : "Chưa có điểm";
  const timeLabel = (seconds) => {
    if (!isNumber(seconds)) return "—";
    const total = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    return `${hours ? `${hours}:` : ""}${hours ? String(minutes).padStart(2, "0") : String(minutes).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
  };
  const setText = (name, value) => { elements[name].textContent = value; };
  const announce = (message) => setText("screenReaderStatus", message);
  const showUploadError = (message) => {
    setText("uploadError", message || "");
    elements.uploadError.hidden = !message;
  };

  function updateControls() {
    elements.analyzeButton.disabled = busy || cameraActive || !selectedFile || !modelReady;
    elements.resetButton.disabled = busy || cameraActive;
    elements.fileInput.disabled = busy || cameraActive;
    elements.dropZone.setAttribute("aria-disabled", String(busy || cameraActive));
    elements.dropZone.tabIndex = busy || cameraActive ? -1 : 0;
    elements.retryButton.disabled = busy || cameraActive || !selectedFile || !modelReady;
    elements.resultPanel.setAttribute("aria-busy", String(busy));
    setText("analyzeButtonText", busy ? "Đang xử lý…" : "Phân tích video");
  }

  function showView(view) {
    for (const name of resultViews) elements[name].hidden = name !== view;
    const badge = {
      emptyResult: ["CHƯA PHÂN TÍCH", ""],
      processingResult: ["ĐANG XỬ LÝ", "processing"],
      completedResult: ["ĐÃ HOÀN TẤT", "completed"],
      failedResult: ["CẦN KIỂM TRA", "failed"],
    }[view];
    setText("resultBadge", badge[0]);
    elements.resultBadge.className = `result-badge ${badge[1]}`.trim();
  }

  async function apiRequest(url, options = {}, timeout = 20000) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(url, { ...options, signal: controller.signal });
      let data = null;
      const body = await response.text();
      if (body) {
        try { data = JSON.parse(body); } catch (_) {
          throw new Error(response.ok ? "Máy chủ trả về dữ liệu không hợp lệ." : `Máy chủ chưa thể xử lý yêu cầu (HTTP ${response.status}).`);
        }
      }
      if (!response.ok) {
        const detail = data?.error || data?.detail || data?.message;
        const message = typeof detail === "string" ? detail : `Yêu cầu chưa thành công (HTTP ${response.status}).`;
        const error = new Error(message);
        error.status = response.status;
        throw error;
      }
      return data;
    } catch (error) {
      if (error.name === "AbortError") throw new Error("Kết nối quá thời gian chờ. Kiểm tra máy chủ và thử lại.");
      if (error instanceof TypeError) throw new Error("Không kết nối được máy chủ. Hãy kiểm tra ứng dụng đang chạy và thử lại.");
      throw error;
    } finally {
      window.clearTimeout(timeoutId);
    }
  }

  async function loadModel() {
    if (modelLoading) return;
    modelLoading = true;
    elements.modelRetry.disabled = true;
    setText("systemStatusText", "Đang kết nối mô hình");
    elements.systemStatus.className = "system-status";
    try {
      const data = await apiRequest("/api/model");
      if (!data || typeof data.ready !== "boolean") throw new Error("Không đọc được thông tin mô hình từ máy chủ.");
      modelReady = data.ready;
      const model = data.model || {};
      const checkpoint = typeof model.checkpoint === "string" ? model.checkpoint : "Chưa có thông tin";
      setText("modelCheckpoint", checkpoint.split(/[\\/]/).pop());
      elements.modelCheckpoint.title = checkpoint;
      setText("modelF1", isNumber(model.val_f1) ? percent(model.val_f1) : "Chưa có số liệu");
      if (isNumber(data.limits?.max_upload_mb) && data.limits.max_upload_mb > 0) maxUploadMb = data.limits.max_upload_mb;
      if (isNumber(data.limits?.max_duration_seconds) && data.limits.max_duration_seconds > 0) maxDurationSeconds = data.limits.max_duration_seconds;
      setText("uploadLimits", `Tối đa ${numberFormat.format(maxUploadMb)} MB · ${numberFormat.format(maxDurationSeconds / 60)} phút / video`);
      elements.systemStatus.className = `system-status ${modelReady ? "ready" : "unavailable"}`;
      setText("systemStatusText", modelReady ? "Mô hình sẵn sàng" : "Mô hình chưa sẵn sàng");
      setText("modelMessage", modelReady ? "" : (data.error || "Mô hình chưa sẵn sàng. Kiểm tra checkpoint trên máy chủ."));
      elements.modelMessage.hidden = modelReady;
      elements.modelRetry.hidden = modelReady;
    } catch (error) {
      modelReady = false;
      elements.systemStatus.className = "system-status unavailable";
      setText("systemStatusText", "Chưa kết nối máy chủ");
      setText("modelCheckpoint", "Chưa tải được");
      setText("modelF1", "—");
      setText("modelMessage", error.message);
      elements.modelMessage.hidden = false;
      elements.modelRetry.hidden = false;
    } finally {
      modelLoading = false;
      elements.modelRetry.disabled = false;
      updateControls();
    }
  }

  async function removePreviousJob() {
    if (!jobId) return;
    try {
      await apiRequest(`/api/jobs/${encodeURIComponent(jobId)}`, { method: "DELETE" });
    } catch (error) {
      if (error.status !== 404) throw new Error(`Chưa xóa được video đã xử lý: ${error.message}`);
    }
    jobId = null;
  }

  function clearPreview() {
    elements.videoPreview.pause();
    elements.videoPreview.removeAttribute("src");
    elements.videoPreview.load();
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
  }

  async function selectFile(file) {
    if (!file || busy || cameraActive) return;
    showUploadError("");
    const extension = file.name.split(".").pop().toLowerCase();
    if (!allowedExtensions.has(extension)) {
      showUploadError("Vui lòng chọn video MP4, MOV, AVI, MKV, WEBM hoặc M4V.");
      elements.fileInput.value = "";
      return;
    }
    if (file.size === 0) {
      showUploadError("Video đang trống. Vui lòng chọn một tệp khác.");
      elements.fileInput.value = "";
      return;
    }
    if (file.size > maxUploadMb * 1024 * 1024) {
      showUploadError(`Video vượt quá giới hạn ${numberFormat.format(maxUploadMb)} MB. Vui lòng chọn một video nhỏ hơn.`);
      elements.fileInput.value = "";
      return;
    }
    busy = true;
    updateControls();
    try {
      await removePreviousJob();
      pollGeneration += 1;
      window.clearTimeout(pollTimer);
      clearPreview();
      selectedFile = file;
      previewUrl = URL.createObjectURL(file);
      elements.videoPreview.src = previewUrl;
      elements.previewWarning.hidden = true;
      elements.previewWrap.hidden = false;
      elements.dropZone.hidden = true;
      setText("fileName", file.name);
      elements.fileName.title = file.name;
      updateFileMeta();
      showView("emptyResult");
      announce(`Đã chọn video ${file.name}. Bạn có thể bắt đầu phân tích.`);
    } catch (error) {
      showUploadError(error.message);
    } finally {
      elements.fileInput.value = "";
      busy = false;
      updateControls();
    }
  }

  function updateFileMeta() {
    if (!selectedFile) return;
    const parts = [`${numberFormat.format(selectedFile.size / 1024 / 1024)} MB`];
    if (Number.isFinite(elements.videoPreview.duration)) parts.push(timeLabel(elements.videoPreview.duration));
    parts.push(selectedFile.name.split(".").pop().toUpperCase());
    setText("fileMeta", parts.join("  ·  "));
  }

  async function reset() {
    if (busy) return;
    busy = true;
    updateControls();
    showUploadError("");
    try {
      await removePreviousJob();
      pollGeneration += 1;
      window.clearTimeout(pollTimer);
      clearPreview();
      selectedFile = null;
      elements.fileInput.value = "";
      elements.dropZone.hidden = false;
      elements.previewWrap.hidden = true;
      elements.previewWarning.hidden = true;
      showView("emptyResult");
      announce("Đã xóa video và kết quả phân tích. Bạn có thể chọn video khác.");
    } catch (error) {
      showUploadError(error.message);
    } finally {
      busy = false;
      updateControls();
      if (!selectedFile) elements.dropZone.focus();
    }
  }

  function updateProgress(progress, stage, indeterminate = false) {
    const value = isNumber(progress) ? Math.min(100, Math.max(0, progress)) : 0;
    setText("progressValue", indeterminate ? "Đang tải…" : `${Math.round(value)}%`);
    elements.progressFill.style.width = `${value}%`;
    elements.progressTrack.classList.toggle("indeterminate", indeterminate);
    if (indeterminate) elements.progressTrack.removeAttribute("aria-valuenow");
    else elements.progressTrack.setAttribute("aria-valuenow", String(Math.round(value)));
    if (stage !== lastStage) {
      setText("processingStage", stage);
      lastStage = stage;
    }
  }

  async function startAnalysis() {
    if (busy || cameraActive || !selectedFile || !modelReady) return;
    if (selectedFile.size > maxUploadMb * 1024 * 1024) {
      showUploadError(`Video vượt quá giới hạn ${numberFormat.format(maxUploadMb)} MB.`);
      return;
    }
    busy = true;
    pollFailures = 0;
    pollGeneration += 1;
    const generation = pollGeneration;
    showUploadError("");
    updateControls();
    showView("processingResult");
    updateProgress(0, "Đang tải video lên máy chủ cục bộ…", true);
    try {
      await removePreviousJob();
      const form = new FormData();
      form.append("video", selectedFile, selectedFile.name);
      const data = await apiRequest("/api/analyze", { method: "POST", body: form }, 180000);
      if (!data || !data.job_id) throw new Error("Máy chủ chưa cung cấp mã phân tích. Vui lòng thử lại.");
      jobId = String(data.job_id);
      updateProgress(0, "Video đã tải lên. Đang chờ phân tích…");
      await pollJob(generation);
    } catch (error) {
      failAnalysis(error.message);
    }
  }

  async function pollJob(generation) {
    if (!jobId || generation !== pollGeneration) return;
    try {
      const data = await apiRequest(`/api/jobs/${encodeURIComponent(jobId)}`);
      if (generation !== pollGeneration) return;
      if (!data || !["queued", "processing", "completed", "failed"].includes(data.status)) throw new Error("Trạng thái phân tích trả về không hợp lệ.");
      pollFailures = 0;
      if (data.status === "completed") {
        if (!data.result) {
          failAnalysis("Quá trình đã kết thúc nhưng chưa nhận được kết quả.");
          return;
        }
        try { renderResult(data.result); } catch (error) {
          failAnalysis(error.message);
          return;
        }
        busy = false;
        updateControls();
        return;
      }
      if (data.status === "failed") {
        failAnalysis(data.error || "Không thể phân tích video này. Vui lòng kiểm tra video và thử lại.");
        return;
      }
      updateProgress(data.progress, data.stage || (data.status === "queued" ? "Video đang chờ phân tích…" : "Đang phân tích chuyển động…"));
      pollTimer = window.setTimeout(() => pollJob(generation), 1000);
    } catch (error) {
      if (generation !== pollGeneration) return;
      if (error.status === 404 || error.status === 410) {
        jobId = null;
        failAnalysis("Không tìm thấy phiên phân tích trên máy chủ. Vui lòng phân tích lại video.");
        return;
      }
      pollFailures += 1;
      updateProgress(Number(elements.progressTrack.getAttribute("aria-valuenow")) || 0, `Kết nối bị gián đoạn. Đang kết nối lại để nhận kết quả… (${pollFailures})`);
      pollTimer = window.setTimeout(() => pollJob(generation), Math.min(15000, 1500 * (2 ** Math.min(pollFailures - 1, 4))));
    }
  }

  function failAnalysis(message) {
    busy = false;
    window.clearTimeout(pollTimer);
    setText("analysisError", message);
    showView("failedResult");
    updateControls();
    announce(`Chưa thể hoàn tất phân tích. ${message}`);
  }

  function makeSvgElement(tag, attributes = {}) {
    const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
    return element;
  }

  function icon(symbol, className = "icon") {
    const svg = makeSvgElement("svg", { class: className, "aria-hidden": "true" });
    svg.append(makeSvgElement("use", { href: `#icon-${symbol}` }));
    return svg;
  }

  function renderTimeline(timeline, threshold, duration) {
    elements.timelineChart.replaceChildren();
    const points = (Array.isArray(timeline) ? timeline : []).filter((point) => point && isNumber(point.time_seconds)).sort((a, b) => a.time_seconds - b.time_seconds);
    const validPoints = points.filter((point) => isNumber(point.probability));
    if (!validPoints.length) {
      const text = document.createElement("p");
      text.className = "chart-empty";
      text.textContent = "Chưa đủ dữ liệu để hiển thị diễn biến.";
      elements.timelineChart.append(text);
      elements.chartCaption.hidden = true;
      return;
    }
    elements.chartCaption.hidden = false;
    const width = 420;
    const height = 126;
    const plot = { left: 28, top: 8, width: 379, height: 86 };
    const endTime = Math.max(1, isNumber(duration) ? duration : 0, ...points.map((point) => point.time_seconds));
    const x = (seconds) => plot.left + Math.max(0, seconds) / endTime * plot.width;
    const y = (probability) => plot.top + (1 - Math.min(1, Math.max(0, probability))) * plot.height;
    const svg = makeSvgElement("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": "Biểu đồ điểm mô hình từ 0 đến 100 theo thời gian video, không phải xác suất té ngã của cả video" });
    for (const level of [0, 0.5, 1]) {
      svg.append(makeSvgElement("line", { x1: plot.left, x2: plot.left + plot.width, y1: y(level), y2: y(level), stroke: "#ecf0f2", "stroke-width": 1 }));
      const label = makeSvgElement("text", { x: plot.left - 5, y: y(level) + 4, "text-anchor": "end", fill: "#526777", "font-size": 12, "font-family": "Segoe UI, sans-serif" });
      label.textContent = String(Math.round(level * 100));
      svg.append(label);
    }
    if (isNumber(threshold)) svg.append(makeSvgElement("line", { x1: plot.left, x2: plot.left + plot.width, y1: y(threshold), y2: y(threshold), stroke: "#cda38b", "stroke-dasharray": "4 4", "stroke-width": 1 }));
    let segment = [];
    const drawSegment = () => {
      if (!segment.length) return;
      const coordinates = segment.map((point) => `${x(point.time_seconds).toFixed(2)},${y(point.probability).toFixed(2)}`);
      if (segment.length > 1) {
        svg.append(makeSvgElement("polygon", { points: `${x(segment[0].time_seconds)},${y(0)} ${coordinates.join(" ")} ${x(segment[segment.length - 1].time_seconds)},${y(0)}`, fill: "#087f7d0a" }));
        svg.append(makeSvgElement("polyline", { points: coordinates.join(" "), fill: "none", stroke: "#168c85", "stroke-width": 1.8, "stroke-linejoin": "round", "stroke-linecap": "round" }));
      } else svg.append(makeSvgElement("circle", { cx: x(segment[0].time_seconds), cy: y(segment[0].probability), r: 2.5, fill: "#168c85" }));
      segment = [];
    };
    for (const point of points) {
      if (isNumber(point.probability)) segment.push(point);
      else drawSegment();
    }
    drawSegment();
    for (const ratio of [0, 0.25, 0.5, 0.75, 1]) {
      const label = makeSvgElement("text", { x: x(endTime * ratio), y: plot.top + plot.height + 19, "text-anchor": ratio === 0 ? "start" : ratio === 1 ? "end" : "middle", fill: "#526777", "font-size": 12, "font-family": "Segoe UI, sans-serif" });
      label.textContent = timeLabel(endTime * ratio);
      svg.append(label);
    }
    elements.timelineChart.append(svg);
  }

  function safeEvidenceUrl(value) {
    if (typeof value !== "string") return null;
    try {
      const url = new URL(value, window.location.origin);
      return url.origin === window.location.origin && ["http:", "https:"].includes(url.protocol) ? url.href : null;
    } catch (_) { return null; }
  }

  function renderEvents(events, resultStatus) {
    elements.eventList.replaceChildren();
    const validEvents = (Array.isArray(events) ? events : []).filter((event) => event && isNumber(event.start_seconds) && isNumber(event.end_seconds));
    setText("eventCount", String(validEvents.length));
    if (!validEvents.length) {
      const empty = document.createElement("p");
      empty.className = "events-empty";
      empty.textContent = resultStatus === "inconclusive" ? "Chưa có sự kiện nào đủ điều kiện xác nhận té ngã. Xem phần điểm mô hình để kiểm tra đoạn có điểm cao nhất." : "Không có sự kiện té ngã nào được mô hình xác nhận.";
      elements.eventList.append(empty);
      return;
    }
    for (const event of validEvents) {
      const button = document.createElement("button");
      button.className = "event-button";
      button.type = "button";
      button.setAttribute("aria-label", `Xem thời điểm từ ${timeLabel(event.start_seconds)} đến ${timeLabel(event.end_seconds)}, điểm mô hình ${modelScore(event.peak_probability)}`);
      const evidenceUrl = safeEvidenceUrl(event.evidence_url);
      const placeholder = () => {
        const span = document.createElement("span");
        span.className = "event-thumbnail event-placeholder";
        span.append(icon("play"));
        return span;
      };
      if (evidenceUrl) {
        const image = document.createElement("img");
        image.className = "event-thumbnail";
        image.alt = `Khung hình tại ${timeLabel(event.start_seconds)}`;
        image.loading = "lazy";
        image.src = evidenceUrl;
        image.addEventListener("error", () => image.replaceWith(placeholder()), { once: true });
        button.append(image);
      } else button.append(placeholder());
      const content = document.createElement("span");
      content.className = "event-text";
      const title = document.createElement("strong");
      title.textContent = `${timeLabel(event.start_seconds)} — ${timeLabel(event.end_seconds)}`;
      const detail = document.createElement("span");
      detail.textContent = `Điểm mô hình cao nhất: ${modelScore(event.peak_probability)}`;
      content.append(title, detail);
      button.append(content, icon("play"));
      button.addEventListener("click", () => {
        if (!selectedFile) return;
        const video = elements.videoPreview;
        if (video.error || !video.seekable.length) {
          elements.previewWarning.hidden = false;
          announce("Trình duyệt chưa thể phát video này. Xem khung hình minh họa và mốc thời gian trong kết quả.");
          return;
        }
        video.currentTime = Math.max(0, event.start_seconds);
        video.play().catch(() => { });
        video.focus();
        video.scrollIntoView({ block: "center", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
      });
      elements.eventList.append(button);
    }
  }

  function renderStats(stats) {
    elements.analysisStats.replaceChildren();
    const values = [
      ["Độ dài video", timeLabel(stats.duration_seconds)],
      ["Cửa sổ phân tích", isNumber(stats.windows_analyzed) ? numberFormat.format(stats.windows_analyzed) : "—"],
      ["Thời gian xử lý", isNumber(stats.processing_seconds) ? `${numberFormat.format(stats.processing_seconds)} giây` : "—"],
    ];
    for (const [label, value] of values) {
      const item = document.createElement("div");
      item.className = "analysis-stat";
      const name = document.createElement("span");
      name.textContent = label;
      const number = document.createElement("strong");
      number.textContent = value;
      item.append(name, number);
      elements.analysisStats.append(item);
    }
  }

  function renderResult(result) {
    if (!result || !["fall", "no_fall", "inconclusive"].includes(result.status)) throw new Error("Kết luận từ máy chủ chưa hợp lệ.");
    const labels = { fall: "Phát hiện té ngã", no_fall: "Không phát hiện té ngã", inconclusive: "Chưa đủ dữ liệu để kết luận" };
    elements.verdict.className = `verdict ${result.status}`;
    elements.verdictIcon.setAttribute("href", result.status === "no_fall" ? "#icon-check" : "#icon-alert");
    const verdictLabel = result.label || labels[result.status];
    setText("verdictLabel", verdictLabel);
    setText("verdictSummary", result.summary || "");
    setText("maxProbability", modelScore(result.max_probability));
    setText("thresholdValue", modelScore(result.threshold));
    renderDecisionDetails(result);
    const stats = result.stats || {};
    renderTimeline(result.timeline, result.threshold, stats.duration_seconds);
    renderEvents(result.events, result.status);
    renderStats(stats);
    elements.resultWarnings.replaceChildren();
    const warnings = [...new Set((Array.isArray(result.warnings) ? result.warnings : []).filter((warning) => typeof warning === "string" && warning.trim()))];
    if (!warnings.length && typeof result.model?.scope === "string") warnings.push(result.model.scope);
    for (const warning of warnings) {
      const note = document.createElement("p");
      note.textContent = warning;
      elements.resultWarnings.append(note);
    }
    elements.resultWarnings.hidden = !warnings.length;
    if (typeof result.model?.checkpoint === "string") {
      setText("modelCheckpoint", result.model.checkpoint.split(/[\\/]/).pop());
      elements.modelCheckpoint.title = result.model.checkpoint;
    }
    if (isNumber(result.model?.val_f1)) setText("modelF1", percent(result.model.val_f1));
    showView("completedResult");
    announce(`Phân tích hoàn tất. ${verdictLabel}. ${elements.decisionExplanation.textContent}`);
  }

  function renderDecisionDetails(result) {
    const timeline = Array.isArray(result.timeline) ? result.timeline : [];
    let scored = 0, above = 0, peak = null;
    for (const point of timeline) {
      if (!point || !isNumber(point.probability)) continue;
      scored += 1;
      if (!peak || point.probability > peak.probability) peak = point;
      if (isNumber(result.threshold) && point.probability >= result.threshold) {
        above += 1;
      }
    }
    setText("confirmedEvents", `${Array.isArray(result.events) ? result.events.length : 0} sự kiện`);
    setText("decisionExplanation", scored && isNumber(result.threshold)
      ? `${above}/${scored} đoạn đạt ngưỡng ${modelScore(result.threshold)}.`
      : "Chưa có đủ dữ liệu chuyển động để đánh giá.");
    elements.peakReviewButton.hidden = !peak || !isNumber(peak.time_seconds);
    if (!peak || !isNumber(peak.time_seconds)) return;
    const fps = result.model?.target_fps;
    const frames = result.model?.window_size;
    const start = isNumber(fps) && fps > 0 && isNumber(frames) ? Math.max(0, peak.time_seconds - (frames - 1) / fps) : peak.time_seconds;
    const precise = (seconds) => `${numberFormat.format(seconds)} giây`;
    elements.peakReviewButton.textContent = `Xem đoạn có điểm cao nhất: ${precise(start)} – ${precise(peak.time_seconds)}`;
    elements.peakReviewButton.onclick = () => {
      const video = elements.videoPreview;
      if (!selectedFile || video.error || !video.seekable.length) {
        elements.previewWarning.hidden = false;
        announce("Trình duyệt chưa phát được video. Bạn có thể xem lại mốc này trong video gốc.");
        return;
      }
      video.currentTime = start;
      video.play().catch(() => {});
      video.focus();
      video.scrollIntoView({block: "center", behavior: "smooth"});
    };
  }

  elements.dropZone.addEventListener("click", () => { if (!busy) elements.fileInput.click(); });
  elements.dropZone.addEventListener("keydown", (event) => {
    if (["Enter", " "].includes(event.key)) {
      event.preventDefault();
      if (!busy) elements.fileInput.click();
    }
  });
  elements.fileInput.addEventListener("change", () => selectFile(elements.fileInput.files?.[0]));
  ["dragenter", "dragover"].forEach((name) => elements.dropZone.addEventListener(name, (event) => {
    event.preventDefault();
    if (!busy) elements.dropZone.classList.add("dragging");
  }));
  ["dragleave", "drop"].forEach((name) => elements.dropZone.addEventListener(name, (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove("dragging");
  }));
  elements.dropZone.addEventListener("drop", (event) => {
    if (busy) return;
    if (event.dataTransfer.files.length > 1) {
      showUploadError("Vui lòng tải lên từng video để phân tích.");
      return;
    }
    selectFile(event.dataTransfer.files[0]);
  });
  window.addEventListener("dragover", (event) => { if (event.dataTransfer?.types.includes("Files")) event.preventDefault(); });
  window.addEventListener("drop", (event) => { if (event.dataTransfer?.types.includes("Files")) event.preventDefault(); });
  elements.videoPreview.addEventListener("loadedmetadata", updateFileMeta);
  elements.videoPreview.addEventListener("error", () => { if (selectedFile && previewUrl) elements.previewWarning.hidden = false; });
  elements.resetButton.addEventListener("click", reset);
  elements.analyzeButton.addEventListener("click", startAnalysis);
  elements.retryButton.addEventListener("click", startAnalysis);
  elements.modelRetry.addEventListener("click", loadModel);
  window.addEventListener("online", () => { if (!modelReady) loadModel(); });
  window.addEventListener("fallsense-camera-state", (event) => {
    cameraActive = Boolean(event.detail?.active);
    updateControls();
  });
  window.addEventListener("beforeunload", (event) => {
    if (busy) { event.preventDefault(); event.returnValue = ""; }
  });
  loadModel();
})();
