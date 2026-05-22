const API = '';
let currentSession = null;
let sessions = [];

// ── DOM refs ──
const chatArea = document.getElementById('chatArea');
const welcomeScreen = document.getElementById('welcomeScreen');
const typingEl = document.getElementById('typing');
const inputField = document.getElementById('cmdInput');
const sessionList = document.getElementById('sessionList');
const uptimeEl = document.getElementById('uptimeVal');
const cpuEl = document.getElementById('cpuVal');
const cpuBar = document.getElementById('cpuBar');
const ramEl = document.getElementById('ramVal');
const ramBar = document.getElementById('ramBar');
const brainEl = document.getElementById('brainVal');
const visionImg = document.getElementById('visionImg');
const visionEmpty = document.getElementById('visionEmpty');

// ── Sessions ──
async function loadSessions() {
  try {
    const r = await fetch(API + '/api/sessions');
    sessions = await r.json();
    renderSessions();
  } catch(e) { console.error('Failed to load sessions', e); }
}

function renderSessions() {
  sessionList.innerHTML = '';
  sessions.forEach(s => {
    const div = document.createElement('div');
    div.className = 'session-item' + (currentSession === s.id ? ' active' : '');
    div.innerHTML = `<span class="session-del" onclick="event.stopPropagation();deleteSession('${s.id}')">&times;</span><div class="session-title">${esc(s.title)}</div><div class="session-time">${formatTime(s.updated_at)}</div>`;
    div.onclick = () => loadSession(s.id);
    sessionList.appendChild(div);
  });
}

async function loadSession(sid) {
  currentSession = sid;
  renderSessions();
  chatArea.innerHTML = '';
  welcomeScreen.style.display = 'none';
  chatArea.style.display = 'flex';
  try {
    const r = await fetch(API + `/api/sessions/${sid}/messages`);
    const msgs = await r.json();
    msgs.forEach(m => appendMsg(m.role === 'user' ? 'user' : 'ai', m.content, m.timestamp, false));
    chatArea.scrollTop = chatArea.scrollHeight;
  } catch(e) { console.error(e); }
}

async function deleteSession(sid) {
  await fetch(API + `/api/sessions/${sid}`, { method: 'DELETE' });
  if (currentSession === sid) { currentSession = null; chatArea.innerHTML = ''; chatArea.style.display = 'none'; welcomeScreen.style.display = 'flex'; }
  loadSessions();
}

function newSession() {
  currentSession = null;
  chatArea.innerHTML = '';
  chatArea.style.display = 'none';
  welcomeScreen.style.display = 'flex';
  renderSessions();
  inputField.focus();
}

// ── Chat ──
async function sendCmd() {
  const val = inputField.value.trim();
  if (!val) return;
  inputField.value = '';

  // Show chat area
  welcomeScreen.style.display = 'none';
  chatArea.style.display = 'flex';

  appendMsg('user', val);
  showTyping(true);

  try {
    const r = await fetch(API + '/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: val, session_id: currentSession })
    });
    const data = await r.json();
    showTyping(false);
    appendMsg('ai', data.response);
    if (!currentSession || currentSession !== data.session_id) {
      currentSession = data.session_id;
      loadSessions();
    }
  } catch(e) {
    showTyping(false);
    appendMsg('ai', 'Connection to Cortex failed.');
  }
}

function appendMsg(type, text, timestamp, animate = true) {
  const ts = timestamp ? formatTime(timestamp) : new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});
  const div = document.createElement('div');
  div.className = `msg msg-${type}`;
  if (!animate) div.style.animation = 'none';
  const senderLabel = type === 'user' ? 'DHRUVAM · ROOT' : 'DRAVION · CEO';
  const senderClass = type === 'user' ? '' : ' cyan';
  div.innerHTML = `<div class="msg-sender${senderClass}">${senderLabel}</div><div class="msg-bubble">${formatContent(text)}</div><div class="msg-time">${ts}</div>`;
  chatArea.appendChild(div);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function showTyping(show) { typingEl.className = 'typing' + (show ? ' show' : ''); chatArea.scrollTop = chatArea.scrollHeight; }

// ── Tabs ──
document.querySelectorAll('.tab-btn').forEach(t => {
  t.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    t.classList.add('active');
    document.getElementById('tab-' + t.dataset.tab).classList.add('active');
  });
});

// ── Vision ──
async function captureScreen() {
  visionEmpty.textContent = 'Capturing...';
  try {
    const r = await fetch(API + '/api/vision/screenshot');
    const data = await r.json();
    if (data.image) {
      visionImg.src = data.image;
      visionImg.style.display = 'block';
      visionEmpty.style.display = 'none';
    } else {
      visionEmpty.textContent = 'Capture failed: ' + (data.error || 'Unknown');
    }
  } catch(e) { visionEmpty.textContent = 'Connection error'; }
}

// ── System Metrics ──
async function refreshMetrics() {
  try {
    const r = await fetch(API + '/api/system');
    const d = await r.json();
    uptimeEl.textContent = d.uptime;
    cpuEl.textContent = d.cpu_percent + '%';
    cpuBar.style.width = d.cpu_percent + '%';
    ramEl.textContent = d.ram_used_gb + 'GB';
    ramBar.style.width = d.ram_percent + '%';
    brainEl.textContent = d.brain_mode.toUpperCase();
    // Update mode buttons
    document.querySelectorAll('.mode-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.mode === d.brain_mode);
    });
  } catch(e) {}
}

// ── Mode Switch ──
document.querySelectorAll('.mode-btn').forEach(b => {
  b.addEventListener('click', async () => {
    await fetch(API + `/api/mode/${b.dataset.mode}`, { method: 'POST' });
    refreshMetrics();
  });
});

// ── Helpers ──
function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function formatContent(text) {
  let s = esc(text);
  // Code blocks
  s = s.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre style="background:rgba(0,200,255,.05);border:1px solid var(--border);padding:8px;margin:6px 0;overflow-x:auto;font-size:11px">$2</pre>');
  // Inline code
  s = s.replace(/`([^`]+)`/g, '<code style="background:rgba(0,200,255,.1);padding:1px 4px;font-size:11px">$1</code>');
  // Bold
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong style="color:var(--txt-b)">$1</strong>');
  // Newlines
  s = s.replace(/\n/g, '<br>');
  return s;
}
function formatTime(ts) {
  if (!ts) return '';
  try { const d = new Date(ts); return d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}); }
  catch(e) { return ts; }
}

// ── Init ──
inputField.addEventListener('keydown', e => { if (e.key === 'Enter') sendCmd(); });
loadSessions();
refreshMetrics();
setInterval(refreshMetrics, 5000);
