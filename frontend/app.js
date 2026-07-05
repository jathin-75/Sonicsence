const API_BASE = "http://127.0.0.1:8000";

const SOUND_ICONS = {
  "Dog Bark": "🐕", "Baby Crying": "🍼", "Gunshot": "🔫", "Glass Breaking": "🔨",
  "Fire Alarm": "🚨", "Siren": "🚔", "Door Knock": "🚪", "Footsteps": "👣",
  "Engine Sound": "🚗", "Vehicle Horn": "📢", "Rain": "🌧", "Thunder": "⛈",
  "Human Speech": "🗣", "Clapping": "👏", "Keyboard Typing": "⌨️",
  "Machine Noise": "⚙️", "Drilling": "🛠", "Construction Sound": "🏗",
  "Bird Chirping": "🐦", "Cat Meowing": "🐈", "Television": "📺",
  "Music": "🎵", "Laughter": "😂", "Cough": "🤧", "Doorbell": "🔔",
  "Alarm Clock": "⏰", "Wind": "🌬", "Water Running": "🚿",
  "Phone Ringing": "📱", "Snoring": "😴",
};
const ALL_CLASSES = Object.keys(SOUND_ICONS);

let token = null;
let userEmail = null;
let ws = null;
let startTime = null;
let stats = { total: 0, confidenceSum: 0, alerts: 0 };

// ---------- Password show/hide toggle ----------
const togglePasswordBtn = document.getElementById("toggle-password");
if (togglePasswordBtn) {
  togglePasswordBtn.addEventListener("click", () => {
    const pwInput = document.getElementById("password");
    if (pwInput.type === "password") {
      pwInput.type = "text";
      togglePasswordBtn.textContent = "🙈";
    } else {
      pwInput.type = "password";
      togglePasswordBtn.textContent = "👁";
    }
  });
}

// ---------- Auth screen tab switching ----------
const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");
const authSubmit = document.getElementById("auth-submit");
let mode = "login";

tabLogin.addEventListener("click", () => setMode("login"));
tabRegister.addEventListener("click", () => setMode("register"));

function setMode(newMode) {
  mode = newMode;
  tabLogin.classList.toggle("active", mode === "login");
  tabRegister.classList.toggle("active", mode === "register");
  authSubmit.textContent = mode === "login" ? "Login" : "Create Account";
  document.getElementById("auth-error").textContent = "";
}

// ---------- Auth form submit ----------
document.getElementById("auth-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const errorEl = document.getElementById("auth-error");
  errorEl.textContent = "";

  const endpoint = mode === "login" ? "/auth/login" : "/auth/register";

  try {
    const res = await fetch(API_BASE + endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();

    if (!res.ok) {
      errorEl.textContent = data.detail || "Something went wrong";
      return;
    }

    token = data.access_token;
    userEmail = email;
    enterDashboard();
  } catch (err) {
    errorEl.textContent = "Cannot reach server. Is the backend running?";
  }
});

// ---------- Logout ----------
document.getElementById("logout-btn").addEventListener("click", () => {
  token = null;
  userEmail = null;
  if (ws) ws.close();
  document.getElementById("dashboard").classList.add("hidden");
  document.getElementById("auth-screen").classList.remove("hidden");
  document.getElementById("auth-form").reset();
});

// ---------- Enter dashboard ----------
function enterDashboard() {
  document.getElementById("auth-screen").classList.add("hidden");
  document.getElementById("dashboard").classList.remove("hidden");
  document.getElementById("user-email").textContent = userEmail;

  buildClassGrid();
  startUptime();
  connectLiveFeed();
  loadHistory();
  drawIdleWaveform();
}

// ---------- Sound class grid ----------
function buildClassGrid() {
  const grid = document.getElementById("class-grid");
  grid.innerHTML = "";
  ALL_CLASSES.forEach((label) => {
    const div = document.createElement("div");
    div.className = "class-item";
    div.id = "class-" + slug(label);
    div.innerHTML = `<span class="class-icon">${SOUND_ICONS[label]}</span>${label}`;
    grid.appendChild(div);
  });
}

function slug(label) {
  return label.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

function flashClass(label, critical) {
  const el = document.getElementById("class-" + slug(label));
  if (!el) return;
  el.classList.add("active");
  if (critical) el.classList.add("critical");
  setTimeout(() => {
    el.classList.remove("active", "critical");
  }, 2500);
}

// ---------- Uptime counter ----------
function startUptime() {
  startTime = Date.now();
  setInterval(() => {
    const diff = Date.now() - startTime;
    const h = String(Math.floor(diff / 3600000)).padStart(2, "0");
    const m = String(Math.floor((diff % 3600000) / 60000)).padStart(2, "0");
    const s = String(Math.floor((diff % 60000) / 1000)).padStart(2, "0");
    document.getElementById("stat-uptime").textContent = `${h}:${m}:${s}`;
  }, 1000);
}

// ---------- Live WebSocket feed ----------
function connectLiveFeed() {
  ws = new WebSocket(API_BASE.replace("http", "ws") + "/ws/live");

  ws.onmessage = (event) => {
    const result = JSON.parse(event.data);
    handleDetection(result);
  };

  ws.onerror = () => console.warn("WebSocket error — live feed unavailable");
}

// ---------- Handle a detection (from live feed or upload) ----------
function handleDetection(result) {
  addFeedItem(result);
  flashClass(result.label, result.critical);
  updateGauge(result.confidence);
  updateStats(result);

  if (result.critical) {
    triggerAlert(result.label);
  }
}

function addFeedItem(result) {
  const feed = document.getElementById("feed-list");
  const item = document.createElement("div");
  item.className = "feed-item" + (result.critical ? " critical" : "");
  item.innerHTML = `
    <span class="feed-icon">${SOUND_ICONS[result.label] || "🔊"}</span>
    <div class="feed-info">
      <div class="feed-label">${result.label}</div>
      <div class="feed-bar-bg"><div class="feed-bar-fill" style="width:${result.confidence}%"></div></div>
    </div>
    <span class="feed-confidence">${result.confidence}%</span>
  `;
  feed.prepend(item);

  while (feed.children.length > 12) feed.removeChild(feed.lastChild);

  setTimeout(() => {
    item.style.transition = "opacity 1s ease";
    item.style.opacity = "0.35";
  }, 8000);
}

function updateGauge(confidence) {
  const fill = document.getElementById("gauge-fill");
  const value = document.getElementById("gauge-value");
  const circumference = 534;
  const offset = circumference - (confidence / 100) * circumference;
  fill.style.strokeDashoffset = offset;
  value.textContent = confidence + "%";

  fill.style.stroke =
    confidence > 90 ? "var(--green)" : confidence > 75 ? "var(--cyan)" : "var(--magenta)";
}

function updateStats(result) {
  stats.total++;
  stats.confidenceSum += result.confidence;
  if (result.critical) stats.alerts++;

  document.getElementById("stat-total").textContent = stats.total;
  document.getElementById("stat-avg").textContent =
    Math.round(stats.confidenceSum / stats.total) + "%";
  document.getElementById("stat-alerts").textContent = stats.alerts;
}

// ---------- Critical alert overlay ----------
function triggerAlert(label) {
  const overlay = document.getElementById("alert-overlay");
  document.getElementById("alert-label").textContent = label.toUpperCase();
  overlay.classList.remove("hidden");
  setTimeout(() => overlay.classList.add("hidden"), 2500);
}

// ---------- Upload ----------
document.getElementById("file-input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  const audioURL = URL.createObjectURL(file);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(API_BASE + "/upload", {
      method: "POST",
      headers: { Authorization: "Bearer " + token },
      body: formData,
    });
    const data = await res.json();
    if (res.ok) {
      if (data.predictions.length > 0) {
        showResultBanner(data.predictions[0], audioURL);
      }
      data.predictions.forEach((p) => handleDetection(p));
      loadHistory();
    } else {
      alert(data.detail || "Upload failed");
    }
  } catch (err) {
    alert("Upload failed — is the backend running?");
  }

  e.target.value = "";
});

function showResultBanner(result, audioURL) {
  const banner = document.getElementById("result-banner");
  document.getElementById("result-icon").textContent = SOUND_ICONS[result.label] || "🔊";
  document.getElementById("result-label").textContent = result.label;
  document.getElementById("result-confidence").textContent = result.confidence + "%";

  const audioPlayer = document.getElementById("result-audio");
  if (audioURL) {
    audioPlayer.src = audioURL;
  }

  banner.classList.remove("hidden");
  banner.classList.toggle("critical", result.critical);

  banner.style.animation = "none";
  void banner.offsetWidth;
  banner.style.animation = "";
}

// ---------- History timeline ----------
async function loadHistory() {
  try {
    const res = await fetch(API_BASE + "/history", {
      headers: { Authorization: "Bearer " + token },
    });
    const data = await res.json();
    const timeline = document.getElementById("timeline");
    timeline.innerHTML = "";

    data.forEach((item) => {
      const div = document.createElement("div");
      div.className = "timeline-item";
      const time = new Date(item.timestamp).toLocaleTimeString();
      div.innerHTML = `
        <div class="timeline-time">${time}</div>
        <div class="timeline-label">${SOUND_ICONS[item.label] || "🔊"} ${item.label}</div>
        <div class="timeline-conf">${item.confidence}%</div>
      `;
      timeline.appendChild(div);
    });
  } catch (err) {
    console.warn("Could not load history");
  }
}

// ---------- Mic button (real Web Audio waveform, visual only) ----------
const micBtn = document.getElementById("mic-btn");
let listening = false;
let audioCtx, analyser, dataArray, source, stream;

micBtn.addEventListener("click", async () => {
  if (!listening) {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      source = audioCtx.createMediaStreamSource(stream);
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      dataArray = new Uint8Array(analyser.frequencyBinCount);
      source.connect(analyser);

      listening = true;
      micBtn.classList.add("listening");
      drawLiveWaveform();
    } catch (err) {
      alert("Microphone access denied or unavailable.");
    }
  } else {
    listening = false;
    micBtn.classList.remove("listening");
    if (stream) stream.getTracks().forEach((t) => t.stop());
    drawIdleWaveform();
  }
});

// ---------- Waveform rendering ----------
const canvas = document.getElementById("waveform");
const ctx = canvas.getContext("2d");

function resizeCanvas() {
  canvas.width = canvas.clientWidth;
  canvas.height = canvas.clientHeight;
}
window.addEventListener("resize", resizeCanvas);
resizeCanvas();

function drawLiveWaveform() {
  if (!listening) return;
  requestAnimationFrame(drawLiveWaveform);
  analyser.getByteTimeDomainData(dataArray);

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#00e5ff";
  ctx.shadowBlur = 10;
  ctx.shadowColor = "#00e5ff";
  ctx.beginPath();

  const sliceWidth = canvas.width / dataArray.length;
  let x = 0;
  for (let i = 0; i < dataArray.length; i++) {
    const v = dataArray[i] / 128.0;
    const y = (v * canvas.height) / 2;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    x += sliceWidth;
  }
  ctx.stroke();
}

function drawIdleWaveform() {
  let t = 0;
  function frame() {
    if (listening) return;
    t += 0.05;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = "rgba(0, 229, 255, 0.35)";
    ctx.beginPath();
    for (let x = 0; x < canvas.width; x++) {
      const y = canvas.height / 2 + Math.sin(x * 0.03 + t) * 6;
      x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();
    requestAnimationFrame(frame);
  }
  frame();
}