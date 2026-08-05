// Toggle Sidebar Drawer Visibility
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  sidebar.classList.toggle('-ml-72');
}

// Toggle Collapsible Accordion Groups in Sidebar
function toggleAccordion(id) {
  const content = document.getElementById(id);
  const icon = document.getElementById('icon-' + id);
  if (content) {
    content.classList.toggle('hidden');
  }
  if (icon) {
    icon.classList.toggle('rotate-180');
  }
}

// Toggle Popover Overlays (Alerts, Accessibility)
function togglePop(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.toggle('hidden');
  }
}

// Switch Light / Dark Mode
function toggleDarkMode() {
  const html = document.documentElement;
  const themeIcon = document.getElementById('theme-icon');
  
  if (html.classList.contains('dark')) {
    html.classList.remove('dark');
    if (themeIcon) {
      themeIcon.className = 'fa-solid fa-sun text-amber-500 text-lg';
    }
  } else {
    html.classList.add('dark');
    if (themeIcon) {
      themeIcon.className = 'fa-solid fa-moon text-lg';
    }
  }
}

// Switch Active View Panels
function switchView(viewName) {
  // Hide all view panels
  document.querySelectorAll('.view-panel').forEach(panel => panel.classList.add('hidden'));

  // Show selected panel
  const target = document.getElementById('view-' + viewName);
  if (target) {
    target.classList.remove('hidden');
  }

  // Update Breadcrumb Text in Top Bar
  const breadcrumb = document.getElementById('header-breadcrumb');
  const titles = {
    'home': 'Home',
    'chat': 'Home / Ask India Groundwater',
    'simulation': 'Home / Policy Simulation',
    'admin': 'Home / Administration',
    'map': 'Home / Map View'
  };
  if (breadcrumb) {
    breadcrumb.innerHTML = `<span>${titles[viewName] || 'Dashboard'}</span>`;
  }
}

// Switch Administration Sub-tabs
function switchAdminTab(tabId) {
  document.querySelectorAll('.admin-tab').forEach(tab => tab.classList.add('hidden'));
  const activeTab = document.getElementById(tabId);
  if (activeTab) {
    activeTab.classList.remove('hidden');
  }

  // Highlight active tab button
  document.querySelectorAll('#view-admin button').forEach(btn => {
    btn.classList.remove('border-b-2', 'border-blue-600', 'text-blue-600', 'dark:text-blue-400');
    btn.classList.add('text-slate-500');
  });

  const activeBtn = document.getElementById('btn-' + tabId);
  if (activeBtn) {
    activeBtn.classList.add('border-b-2', 'border-blue-600', 'text-blue-600', 'dark:text-blue-400');
    activeBtn.classList.remove('text-slate-500');
  }
}

// Pre-fill prompt text into home input
function fillQuery(text) {
  const input = document.getElementById('home-input');
  if (input) {
    input.value = text;
  }
}

// Ensure initial view is loaded properly on launch
document.addEventListener('DOMContentLoaded', () => {
  switchView('home');
});

// ============================================================================
// INGRES-AI BACKEND INTEGRATION
// Everything below talks to the FastAPI backend (POST /api/v1/chat) and
// renders its structured response (reply + records + chart + crop_advisory)
// into the chat view. Nothing above this line was touched.
// ============================================================================

// Change this if your backend isn't running on localhost:8000 (e.g. once deployed)
const API_BASE_URL = 'http://localhost:8000';

// Groups messages into one conversation so the backend/AI model has context
// across turns. Starts null (first call gets a fresh one back from the server).
let currentSessionId = null;

// Tailwind classes matching the category-badge colors already used elsewhere
// in this UI (see the "Critical"/"Over-Exploited" badges in the alerts popover).
const CATEGORY_STYLES = {
  'Safe': 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300',
  'Semi-Critical': 'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-700 dark:text-yellow-300',
  'Critical': 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300',
  'Over-Exploited': 'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300',
  'Saline': 'bg-cyan-100 dark:bg-cyan-900/50 text-cyan-700 dark:text-cyan-300',
};


// LLM/user input, so this avoids it being interpreted as markup.
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str == null ? '' : String(str);
  return div.innerHTML;
}

function clearHomeHint(thread) {
  // Removes the "Ask a question below to start..." placeholder on first message
  const hint = thread.querySelector('[data-chat-hint]');
  if (hint) hint.remove();
}

function appendUserMessage(text) {
  const thread = document.getElementById('chat-messages');
  if (!thread) return;
  clearHomeHint(thread);
  const bubble = document.createElement('div');
  bubble.className = 'flex justify-end';
  bubble.innerHTML = `
    <div class="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[80%] text-sm shadow">
      ${escapeHtml(text)}
    </div>`;
  thread.appendChild(bubble);
  thread.scrollTop = thread.scrollHeight;
}

function appendAssistantMessage(data) {
  const thread = document.getElementById('chat-messages');
  if (!thread) return;
  clearHomeHint(thread);

  const wrapper = document.createElement('div');
  wrapper.className = 'flex justify-start';

  // De-duplicated category badges from the matched records
  const categories = (data.records || []).reduce(
    (acc, r) => (acc.includes(r.category) ? acc : [...acc, r.category]), []
  );
  const badgesHtml = categories
    .map(cat => `<span class="px-1.5 py-0.5 rounded text-[11px] font-medium ${CATEGORY_STYLES[cat] || 'bg-slate-100 text-slate-600'}">${escapeHtml(cat)}</span>`)
    .join(' ');

  const advisoryHtml = (data.crop_advisory && data.crop_advisory.length)
    ? `<ul class="mt-2 text-xs list-disc list-inside space-y-0.5 text-slate-600 dark:text-slate-400">
         ${data.crop_advisory.map(tip => `<li>${escapeHtml(tip)}</li>`).join('')}
       </ul>`
    : '';

  const chartCanvasId = `chat-chart-${Date.now()}`;
  const chartHtml = data.chart ? `<canvas id="${chartCanvasId}" class="mt-3" height="180"></canvas>` : '';

  // A quiet indicator of whether this came from the real AI model or the
  // backend's offline fallback (see llm_status in the API response) — useful
  // while you're setting up your GROQ_API_KEY.
  const modeNote = data.llm_status && data.llm_status !== 'ok'
    ? `<p class="text-[10px] text-amber-600 dark:text-amber-400 mt-2">⚠ offline mode — AI model not reachable (${escapeHtml(data.llm_status)})</p>`
    : '';

  wrapper.innerHTML = `
    <div class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl rounded-tl-sm px-4 py-3 max-w-[85%] text-sm shadow">
      <p class="whitespace-pre-line text-slate-800 dark:text-slate-100">${escapeHtml(data.reply)}</p>
      ${badgesHtml ? `<div class="flex flex-wrap gap-1.5 mt-2">${badgesHtml}</div>` : ''}
      ${advisoryHtml}
      ${chartHtml}
      ${modeNote}
    </div>`;
  thread.appendChild(wrapper);
  thread.scrollTop = thread.scrollHeight;

  if (data.chart) {
    renderChatChart(chartCanvasId, data.chart);
  }
}

function renderChatChart(canvasId, chart) {
  if (typeof Chart === 'undefined') {
    console.warn('Chart.js did not load — skipping chart render.');
    return;
  }
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const palette = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#8b5cf6'];
  new Chart(ctx, {
    type: chart.type === 'pie' ? 'pie' : chart.type === 'line' ? 'line' : 'bar',
    data: {
      labels: chart.labels,
      datasets: [{
        label: chart.title,
        data: chart.values,
        backgroundColor: palette,
        borderColor: chart.type === 'line' ? '#2563eb' : palette,
        fill: chart.type === 'line' ? false : true,
        tension: 0.3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: chart.title, font: { size: 11 } },
        legend: { display: chart.type !== 'line', labels: { boxWidth: 10, font: { size: 10 } } },
      },
    },
  });
}

function showChatError(message) {
  const el = document.getElementById('chat-error');
  if (!el) return;
  el.textContent = message;
  el.classList.remove('hidden');
}

function clearChatError() {
  const el = document.getElementById('chat-error');
  if (!el) return;
  el.classList.add('hidden');
  el.textContent = '';
}

function setChatLoading(isLoading) {
  const btn = document.getElementById('chat-send-btn');
  const label = document.getElementById('chat-send-label');
  const icon = document.getElementById('chat-send-icon');
  const input = document.getElementById('chat-input');
  if (btn) btn.disabled = isLoading;
  if (input) input.disabled = isLoading;
  if (label) label.textContent = isLoading ? 'Thinking…' : 'Ask';
  if (icon) icon.className = isLoading ? 'fa-solid fa-spinner fa-spin text-xs' : 'fa-solid fa-arrow-right text-xs';
}

// The actual network call — POST to the backend exactly matching ChatRequest/
// ChatResponse in app/schemas.py.
async function callChatApi(message) {
  const res = await fetch(`${API_BASE_URL}/api/v1/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: currentSessionId }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Backend returned ${res.status}: ${detail.slice(0, 200)}`);
  }
  return res.json();
}

// Main entry point for the chat view's input box + send button.
async function sendChatMessage(prefilledText) {
  const input = document.getElementById('chat-input');
  const text = (prefilledText !== undefined ? prefilledText : input ? input.value : '').trim();
  if (!text) return;

  clearChatError();
  appendUserMessage(text);
  if (input) input.value = '';
  setChatLoading(true);

  try {
    const data = await callChatApi(text);
    currentSessionId = data.session_id;
    appendAssistantMessage(data);
  } catch (err) {
    console.error('Chat request failed:', err);
    showChatError(
      `Couldn't reach the backend at ${API_BASE_URL}. Make sure it's running ` +
      `(uvicorn app.main:app --reload) and that this page's origin is listed in ` +
      `FRONTEND_ORIGINS in its .env. (${err.message})`
    );
  } finally {
    setChatLoading(false);
  }
}

// Wires the Home page's search bar to actually send the first message,
// instead of just switching views with the typed text going nowhere.
function askFromHome() {
  const homeInput = document.getElementById('home-input');
  const text = homeInput ? homeInput.value.trim() : '';
  switchView('chat');
  if (text) {
    sendChatMessage(text);
  }
}