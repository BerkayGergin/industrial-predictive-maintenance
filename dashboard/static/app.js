const $ = (id) => document.getElementById(id);
const state = { telemetry: null, alarms: [], simulation: null, ws: null, pingTimer: null };

function fmt(value, digits = 1) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(digits) : "--";
}

function timeLabel(iso) {
  if (!iso) return "--";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleTimeString();
}

class LineChart {
  constructor(canvas, series, maxPoints = 180) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.series = series;
    this.maxPoints = maxPoints;
    this.points = [];
  }
  push(point) {
    this.points.push(point);
    if (this.points.length > this.maxPoints) this.points.shift();
    this.draw();
  }
  setPoints(points) {
    this.points = points.slice(-this.maxPoints);
    this.draw();
  }
  draw() {
    const ctx = this.ctx, w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#0a1520"; ctx.fillRect(0, 0, w, h);
    const pad = { l: 52, r: 20, t: 20, b: 28 };
    const plotW = w - pad.l - pad.r, plotH = h - pad.t - pad.b;
    const vals = [];
    this.points.forEach(p => this.series.forEach(s => { const v = Number(p[s.key]); if (Number.isFinite(v)) vals.push(v); }));
    let min = vals.length ? Math.min(...vals) : 0, max = vals.length ? Math.max(...vals) : 1;
    if (this.series.some(s => s.minZero)) min = Math.min(0, min);
    if (max === min) { max += 1; min -= 1; }
    const margin = (max - min) * 0.12; max += margin; min -= margin;
    ctx.strokeStyle = "#243544"; ctx.lineWidth = 1; ctx.fillStyle = "#8497a6"; ctx.font = "12px system-ui";
    for (let i = 0; i <= 4; i++) {
      const y = pad.t + (plotH * i / 4);
      ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
      const value = max - (max - min) * i / 4;
      ctx.fillText(value.toFixed(1), 7, y + 4);
    }
    this.series.forEach((s, idx) => {
      ctx.strokeStyle = s.color; ctx.lineWidth = 2; ctx.beginPath();
      let started = false;
      this.points.forEach((p, i) => {
        const v = Number(p[s.key]); if (!Number.isFinite(v)) return;
        const x = pad.l + (this.points.length <= 1 ? 0 : i * plotW / (this.points.length - 1));
        const y = pad.t + (max - v) * plotH / (max - min);
        if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.fillStyle = s.color; ctx.fillRect(pad.l + idx * 150, h - 14, 10, 3);
      ctx.fillStyle = "#b9c8d2"; ctx.fillText(s.label, pad.l + 15 + idx * 150, h - 9);
    });
  }
}

const liveConditionChart = new LineChart($("liveConditionChart"), [
  { key: "vibration", label: "Vibration mm/s", color: "#39d0b5", minZero: true },
  { key: "anomaly_scaled", label: "Anomaly × 5", color: "#5aa9ff", minZero: true },
], 160);
const liveTemperatureChart = new LineChart($("liveTemperatureChart"), [
  { key: "motor_temperature", label: "Motor °C", color: "#f7b955" },
  { key: "bearing_temperature", label: "Bearing °C", color: "#ff6673" },
], 160);
const historyConditionChart = new LineChart($("historyConditionChart"), [
  { key: "vibration", label: "Vibration mm/s", color: "#39d0b5", minZero: true },
  { key: "load_scaled", label: "Load ÷ 20", color: "#b28cff", minZero: true },
  { key: "anomaly_scaled", label: "Anomaly × 5", color: "#5aa9ff", minZero: true },
], 1200);
const historyHealthChart = new LineChart($("historyHealthChart"), [
  { key: "health_score", label: "Health score", color: "#4bd49b", minZero: true },
  { key: "bearing_temperature", label: "Bearing °C", color: "#ff6673", minZero: true },
], 1200);

function setHealthState(t) {
  const el = $("healthState");
  el.textContent = t.health_state || "NO DATA";
  el.className = "badge " + (t.health_state || "").toLowerCase();
  $("healthScore").textContent = Number.isFinite(Number(t.health_score)) ? `${t.health_score}/100` : "--";
  $("healthBar").style.width = `${Math.max(0, Math.min(100, Number(t.health_score) || 0))}%`;
  $("anomalyScore").textContent = fmt(t.anomaly_score, 2);
  $("baselineState").textContent = t.anomaly_baseline_ready ? "Healthy baseline ready" : "Learning healthy baseline…";
  $("recommendation").textContent = t.analysis?.recommendation || "Waiting for analysis.";
  const contributors = t.analysis?.contributors || [];
  $("contributors").innerHTML = contributors.length
    ? contributors.slice(0, 4).map(c => `<div class="contributor"><span>${c.name}</span><span>−${fmt(c.penalty, 1)}</span></div>`).join("")
    : `<div class="muted">No significant health penalties.</div>`;
}

function updateTelemetry(t) {
  state.telemetry = t;
  $("rpm").textContent = fmt(t.rpm, 0);
  $("load").textContent = fmt(t.load, 1);
  $("vibration").textContent = fmt(t.vibration, 2);
  $("bearingTemp").textContent = fmt(t.bearing_temperature, 1);
  $("motorTemp").textContent = fmt(t.motor_temperature, 1);
  $("current").textContent = fmt(t.current, 2);
  $("power").textContent = fmt(t.power, 2);
  $("hours").textContent = fmt(t.operating_hours, 1);
  $("lastUpdate").textContent = `Telemetry ${timeLabel(t.time)}`;
  $("truthFault").textContent = t.fault_mode || "--";
  $("truthProgress").textContent = `${fmt((Number(t.fault_progress) || 0) * 100, 0)}%`;
  $("truthRunning").textContent = t.running ? "RUNNING" : "STOPPED";
  setHealthState(t);
  liveConditionChart.push({ vibration: t.vibration, anomaly_scaled: (Number(t.anomaly_score) || 0) * 5 });
  liveTemperatureChart.push({ motor_temperature: t.motor_temperature, bearing_temperature: t.bearing_temperature });
}

function renderAlarms(alarms) {
  state.alarms = alarms;
  const body = $("alarmBody");
  if (!alarms.length) {
    body.innerHTML = `<tr><td colspan="7" class="muted">No open alarms.</td></tr>`;
    return;
  }
  body.innerHTML = alarms.map(a => {
    const val = a.value == null ? "--" : `${fmt(a.value, 2)} ${a.unit || ""}`;
    const action = a.state === "ACTIVE" ? `<button class="button secondary ack" data-id="${a.id}">Acknowledge</button>` : "—";
    return `<tr><td><span class="alarm-pill ${String(a.severity).toLowerCase()}">${a.severity}</span></td><td>${a.code}</td><td>${a.message}</td><td>${val}</td><td>${a.state}</td><td>${timeLabel(a.activated_at)}</td><td>${action}</td></tr>`;
  }).join("");
  document.querySelectorAll(".ack").forEach(btn => btn.addEventListener("click", () => acknowledgeAlarm(btn.dataset.id)));
}

async function api(path, options = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try { const body = await res.json(); msg = body.detail || msg; } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

async function acknowledgeAlarm(id) {
  try { await api(`/api/alarms/${id}/ack`, { method: "POST", body: JSON.stringify({ acknowledged_by: "dashboard-operator" }) }); }
  catch (e) { alert(`Acknowledge failed: ${e.message}`); }
}

function setWsStatus(status, text) {
  $("wsDot").className = `status-dot ${status}`;
  $("wsText").textContent = text;
}

function connectWebSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${location.host}/ws/telemetry`);
  state.ws = ws;
  ws.onopen = () => {
    setWsStatus("online", "WebSocket live");
    if (state.pingTimer) clearInterval(state.pingTimer);
    state.pingTimer = setInterval(() => { if (ws.readyState === WebSocket.OPEN) ws.send("ping"); }, 15000);
  };
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === "telemetry") updateTelemetry(msg.data);
    if (msg.type === "alarms") renderAlarms(msg.data);
  };
  ws.onerror = () => setWsStatus("offline", "WebSocket error");
  ws.onclose = () => {
    setWsStatus("offline", "WebSocket reconnecting");
    if (state.pingTimer) clearInterval(state.pingTimer);
    setTimeout(connectWebSocket, 1800);
  };
}

async function loadHistory() {
  const minutes = $("historyMinutes").value;
  $("historyInfo").textContent = "Loading history…";
  try {
    const rows = await api(`/api/motors/Motor_01/history?minutes=${minutes}&limit=5000`);
    historyConditionChart.setPoints(rows.map(r => ({ vibration: r.vibration, load_scaled: Number(r.load) / 20, anomaly_scaled: Number(r.anomaly_score) * 5 })));
    historyHealthChart.setPoints(rows.map(r => ({ health_score: r.health_score, bearing_temperature: r.bearing_temperature })));
    $("historyInfo").textContent = `${rows.length} historian samples loaded for the last ${minutes} minute(s).`;
  } catch (e) { $("historyInfo").textContent = `History error: ${e.message}`; }
}

async function refreshSimulationState() {
  try {
    const s = await api("/api/simulation/state"); state.simulation = s;
    $("simStatus").textContent = "OPC UA controls online";
    $("faultMode").value = s.fault_mode;
    $("faultIntensity").value = Math.round(Number(s.fault_intensity) * 100);
    $("faultIntensityLabel").textContent = `${$("faultIntensity").value}%`;
    $("targetLoad").value = Math.round(Number(s.target_load));
    updateLoadLabel();
    $("truthLoad").textContent = Number(s.target_load) < 0 ? "AUTO" : `${fmt(s.target_load, 0)}%`;
    $("runningToggle").textContent = s.running_command ? "Stop motor" : "Start motor";
  } catch (e) { $("simStatus").textContent = `Control offline: ${e.message}`; }
}

function updateLoadLabel() { const v = Number($("targetLoad").value); $("targetLoadLabel").textContent = v < 0 ? "AUTO" : `${v}%`; }

$("faultIntensity").addEventListener("input", () => $("faultIntensityLabel").textContent = `${$("faultIntensity").value}%`);
$("targetLoad").addEventListener("input", updateLoadLabel);
$("applyFault").addEventListener("click", async () => {
  try { await api("/api/simulation/fault", { method: "POST", body: JSON.stringify({ mode: $("faultMode").value, intensity: Number($("faultIntensity").value) / 100 }) }); await refreshSimulationState(); }
  catch (e) { alert(`Fault command failed: ${e.message}`); }
});
$("resetFault").addEventListener("click", async () => { try { await api("/api/simulation/reset", { method: "POST" }); await refreshSimulationState(); } catch (e) { alert(e.message); } });
$("applyLoad").addEventListener("click", async () => { try { await api("/api/simulation/load", { method: "POST", body: JSON.stringify({ target_load: Number($("targetLoad").value) }) }); await refreshSimulationState(); } catch (e) { alert(e.message); } });
$("autoLoad").addEventListener("click", async () => { $("targetLoad").value = -1; updateLoadLabel(); try { await api("/api/simulation/load", { method: "POST", body: JSON.stringify({ target_load: -1 }) }); await refreshSimulationState(); } catch (e) { alert(e.message); } });
$("runningToggle").addEventListener("click", async () => { const next = !(state.simulation?.running_command ?? true); try { await api("/api/simulation/running", { method: "POST", body: JSON.stringify({ running: next }) }); await refreshSimulationState(); } catch (e) { alert(e.message); } });
$("loadHistory").addEventListener("click", loadHistory);

document.querySelectorAll(".tab").forEach(tab => tab.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
  document.querySelectorAll(".tab-panel").forEach(x => x.classList.remove("active"));
  tab.classList.add("active"); $(tab.dataset.tab).classList.add("active");
  if (tab.dataset.tab === "trends") loadHistory();
  if (tab.dataset.tab === "simulation") refreshSimulationState();
}));

connectWebSocket();
refreshSimulationState();
