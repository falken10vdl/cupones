/* ============================================================
   app.js – Main application logic for Barman PWA
   ============================================================ */

const API_BASE = window.location.origin;

let currentBarman = null; // { id, name, pin, event_id, event_name }
let isOnline      = navigator.onLine;
let pingInterval  = null;
let resultTimeout = null;
let isScannerOpen = false;

// ── Boot ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await initDB();
  tryAutoLogin();
  setupNetworkListeners();
  startPing();
});

// ── Auto-login from localStorage ─────────────────────────────
function tryAutoLogin() {
  const stored = localStorage.getItem('barman_session');
  if (stored) {
    try {
      currentBarman = JSON.parse(stored);
      showMain();
      refreshStats();
    } catch {
      localStorage.removeItem('barman_session');
      showLogin();
    }
  } else {
    showLogin();
  }
}

// ── Screen helpers ───────────────────────────────────────────
function showLogin() {
  document.getElementById('screen-login').style.display  = 'flex';
  document.getElementById('screen-main').style.display   = 'none';
  document.getElementById('overlay-scanner').style.display = 'none';
  document.getElementById('overlay-result').style.display  = 'none';
}

function showMain() {
  document.getElementById('screen-login').style.display  = 'none';
  document.getElementById('screen-main').style.display   = 'flex';
  document.getElementById('overlay-scanner').style.display = 'none';
  document.getElementById('overlay-result').style.display  = 'none';

  document.getElementById('barman-name').textContent  = currentBarman.name;
  document.getElementById('event-name').textContent   = currentBarman.event_name;
  updateOnlineIndicator();
  refreshStats();
}

// ── Login ─────────────────────────────────────────────────────
async function doLogin() {
  const eventId = document.getElementById('login-event-id').value.trim();
  const pin     = document.getElementById('login-pin').value.trim();
  const btn     = document.getElementById('login-btn');
  const errEl   = document.getElementById('login-error');

  errEl.textContent = '';

  if (!eventId || !pin) {
    errEl.textContent = 'Completa todos los campos.';
    return;
  }
  if (pin.length < 4 || pin.length > 6) {
    errEl.textContent = 'El PIN debe tener 4–6 dígitos.';
    return;
  }

  btn.disabled     = true;
  btn.textContent  = 'Conectando…';

  try {
    const res  = await fetch(`${API_BASE}/api/barman/login`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ event_id: Number(eventId), pin })
    });

    const data = await res.json();

    if (!res.ok) {
      errEl.textContent = data.message || 'Credenciales inválidas.';
      return;
    }

    currentBarman = {
      id:         data.barman_id,
      name:       data.barman_name,
      pin:        pin,
      event_id:   data.event_id,
      event_name: data.event_name
    };

    localStorage.setItem('barman_session', JSON.stringify(currentBarman));

    // Store HMAC key if provided
    if (data.hmac_key) {
      localStorage.setItem('barman_hmac_key', data.hmac_key);
    }

    showMain();
    // Auto-fetch coupon cache on first login
    await refreshCouponCache();

  } catch (err) {
    errEl.textContent = 'Sin conexión. Intenta de nuevo.';
  } finally {
    btn.disabled    = false;
    btn.textContent = 'ENTRAR';
  }
}

// ── Logout ────────────────────────────────────────────────────
function doLogout() {
  localStorage.removeItem('barman_session');
  currentBarman = null;
  showLogin();
}

// ── Network detection ─────────────────────────────────────────
function setupNetworkListeners() {
  window.addEventListener('online',  () => setOnline(true));
  window.addEventListener('offline', () => setOnline(false));
}

function startPing() {
  // Initial check
  pingServer();
  pingInterval = setInterval(pingServer, 10000);
}

async function pingServer() {
  try {
    const res = await fetch(`${API_BASE}/api/events`, {
      method:  'GET',
      cache:   'no-store',
      signal:  AbortSignal.timeout(4000)
    });
    setOnline(res.ok || res.status < 500);
  } catch {
    setOnline(false);
  }
}

function setOnline(online) {
  isOnline = online;
  updateOnlineIndicator();
}

function updateOnlineIndicator() {
  const dot    = document.getElementById('status-dot');
  const label  = document.getElementById('status-label');
  if (!dot) return;

  if (isOnline) {
    dot.style.background  = '#4ecca3';
    label.textContent     = 'En línea';
  } else {
    dot.style.background  = '#e94560';
    label.textContent     = 'Sin conexión';
  }
}

// ── Stats ─────────────────────────────────────────────────────
async function refreshStats() {
  try {
    const stats = await getStats();

    document.getElementById('stat-processed').textContent = stats.redeemed;
    document.getElementById('stat-pending').textContent   = stats.pending_sync;

    const syncBtn = document.getElementById('btn-sync');
    if (syncBtn) {
      syncBtn.style.display = stats.pending_sync > 0 ? 'block' : 'none';
    }
  } catch (e) {
    console.error('refreshStats error', e);
  }
}

// ── Scanner ───────────────────────────────────────────────────
async function openScanner() {
  if (isScannerOpen) return;

  document.getElementById('overlay-scanner').style.display = 'flex';
  isScannerOpen = true;

  initScanner(onQrScanned);

  try {
    await startScanning();
  } catch (err) {
    isScannerOpen = false;
    document.getElementById('overlay-scanner').style.display = 'none';
    showResult({
      type:    'INVALID',
      message: '❌ No se pudo acceder a la cámara.\n' + (err.message || err)
    });
  }
}

async function closeScanner() {
  await stopScanning();
  document.getElementById('overlay-scanner').style.display = 'none';
  isScannerOpen = false;
}

// Called once per unique QR decode
let lastScannedCode = '';
let scanCooldown    = false;

async function onQrScanned(code) {
  if (scanCooldown || code === lastScannedCode) return;

  lastScannedCode = code;
  scanCooldown    = true;
  setTimeout(() => { scanCooldown = false; }, 3000);

  await closeScanner();

  if (isOnline) {
    await processOnline(code);
  } else {
    await processOffline(code);
  }

  refreshStats();
}

// ── Online processing ─────────────────────────────────────────
async function processOnline(code) {
  try {
    const res  = await fetch(`${API_BASE}/api/redeem`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        code,
        barman_id:  currentBarman.id,
        barman_pin: currentBarman.pin
      })
    });

    const data = await res.json();

    switch (data.status) {
      case 'SUCCESS':
        showResult({
          type:    'SUCCESS',
          message: `✅ Cupón válido\n${data.holder_name}\n¡Servido!`
        });
        break;

      case 'ALREADY_USED':
        showResult({
          type:    'ALREADY_USED',
          message: `⚠️ Cupón ya utilizado\n${data.redeemed_at ? formatDate(data.redeemed_at) : ''}\npor ${data.redeemed_by || 'otro barman'}`
        });
        break;

      case 'INVALID':
      default:
        showResult({
          type:    'INVALID',
          message: `❌ Cupón no válido\n${data.message || ''}`
        });
        break;
    }
  } catch (err) {
    // Network failed mid-scan – fall back to offline
    console.warn('Online redeem failed, falling back to offline', err);
    setOnline(false);
    await processOffline(code);
  }
}

// ── Offline processing ────────────────────────────────────────
async function processOffline(code) {
  const coupon = await getCoupon(code);

  if (!coupon) {
    showResult({
      type:    'INVALID',
      message: '❌ No se puede verificar offline.\nCupón no asignado a este barman.'
    });
    return;
  }

  // Verify HMAC signature
  const hmacKey = localStorage.getItem('barman_hmac_key');
  if (hmacKey && coupon.hmac_signature) {
    const valid = await verifyHmac(code, coupon.hmac_signature, hmacKey);
    if (!valid) {
      showResult({
        type:    'INVALID',
        message: '❌ Firma del cupón inválida.\nPosible falsificación.'
      });
      return;
    }
  }

  // Check barman assignment
  if (coupon.assigned_barman_id !== currentBarman.id) {
    showResult({
      type:    'WRONG_BARMAN',
      message: `⚠️ Este cupón pertenece al barman ${coupon.assigned_barman_name}.\nNo puedes procesarlo offline.`
    });
    return;
  }

  // Already redeemed?
  if (coupon.redeemed_at || coupon.redeemed_locally) {
    showResult({
      type:    'ALREADY_USED',
      message: `⚠️ Cupón ya utilizado\n${coupon.redeemed_at ? formatDate(coupon.redeemed_at) : 'fecha desconocida'}`
    });
    return;
  }

  // Mark redeemed locally
  const timestamp = new Date().toISOString();
  await markRedeemed(code, timestamp, currentBarman.id);

  showResult({
    type:    'SUCCESS',
    message: `✅ Cupón válido (offline)\n${coupon.holder_name}\n¡Servido!`
  });
}

// ── HMAC verification (Web Crypto API) ───────────────────────
async function verifyHmac(code, signature, keyString) {
  try {
    const enc        = new TextEncoder();
    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      enc.encode(keyString),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['verify']
    );

    const sigBytes = hexToBytes(signature);
    return await crypto.subtle.verify(
      'HMAC',
      keyMaterial,
      sigBytes,
      enc.encode(code)
    );
  } catch (e) {
    console.error('HMAC verify error', e);
    return false;
  }
}

function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
  }
  return bytes;
}

// ── Result overlay ────────────────────────────────────────────
const RESULT_COLORS = {
  SUCCESS:      '#4ecca3',
  ALREADY_USED: '#f39c12',
  INVALID:      '#e94560',
  WRONG_BARMAN: '#f1c40f'
};

function showResult({ type, message }) {
  const overlay = document.getElementById('overlay-result');
  const box     = document.getElementById('result-box');
  const msgEl   = document.getElementById('result-message');

  msgEl.textContent          = message;
  box.style.borderColor      = RESULT_COLORS[type] || '#eee';
  box.style.boxShadow        = `0 0 30px ${RESULT_COLORS[type] || '#eee'}55`;
  msgEl.style.color          = RESULT_COLORS[type] || '#eee';

  overlay.style.display = 'flex';

  // Clear previous timeout
  if (resultTimeout) clearTimeout(resultTimeout);
  resultTimeout = setTimeout(dismissResult, 3000);
}

function dismissResult() {
  if (resultTimeout) clearTimeout(resultTimeout);
  document.getElementById('overlay-result').style.display = 'none';
}

// ── Sync ──────────────────────────────────────────────────────
async function doSync() {
  const btn = document.getElementById('btn-sync');
  if (btn) { btn.disabled = true; btn.textContent = 'Sincronizando…'; }

  try {
    const pending = await getPendingSync();

    if (pending.length === 0) {
      alert('No hay cupones pendientes de sincronizar.');
      return;
    }

    const res  = await fetch(`${API_BASE}/api/sync`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        barman_id:   currentBarman.id,
        barman_pin:  currentBarman.pin,
        redemptions: pending
      })
    });

    const data = await res.json();

    if (res.ok) {
      await clearPendingSync();

      // Handle conflicts reported by the server
      if (data.conflicts && data.conflicts.length > 0) {
        const names = data.conflicts.map(c => c.code).join('\n');
        alert(`Sincronización completa.\n\nConflictos (ya registrados por otro barman):\n${names}`);
      } else {
        alert(`✅ Sincronización exitosa.\n${pending.length} cupón(es) registrado(s).`);
      }
    } else {
      alert(`Error al sincronizar: ${data.message || 'Error desconocido'}`);
    }
  } catch (err) {
    alert('Sin conexión. No se pudo sincronizar.');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'SINCRONIZAR'; }
    refreshStats();
  }
}

// ── Refresh coupon cache ──────────────────────────────────────
async function refreshCouponCache() {
  const btn = document.getElementById('btn-refresh');
  if (btn) { btn.disabled = true; btn.textContent = 'Actualizando…'; }

  try {
    const res = await fetch(
      `${API_BASE}/api/barman/${currentBarman.id}/coupons?pin=${encodeURIComponent(currentBarman.pin)}`
    );

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      alert(`Error al actualizar cupones: ${data.message || res.status}`);
      return;
    }

    const data = await res.json();

    // Store HMAC key if returned
    if (data.hmac_key) {
      localStorage.setItem('barman_hmac_key', data.hmac_key);
    }

    await storeCoupons(data.coupons || []);
    alert(`✅ Cache actualizado.\n${(data.coupons || []).length} cupón(es) disponibles offline.`);
    refreshStats();

  } catch (err) {
    alert('Sin conexión. No se pudo actualizar el cache de cupones.');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'ACTUALIZAR CUPONES'; }
  }
}

// ── Utilities ─────────────────────────────────────────────────
function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString('es-ES', {
      day:    '2-digit',
      month:  '2-digit',
      year:   'numeric',
      hour:   '2-digit',
      minute: '2-digit'
    });
  } catch {
    return iso;
  }
}
