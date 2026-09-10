/**
 * ZeroOne Mobility / ShareAuto - Complete Frontend-Backend Integration Engine
 * Provides Real Authentication, Role Enforcement, Live Dispatch, WebSocket and Polling
 */

const API_BASE = (window.location.protocol === 'file:' || !window.location.origin || window.location.origin === 'null')
  ? 'http://localhost:8000'
  : window.location.origin;

const WS_BASE = API_BASE.replace(/^http:\/\//i, 'ws://').replace(/^https:\/\//i, 'wss://');

class ZeroOneAPI {
  constructor() {
    this.apiBase = API_BASE;
    this.wsBase = WS_BASE;
    this.tokenKey = 'zeroone_token';
    this.userKey = 'zeroone_user';
    this.activeRideKey = 'zeroone_active_ride';
  }

  getToken() {
    return localStorage.getItem(this.tokenKey);
  }

  getUser() {
    try {
      return JSON.parse(localStorage.getItem(this.userKey));
    } catch {
      return null;
    }
  }

  setSession(token, user) {
    localStorage.setItem(this.tokenKey, token);
    localStorage.setItem(this.userKey, JSON.stringify(user));
  }

  clearSession() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
    localStorage.removeItem(this.activeRideKey);
  }

  async logout() {
    try {
      const token = this.getToken();
      if (token) {
        await fetch(`${this.apiBase}/api/auth/logout`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          }
        });
      }
    } catch (e) {}
    this.clearSession();
    window.location.replace('index.html');
  }

  async request(path, options = {}) {
    const url = `${this.apiBase}${path.startsWith('/') ? path : '/' + path}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const res = await fetch(url, { ...options, headers });
      if (res.status === 401) {
        // Expired or invalid token
        console.warn('[ZeroOne API] Token expired or unauthorized. Clearing session.');
        this.clearSession();
        if (!window.location.pathname.endsWith('index.html')) {
          window.location.href = 'index.html';
        }
        throw new Error('Session expired. Please log in again.');
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Request failed');
      }
      return await res.json();
    } catch (e) {
      console.warn(`[ZeroOne API] Request error for ${path}:`, e.message);
      throw e;
    }
  }

  get(path) {
    return this.request(path, { method: 'GET' });
  }

  post(path, data) {
    return this.request(path, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  patch(path, data) {
    return this.request(path, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  }

  delete(path) {
    return this.request(path, { method: 'DELETE' });
  }

  // WebSocket connections
  connectAdminWS(onMessage) {
    try {
      const ws = new WebSocket(`${this.wsBase}/ws/admin/live`);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (e) {}
      };
      return ws;
    } catch (e) {
      return null;
    }
  }

  connectDriverWS(driverId, onMessage) {
    try {
      const ws = new WebSocket(`${this.wsBase}/ws/driver/${driverId}`);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (e) {}
      };
      return ws;
    } catch (e) {
      return null;
    }
  }

  connectRideWS(rideId, onMessage) {
    try {
      const ws = new WebSocket(`${this.wsBase}/ws/rides/${rideId}`);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (e) {}
      };
      return ws;
    } catch (e) {
      return null;
    }
  }
}

const api = new ZeroOneAPI();

// -------------------------------------------------------------
// Universal DOM Initializer with Strict Role Enforcement
// -------------------------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
  const pagePath = window.location.pathname;

  // If on entry screen, don't perform protected page checks
  if (pagePath.endsWith('index.html') || pagePath === '/' || pagePath.endsWith('login.html')) {
    return;
  }

  const isAdminPage = pagePath.includes('admin-') || pagePath.includes('fleet-') || pagePath.includes('demand-analysis-') || pagePath.includes('live-auto-tracking');
  const isDriverPage = pagePath.includes('driver-');
  const isPassengerPage = pagePath.includes('request-shared-auto') || pagePath.includes('search-routes-stops') || pagePath.includes('ai-chatbot');
  const expectedRole = isAdminPage ? 'ADMIN' : (isDriverPage ? 'DRIVER' : (isPassengerPage ? 'PASSENGER' : ''));

  // 1. STRICT AUTH GUARD: Verify session exists
  const token = api.getToken();
  if (!token) {
    console.warn('[ZeroOne Auth] No authenticated session found. Redirecting to login.');
    window.location.replace(expectedRole ? `index.html?role=${expectedRole}` : 'index.html');
    return;
  }

  // 2. Fetch real user profile from backend
  let currentUser = null;
  try {
    currentUser = await api.get('/api/auth/me');
    const storedUser = api.getUser() || {};
    api.setSession(token, { ...storedUser, ...currentUser });
  } catch (err) {
    console.warn('[ZeroOne Auth] Failed to verify user profile. Redirecting to login.', err);
    api.clearSession();
    window.location.replace(expectedRole ? `index.html?role=${expectedRole}` : 'index.html');
    return;
  }

  // 3. STRICT ROLE-BASED ACCESS CONTROL
  const role = currentUser.role;

  if (isAdminPage && role !== 'ADMIN') {
    alert(`Access Denied: Admin privileges required. Your account role is ${role}.`);
    api.clearSession();
    window.location.replace('index.html?role=ADMIN');
    return;
  }

  if (isDriverPage && role !== 'DRIVER') {
    alert(`Access Denied: Driver portal access requires a Driver account. Your account role is ${role}.`);
    api.clearSession();
    window.location.replace('index.html?role=DRIVER');
    return;
  }

  if (isPassengerPage && role !== 'PASSENGER') {
    alert(`Access Denied: Passenger portal requires a Commuter account. Your account role is ${role}.`);
    api.clearSession();
    window.location.replace('index.html?role=PASSENGER');
    return;
  }

  // 4. Hydrate Real User Profile in Header and Sidebar
  hydrateUserProfile(currentUser);

  // 5. Inject Logout Button
  injectLogoutButton(currentUser);

  // 6. Universal Navigation Link Normalizer
  setupNavigationRouting();

  // 7. Page-Specific Functionality
  if (pagePath.includes('request-shared-auto')) {
    await initPassengerRequestPage(currentUser);
  } else if (pagePath.includes('live-auto-tracking')) {
    await initLiveTrackingPage(currentUser);
  } else if (pagePath.includes('driver-dashboard')) {
    await initDriverDashboardPage(currentUser);
  } else if (pagePath.includes('driver-earnings')) {
    await initDriverEarningsPage(currentUser);
  } else if (pagePath.includes('driver-passengers')) {
    await initDriverPassengersPage(currentUser);
  } else if (pagePath.includes('driver-profile-settings')) {
    await initDriverProfilePage(currentUser);
  } else if (pagePath.includes('admin-operations-dashboard')) {
    await initAdminDashboardPage(currentUser);
  } else if (pagePath.includes('fleet-autos-management')) {
    await initFleetManagementPage(currentUser);
  } else if (pagePath.includes('ai-chatbot')) {
    await initAIChatbotPage(currentUser);
  } else if (pagePath.includes('search-routes-stops')) {
    await initSearchRoutesPage(currentUser);
  }
});

// Prevent browser Back button from revealing authenticated state after logout
window.addEventListener('pageshow', (event) => {
  const pagePath = window.location.pathname;
  if (!pagePath.endsWith('index.html') && pagePath !== '/' && !pagePath.endsWith('login.html')) {
    if (!localStorage.getItem('zeroone_token')) {
      window.location.replace('index.html');
    }
  }
});

// Replace hardcoded mock names with real logged in user's profile
function hydrateUserProfile(user) {
  if (!user) return;

  // On Admin portal, maintain clean single two-line identity: "Fleet Controller" / "SUPER ADMIN"
  if (user.role === 'ADMIN') {
    const adminHeader = document.querySelector('header .flex.flex-col.text-right');
    if (adminHeader) {
      adminHeader.innerHTML = `
        <span class="font-body-sm text-body-sm text-on-surface font-bold leading-tight">Fleet Controller</span>
        <span class="font-label-micro text-label-micro text-on-surface-variant uppercase">SUPER ADMIN</span>
      `;
    }
    return;
  }

  const fullName = user.full_name || 'Authenticated User';
  const names = fullName.trim().split(' ');
  const initials = (names[0][0] + (names.length > 1 ? names[names.length - 1][0] : '')).toUpperCase();

  // Replace text nodes containing mock names
  const mockNames = ['Aarav Sharma', 'R. F. Sharma', 'Ramesh Sharma', 'Venkat Rao'];
  document.querySelectorAll('span, p, div, h1, h2, h3').forEach(el => {
    if (el.children.length === 0) {
      mockNames.forEach(mock => {
        if (el.textContent.trim() === mock) {
          el.textContent = fullName;
        }
      });
    }
  });

  // Replace avatar initials (e.g. AS, VR)
  document.querySelectorAll('.rounded-full').forEach(el => {
    const text = el.textContent.trim();
    if (text === 'AS' || text === 'VR' || text === 'RF') {
      el.textContent = initials;
    }
  });

  // Profile text specific selectors
  const passengerNameEl = document.querySelector('header span.text-\\[13px\\].font-bold');
  if (passengerNameEl) passengerNameEl.textContent = fullName;

  const driverNameEl = document.querySelector('span.text-slate-800.truncate');
  if (driverNameEl) driverNameEl.textContent = fullName;
}

// Inject an explicit, styled Logout button into the header
function injectLogoutButton(user) {
  const header = document.querySelector('header');
  if (!header || document.getElementById('zeroone-logout-btn')) return;

  // On Admin portal, the red Logout / Sign Out of Operations Console button already exists in the header
  if (header.querySelector('button[title*="Operations Console"], button[onclick*="api.logout()"]')) {
    return;
  }

  const logoutBtn = document.createElement('button');
  logoutBtn.id = 'zeroone-logout-btn';
  logoutBtn.title = 'Sign Out of ShareAuto';
  logoutBtn.className = 'ml-3 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-red-50 text-slate-600 hover:text-red-600 border border-slate-200 text-xs font-bold transition-all flex items-center gap-1.5 shadow-sm cursor-pointer shrink-0';
  logoutBtn.innerHTML = '<span class="material-symbols-outlined text-[16px]">logout</span><span class="hidden sm:inline">Logout</span>';
  logoutBtn.addEventListener('click', (e) => {
    e.preventDefault();
    api.logout();
  });

  // Append to right header container
  const rightContainer = header.querySelector('.flex.items-center.gap-3') || 
                         header.querySelector('.flex.items-center.gap-4') || 
                         header.querySelector('.flex.items-center.gap-3\\.5') ||
                         header.lastElementChild;
  if (rightContainer) {
    rightContainer.appendChild(logoutBtn);
  }
}

// Setup Link Handlers so sidebar navigation works across all HTML files
function setupNavigationRouting() {
  const linkMapping = {
    'operations-dashboard': 'admin-operations-dashboard.html',
    'live-auto-tracking': 'live-auto-tracking.html',
    'demand-analysis-ai': 'demand-analysis-ai.html',
    'fleet-autos': 'fleet-autos-management.html',
    'dashboard': 'driver-dashboard.html',
    'demand-ai': 'driver-demand-ai.html',
    'passengers': 'driver-passengers.html',
    'earnings': 'driver-earnings.html',
    'profile-settings': 'driver-profile-settings.html',
    'request-shared-auto': 'request-shared-auto.html',
    'search-routes-stops': 'search-routes-stops.html',
    'ai-chatbot': 'ai-chatbot.html'
  };

  document.querySelectorAll('a[data-path], nav a').forEach(a => {
    const dataPath = a.getAttribute('data-path');
    if (dataPath && linkMapping[dataPath]) {
      a.setAttribute('href', linkMapping[dataPath]);
    } else {
      const text = a.textContent.toLowerCase();
      if (text.includes('request shared auto')) a.setAttribute('href', 'request-shared-auto.html');
      else if (text.includes('search routes')) a.setAttribute('href', 'search-routes-stops.html');
      else if (text.includes('chatbot') || text.includes('ai chat')) a.setAttribute('href', 'ai-chatbot.html');
      else if (text.includes('operations dashboard')) a.setAttribute('href', 'admin-operations-dashboard.html');
      else if (text.includes('live auto tracking')) a.setAttribute('href', 'live-auto-tracking.html');
      else if (text.includes('demand analysis')) a.setAttribute('href', 'demand-analysis-ai.html');
      else if (text.includes('fleet & autos')) a.setAttribute('href', 'fleet-autos-management.html');
      else if (text.includes('dashboard')) a.setAttribute('href', 'driver-dashboard.html');
      else if (text.includes('demand ai')) a.setAttribute('href', 'driver-demand-ai.html');
      else if (text.includes('passengers')) a.setAttribute('href', 'driver-passengers.html');
      else if (text.includes('earnings')) a.setAttribute('href', 'driver-earnings.html');
      else if (text.includes('profile')) a.setAttribute('href', 'driver-profile-settings.html');
    }
  });
}

// -------------------------------------------------------------
// 1. PASSENGER REQUEST AUTO & DISPATCH FLOW
// -------------------------------------------------------------
async function initPassengerRequestPage(currentUser) {
  // Load real autos standby summary
  try {
    const summary = await api.get('/api/corridors/stations/HITEC/autos-summary');
    if (summary && summary.standby_autos_count) {
      document.querySelectorAll('body *').forEach(node => {
        if (node.nodeType === Node.TEXT_NODE && node.nodeValue.includes('autos currently on standby')) {
          node.parentElement.innerHTML = `<strong class="font-bold text-slate-900">${summary.standby_autos_count} autos</strong> currently on standby at HITEC City Metro`;
        }
      });
    }
  } catch (e) {}

  // Commuter count selector buttons (1 Person, 2 People, 3 People, 4+ Group)
  let commuterCount = 1;
  const countButtons = document.querySelectorAll('.grid.grid-cols-4 button');
  countButtons.forEach((btn, idx) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      commuterCount = idx + 1;
      countButtons.forEach(b => {
        b.className = 'py-2.5 px-3 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 font-semibold text-[13px] border border-slate-200/80 transition-all';
      });
      btn.className = 'py-2.5 px-3 rounded-xl bg-slate-900 text-white font-bold text-[13px] shadow-sm flex items-center justify-center gap-1.5 ring-2 ring-slate-900 transition-all';
    });
  });

  // DOM elements for active state
  const waitButton = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes("I'M WAITING"));
  const cancelBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Cancel Signal'));
  const idEl = Array.from(document.querySelectorAll('span')).find(s => s.textContent.includes('#ZO-'));
  const statusTag = document.querySelector('.inline-flex.items-center.gap-2.px-3.py-1\\.5.rounded-full');
  const rightColumnCard = document.querySelector('.lg\\:col-span-5');

  let activeRequestId = null;
  let activePollInterval = null;

  // Function to render active ride status
  function updatePassengerRideUI(rideData) {
    if (!rideData || !rideData.has_active) {
      if (idEl) idEl.textContent = '#ZO-READY';
      if (statusTag) {
        statusTag.innerHTML = `
          <span class="relative flex h-2 w-2">
            <span class="inline-flex rounded-full h-2 w-2 bg-slate-400"></span>
          </span>
          <span>Ready to Signal Pickup</span>
        `;
      }
      return;
    }

    activeRequestId = rideData.request_id;
    if (idEl) idEl.textContent = rideData.request_code;

    const status = rideData.status;

    if (status === 'REQUESTED') {
      if (statusTag) {
        statusTag.className = 'inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-50 border border-amber-200/80 text-[12px] font-bold text-amber-800 shadow-sm';
        statusTag.innerHTML = `
          <span class="relative flex h-2 w-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
          </span>
          <span>Signal Broadcasted • Notifying Drivers...</span>
        `;
      }
    } else if (status === 'ACCEPTED') {
      const d = rideData.driver || {};
      if (statusTag) {
        statusTag.className = 'inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200/80 text-[12px] font-bold text-emerald-800 shadow-sm';
        statusTag.innerHTML = `
          <span class="relative flex h-2 w-2">
            <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span>Driver Found: ${escapeHtml(d.name || 'Venkat Rao')}</span>
        `;
      }

      // Inject Driver Approach Card if not already present
      let driverCard = document.getElementById('passenger-driver-card');
      if (!driverCard && rightColumnCard) {
        driverCard = document.createElement('div');
        driverCard.id = 'passenger-driver-card';
        driverCard.className = 'p-5 rounded-2xl bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200/90 shadow-sm space-y-3';
        driverCard.innerHTML = `
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-bold text-lg">🛺</div>
              <div>
                <div class="text-sm font-black text-slate-900">${escapeHtml(d.name || 'Venkat Rao')}</div>
                <div class="text-[11px] text-slate-500 font-semibold">${escapeHtml(d.vehicle_code || 'AUTO-HYD-501')} • ${escapeHtml(d.plate_number || 'AP 28 TB 7721')}</div>
              </div>
            </div>
            <div class="text-right">
              <span class="text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">Approaching Bay 4</span>
              <div class="text-[11px] text-slate-400 font-medium mt-0.5">ETA ~2 mins</div>
            </div>
          </div>
          <div class="text-xs text-slate-600 bg-white/80 p-2.5 rounded-xl border border-emerald-100 flex items-center justify-between">
            <span>Model: <strong>${escapeHtml(d.model || 'Bajaj RE E-Tec (5-Seater)')}</strong></span>
            <span>Speed: <strong>${d.speed || 28} km/h</strong></span>
          </div>
        `;
        const passCard = rightColumnCard.querySelector('.bg-white.rounded-3xl');
        if (passCard) {
          passCard.parentNode.insertBefore(driverCard, passCard.nextSibling);
        }
      }
    } else if (status === 'IN_PROGRESS') {
      if (statusTag) {
        statusTag.className = 'inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-50 border border-blue-200 text-[12px] font-bold text-blue-800 shadow-sm';
        statusTag.innerHTML = `
          <span class="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
          <span>Trip In Progress to DLF Phase 2</span>
        `;
      }
    } else if (status === 'COMPLETED') {
      if (statusTag) {
        statusTag.className = 'inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-purple-50 border border-purple-200 text-[12px] font-bold text-purple-800 shadow-sm';
        statusTag.innerHTML = `
          <span class="material-symbols-outlined text-[15px]">check_circle</span>
          <span>Trip Completed • Fare ₹${rideData.fixed_fare} Paid</span>
        `;
      }
      alert('Trip completed! Thank you for commuting with ShareAuto.');
      // Remove driver approach card
      const driverCard = document.getElementById('passenger-driver-card');
      if (driverCard) driverCard.remove();
    }
  }

  // Initial check on page mount
  try {
    const active = await api.get('/api/rides/my-active');
    updatePassengerRideUI(active);
  } catch (e) {}

  // Start periodic sync polling (every 2.5 seconds)
  activePollInterval = setInterval(async () => {
    try {
      const active = await api.get('/api/rides/my-active');
      updatePassengerRideUI(active);
    } catch (e) {}
  }, 2500);

  // "I'M WAITING" Hero Broadcast Button
  if (waitButton) {
    waitButton.addEventListener('click', async (e) => {
      e.preventDefault();
      try {
        waitButton.innerHTML = '<span class="material-symbols-outlined animate-spin text-xl">progress_activity</span> Broadcasting Signal...';
        waitButton.disabled = true;

        // Fetch Corridor H1 stations
        const h1 = await api.get('/api/corridors/H1');
        const originId = h1.stations[0].id;
        const destId = h1.stations[h1.stations.length - 1].id;

        const req = await api.post('/api/rides/waiting-signal', {
          station_id: originId,
          destination_station_id: destId,
          corridor_id: h1.id,
          commuter_count: commuterCount
        });

        activeRequestId = req.id;
        if (idEl) idEl.textContent = req.request_code;

        // Connect WebSocket for real-time ride updates
        api.connectRideWS(req.id, (update) => {
          if (update && update.type === 'RIDE_UPDATE') {
            api.get('/api/rides/my-active').then(updatePassengerRideUI);
          }
        });

        waitButton.innerHTML = '<span class="text-2xl">🙋</span> <span>SIGNAL ACTIVE</span>';
        waitButton.disabled = false;

        // Re-check active state immediately
        const active = await api.get('/api/rides/my-active');
        updatePassengerRideUI(active);

      } catch (err) {
        alert('Could not broadcast signal: ' + err.message);
        waitButton.innerHTML = '<span class="text-2xl">🙋</span> <span>I\'M WAITING</span>';
        waitButton.disabled = false;
      }
    });
  }

  // Cancel Signal Button
  if (cancelBtn) {
    cancelBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      try {
        const active = await api.get('/api/rides/my-active');
        if (active && active.has_active) {
          await api.delete(`/api/rides/waiting-signal/${active.request_id}`);
          if (idEl) idEl.textContent = '#ZO-READY';
          const driverCard = document.getElementById('passenger-driver-card');
          if (driverCard) driverCard.remove();
          alert('Waiting signal cancelled.');
          updatePassengerRideUI({ has_active: false });
        } else {
          alert('No active waiting signal to cancel.');
        }
      } catch (err) {
        alert('Error cancelling: ' + err.message);
      }
    });
  }
}

// -------------------------------------------------------------
// 2. DRIVER DASHBOARD & DISPATCH RECEIVER FLOW
// -------------------------------------------------------------
async function initDriverDashboardPage(currentUser) {
  let isOnline = false;

  // 1. Load initial driver summary
  try {
    const summary = await api.get('/api/driver/dashboard-summary');
    if (summary) {
      isOnline = summary.status === 'ONLINE';
      updateDriverStatusUI(isOnline);

      // Earnings
      const earningsEl = document.querySelector('h3.text-2xl.font-extrabold') || document.querySelector('.text-2xl.font-bold');
      if (earningsEl && summary.today_earnings !== undefined) {
        earningsEl.textContent = `₹${summary.today_earnings.toFixed(2)}`;
      }
    }
  } catch (e) {}

  function updateDriverStatusUI(online) {
    isOnline = online;
    const pill = document.querySelector('header .bg-emerald-50') || document.querySelector('header span.text-emerald-700');
    if (pill) {
      if (online) {
        pill.parentElement.className = 'flex items-center gap-2 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-full text-xs font-medium text-emerald-700';
        pill.parentElement.innerHTML = `
          <span class="relative flex h-2 w-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span>Online • Receiving Requests</span>
        `;
      } else {
        pill.parentElement.className = 'flex items-center gap-2 bg-slate-100 border border-slate-300 px-3 py-1.5 rounded-full text-xs font-medium text-slate-600';
        pill.parentElement.innerHTML = `
          <span class="w-2 h-2 rounded-full bg-slate-400"></span>
          <span>Offline • Standby</span>
        `;
      }
    }
  }

  // 2. Online / Offline Toggle Button
  const toggleBtn = document.querySelector('button[role="switch"]') || 
                    Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('ONLINE') || b.textContent.includes('Go Offline') || b.textContent.includes('Offline'));
  if (toggleBtn) {
    toggleBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      try {
        const nextState = !isOnline;
        const res = await api.patch('/api/driver/status', { is_online: nextState });
        updateDriverStatusUI(res.is_online);
        alert(`Your pilot status is now: ${res.is_online ? 'ONLINE (Receiving Requests)' : 'OFFLINE'}`);
      } catch (err) {
        alert('Could not update status: ' + err.message);
      }
    });
  }

  // 3. Driver Dispatch Request Queue & Modal Handlers
  const mainContent = document.querySelector('main');

  function renderIncomingRequestModal(request) {
    let modal = document.getElementById('driver-request-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'driver-request-modal';
      modal.className = 'fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4';
      document.body.appendChild(modal);
    }

    modal.innerHTML = `
      <div class="bg-white rounded-3xl p-6 sm:p-7 max-w-md w-full shadow-2xl border border-slate-200 space-y-5 animate-in fade-in zoom-in duration-200">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <div class="w-9 h-9 rounded-xl bg-amber-500 text-slate-950 flex items-center justify-center font-bold text-lg">🙋</div>
            <div>
              <span class="text-xs font-bold text-amber-600 uppercase tracking-wider block">Corridor Alert</span>
              <h3 class="text-lg font-black text-slate-900 leading-tight">NEW RIDE REQUEST</h3>
            </div>
          </div>
          <span class="px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 font-mono text-xs font-bold">${escapeHtml(request.request_code)}</span>
        </div>

        <div class="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2.5 text-xs text-slate-700">
          <div class="flex items-center justify-between">
            <span class="font-semibold text-slate-500">Passenger:</span>
            <span class="font-bold text-slate-900 text-sm">${escapeHtml(request.passenger_name)}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="font-semibold text-slate-500">Pickup Station:</span>
            <span class="font-bold text-slate-900">${escapeHtml(request.pickup)} (${escapeHtml(request.bay)})</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="font-semibold text-slate-500">Destination:</span>
            <span class="font-bold text-slate-900">${escapeHtml(request.destination)}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="font-semibold text-slate-500">Seats Requested:</span>
            <span class="font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-full">${request.commuters} Commuter${request.commuters > 1 ? 's' : ''}</span>
          </div>
          <div class="flex items-center justify-between border-t border-slate-200/80 pt-2">
            <span class="font-semibold text-slate-500">Fixed Fare:</span>
            <span class="font-black text-emerald-700 text-base">₹${request.fixed_fare * request.commuters}</span>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3 pt-1">
          <button onclick="rejectRide('${request.id}')" class="py-3 px-4 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs transition-colors cursor-pointer">
            Decline
          </button>
          <button onclick="acceptRide('${request.id}')" class="py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-bold text-xs shadow-lg shadow-emerald-600/20 transition-all flex items-center justify-center gap-1.5 cursor-pointer">
            <span class="material-symbols-outlined text-base">check</span> Accept Ride
          </button>
        </div>
      </div>
    `;
    modal.classList.remove('hidden');
  }

  function renderActiveTripBanner(activeRide) {
    let banner = document.getElementById('driver-active-trip-card');
    if (!activeRide) {
      if (banner) banner.remove();
      return;
    }

    if (!banner && mainContent) {
      banner = document.createElement('div');
      banner.id = 'driver-active-trip-card';
      banner.className = 'p-6 rounded-3xl bg-slate-900 text-white shadow-xl space-y-4';
      mainContent.insertBefore(banner, mainContent.firstChild);
    }

    const isOngoing = activeRide.status === 'IN_PROGRESS';

    banner.innerHTML = `
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-2xl bg-amber-400 text-slate-950 flex items-center justify-center font-bold text-xl">🛺</div>
          <div>
            <span class="text-[11px] font-bold text-amber-400 uppercase tracking-wider block">Active Corridor Trip</span>
            <h2 class="text-base font-black text-white">${escapeHtml(activeRide.pickup)} ➔ ${escapeHtml(activeRide.destination)}</h2>
          </div>
        </div>
        <span class="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${isOngoing ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'}">
          ${isOngoing ? 'Trip In Progress' : 'Passenger Boarding'}
        </span>
      </div>

      <div class="grid grid-cols-3 gap-3 p-3.5 rounded-2xl bg-slate-800/80 border border-slate-700/80 text-xs">
        <div>
          <span class="text-slate-400 block text-[10px] uppercase font-bold">Passenger</span>
          <span class="font-bold text-white">${escapeHtml(activeRide.passenger_name)}</span>
        </div>
        <div>
          <span class="text-slate-400 block text-[10px] uppercase font-bold">Seats Reserved</span>
          <span class="font-bold text-white">${activeRide.commuters} Person</span>
        </div>
        <div>
          <span class="text-slate-400 block text-[10px] uppercase font-bold">Total Fare</span>
          <span class="font-bold text-emerald-400">₹${activeRide.fixed_fare * activeRide.commuters}</span>
        </div>
      </div>

      <div class="flex items-center gap-3 pt-1">
        ${!isOngoing ? `
          <button onclick="startTrip('${activeRide.id}')" class="flex-1 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs transition-colors flex items-center justify-center gap-1.5 cursor-pointer">
            <span class="material-symbols-outlined text-base">directions_car</span> Start Trip
          </button>
        ` : `
          <button onclick="completeTrip('${activeRide.id}')" class="flex-1 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs transition-colors flex items-center justify-center gap-1.5 cursor-pointer shadow-lg shadow-emerald-600/20">
            <span class="material-symbols-outlined text-base">check_circle</span> Complete Trip & Collect Fare
          </button>
        `}
      </div>
    `;
  }

  // Global action handlers for driver modal
  window.acceptRide = async function(requestId) {
    try {
      const res = await api.post(`/api/rides/${requestId}/accept`, {});
      const modal = document.getElementById('driver-request-modal');
      if (modal) modal.classList.add('hidden');
      alert('Ride Accepted! Passenger notified that you are approaching.');
      fetchDriverRequests();
    } catch (err) {
      alert('Error accepting ride: ' + err.message);
    }
  };

  window.rejectRide = async function(requestId) {
    try {
      await api.post(`/api/rides/${requestId}/reject`, {});
      const modal = document.getElementById('driver-request-modal');
      if (modal) modal.classList.add('hidden');
    } catch (err) {}
  };

  window.startTrip = async function(requestId) {
    try {
      await api.post(`/api/rides/${requestId}/start`, {});
      alert('Trip Started! Navigating along corridor.');
      fetchDriverRequests();
    } catch (err) {
      alert('Error starting trip: ' + err.message);
    }
  };

  window.completeTrip = async function(requestId) {
    try {
      const res = await api.post(`/api/rides/${requestId}/complete`, {});
      alert(`Trip Completed! Collected ₹${res.fare_collected || 25}. Auto reset to ONLINE.`);
      fetchDriverRequests();
      // Reload earnings
      const summary = await api.get('/api/driver/dashboard-summary');
      const earningsEl = document.querySelector('h3.text-2xl.font-extrabold') || document.querySelector('.text-2xl.font-bold');
      if (earningsEl && summary.today_earnings) {
        earningsEl.textContent = `₹${summary.today_earnings.toFixed(2)}`;
      }
    } catch (err) {
      alert('Error completing trip: ' + err.message);
    }
  };

  // Poll driver requests periodically (every 2.5s)
  async function fetchDriverRequests() {
    try {
      const data = await api.get('/api/rides/driver-requests');
      if (data) {
        renderActiveTripBanner(data.active_ride);
        if (data.pending_requests && data.pending_requests.length > 0 && !data.active_ride) {
          renderIncomingRequestModal(data.pending_requests[0]);
        }
      }
    } catch (e) {}
  }

  fetchDriverRequests();
  setInterval(fetchDriverRequests, 2500);

  // Connect Driver WebSocket
  const driverProfile = await api.get('/api/driver/profile').catch(() => null);
  if (driverProfile) {
    api.connectDriverWS(currentUser.id, (msg) => {
      if (msg && msg.type === 'NEW_RIDE_REQUEST') {
        renderIncomingRequestModal(msg.request);
      }
    });
  }
}

// -------------------------------------------------------------
// 3. LIVE AUTO CORRIDOR TRACKING (ADMIN)
// -------------------------------------------------------------
async function initLiveTrackingPage(currentUser) {
  if (typeof window.inspectVehicle === 'function') {
    const originalInspect = window.inspectVehicle;
    window.inspectVehicle = async function(vehicleKey) {
      try {
        const data = await api.get(`/api/admin/vehicles/${vehicleKey}/inspect`);
        if (data && window.vehicleDatabase) {
          window.vehicleDatabase[vehicleKey] = data;
        }
      } catch (e) {}
      originalInspect(vehicleKey);
    };
  }

  // Subscribe to live telemetry updates over WebSocket
  api.connectAdminWS((data) => {
    if (data.type === 'TELEMETRY_UPDATE') {
      const activeCount = data.vehicles ? data.vehicles.length : 14;
      document.querySelectorAll('span').forEach(s => {
        if (s.textContent.includes('Active Autos')) {
          s.textContent = `${activeCount} Active Autos`;
        }
      });
    }
  });
}

// -------------------------------------------------------------
// 4. DRIVER EARNINGS
// -------------------------------------------------------------
async function initDriverEarningsPage(currentUser) {
  try {
    const data = await api.get('/api/driver/earnings/summary');
    console.log('[ZeroOne API] Driver Earnings loaded:', data);
  } catch (e) {}
}

// -------------------------------------------------------------
// 5. DRIVER PASSENGERS & STATIONS
// -------------------------------------------------------------
async function initDriverPassengersPage(currentUser) {
  try {
    const stations = await api.get('/api/corridors/stations/demand-staging/nodes');
    console.log('[ZeroOne API] Demand stations loaded:', stations.length);
  } catch (e) {}
}

// -------------------------------------------------------------
// 6. DRIVER PROFILE & SETTINGS
// -------------------------------------------------------------
async function initDriverProfilePage(currentUser) {
  try {
    const profile = await api.get('/api/driver/profile');
    console.log('[ZeroOne API] Driver Profile loaded:', profile.pilot_name);
  } catch (e) {}
}

// -------------------------------------------------------------
// 7. ADMIN OPERATIONS DASHBOARD
// -------------------------------------------------------------
async function initAdminDashboardPage(currentUser) {
  try {
    const kpis = await api.get('/api/admin/dashboard/kpis');
    const feed = await api.get('/api/admin/dashboard/live-feed');
    console.log('[ZeroOne API] Admin KPIs loaded:', kpis);
  } catch (e) {}

  api.connectAdminWS((data) => {});
}

// -------------------------------------------------------------
// 8. FLEET & AUTOS MANAGEMENT
// -------------------------------------------------------------
async function initFleetManagementPage(currentUser) {
  try {
    const pending = await api.get('/api/admin/drivers/pending-approvals');
    document.querySelectorAll('button').forEach(btn => {
      if (btn.textContent.includes('Approve Pilot') || btn.textContent.includes('Approve')) {
        btn.addEventListener('click', async (e) => {
          e.preventDefault();
          if (pending.length > 0) {
            try {
              await api.post(`/api/admin/drivers/${pending[0].id}/approve`);
              btn.textContent = 'Approved ✓';
              btn.disabled = true;
              alert('Driver KYC & Commercial Badge Approved!');
            } catch (err) {
              alert('Approval failed: ' + err.message);
            }
          }
        });
      }
    });
  } catch (e) {}
}

// -------------------------------------------------------------
// 9. AI CHATBOT PAGE
// -------------------------------------------------------------
async function initAIChatbotPage(currentUser) {
  const chatInput = document.querySelector('input[type="text"]') || document.querySelector('input[placeholder*="Ask"]');
  const sendButton = Array.from(document.querySelectorAll('button')).find(b => b.querySelector('span') && b.querySelector('span').textContent.includes('send')) || document.querySelector('button[type="submit"]');
  const chatMessagesContainer = document.querySelector('.overflow-y-auto') || document.querySelector('main');

  async function handleSend(query) {
    if (!query || !query.trim()) return;
    const userText = query.trim();
    if (chatInput) chatInput.value = '';

    appendUserBubble(userText);

    try {
      const res = await api.post('/api/chat/message', { message: userText });
      appendBotBubble(res.response, res.card_data, res.suggestions);
    } catch (err) {
      appendBotBubble('Apologies, could not connect to ZeroOne Transit Assistant: ' + err.message);
    }
  }

  function appendUserBubble(text) {
    if (!chatMessagesContainer) return;
    const div = document.createElement('div');
    div.className = 'flex items-start justify-end gap-3 my-4';
    div.innerHTML = `
      <div class="bg-slate-900 text-white p-4 rounded-2xl max-w-lg shadow-sm text-[13.5px]">
        <p>${escapeHtml(text)}</p>
      </div>
      <div class="w-8 h-8 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-bold text-xs shrink-0">
        ${escapeHtml(currentUser.full_name.substring(0, 2).toUpperCase())}
      </div>
    `;
    chatMessagesContainer.appendChild(div);
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
  }

  function appendBotBubble(botText, cardData, suggestions) {
    if (!chatMessagesContainer) return;
    const div = document.createElement('div');
    div.className = 'flex items-start gap-3 my-4';
    
    let cardHtml = '';
    if (cardData) {
      cardHtml = `
        <div class="mt-3 p-3 bg-white border border-slate-200 rounded-xl shadow-xs text-xs space-y-1">
          <div class="font-bold text-slate-900">${escapeHtml(cardData.corridor_name || '')}</div>
          <div class="text-slate-600">Fixed Fare: <strong class="text-emerald-700">₹${cardData.fixed_fare}</strong> • Headway: ${cardData.headway}</div>
          <div class="text-[11px] text-slate-500">${cardData.stops ? cardData.stops.join(' ➔ ') : ''}</div>
        </div>
      `;
    }

    let suggHtml = '';
    if (suggestions && suggestions.length) {
      suggHtml = `<div class="mt-3 flex flex-wrap gap-2">` + 
        suggestions.map(s => `<button class="px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 text-[11px] font-semibold hover:bg-indigo-100 transition-colors" onclick="window.sendChatSuggestion('${escapeHtml(s)}')">${escapeHtml(s)}</button>`).join('') +
        `</div>`;
    }

    div.innerHTML = `
      <div class="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0">AI</div>
      <div class="bg-slate-100 border border-slate-200/80 text-slate-800 p-4 rounded-2xl max-w-lg shadow-sm text-[13.5px] leading-relaxed">
        <p>${escapeHtml(botText)}</p>
        ${cardHtml}
        ${suggHtml}
      </div>
    `;
    chatMessagesContainer.appendChild(div);
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
  }

  window.sendChatSuggestion = function(text) {
    handleSend(text);
  };

  if (sendButton && chatInput) {
    sendButton.addEventListener('click', (e) => {
      e.preventDefault();
      handleSend(chatInput.value);
    });
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleSend(chatInput.value);
      }
    });
  }

  document.querySelectorAll('button').forEach(btn => {
    const txt = btn.textContent.trim();
    if (txt.startsWith('Show ') || txt.includes('HITEC') || txt.includes('Schedule') || txt.includes('Fare')) {
      btn.addEventListener('click', (e) => {
        if (!btn.closest('nav') && !btn.closest('header')) {
          e.preventDefault();
          handleSend(txt);
        }
      });
    }
  });
}

// -------------------------------------------------------------
// 10. SEARCH ROUTES & STOPS
// -------------------------------------------------------------
async function initSearchRoutesPage(currentUser) {
  try {
    const corridors = await api.get('/api/corridors');
    console.log('[ZeroOne API] Search page loaded corridors:', corridors.length);
  } catch (e) {}
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
