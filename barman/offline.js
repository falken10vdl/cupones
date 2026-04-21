/* ============================================================
   offline.js – IndexedDB wrapper for offline coupon storage
   ============================================================ */

const DB_NAME = 'barman-coupons';
const DB_VERSION = 1;

let _db = null;

/**
 * Open (or create) the IndexedDB database.
 * @returns {Promise<IDBDatabase>}
 */
function initDB() {
  if (_db) return Promise.resolve(_db);

  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = event => {
      const db = event.target.result;

      // ── coupons store ──────────────────────────────────────
      if (!db.objectStoreNames.contains('coupons')) {
        const couponStore = db.createObjectStore('coupons', { keyPath: 'code' });
        couponStore.createIndex('event_id',            'event_id',            { unique: false });
        couponStore.createIndex('assigned_barman_id',  'assigned_barman_id',  { unique: false });
        couponStore.createIndex('redeemed_locally',    'redeemed_locally',    { unique: false });
      }

      // ── pending_sync store ─────────────────────────────────
      if (!db.objectStoreNames.contains('pending_sync')) {
        db.createObjectStore('pending_sync', {
          keyPath:       'id',
          autoIncrement: true
        });
      }
    };

    request.onsuccess = event => {
      _db = event.target.result;
      resolve(_db);
    };

    request.onerror = event => {
      reject(event.target.error);
    };
  });
}

/**
 * Clear all coupons and store a fresh batch.
 * @param {Array} coupons
 * @returns {Promise<void>}
 */
function storeCoupons(coupons) {
  return initDB().then(db => {
    return new Promise((resolve, reject) => {
      const tx = db.transaction('coupons', 'readwrite');
      const store = tx.objectStore('coupons');

      store.clear();

      for (const coupon of coupons) {
        store.put({
          code:                 coupon.code,
          event_id:             coupon.event_id,
          holder_name:          coupon.holder_name,
          holder_email:         coupon.holder_email  || '',
          assigned_barman_id:   coupon.assigned_barman_id,
          assigned_barman_name: coupon.assigned_barman_name || '',
          hmac_signature:       coupon.hmac_signature || '',
          redeemed_at:          coupon.redeemed_at    || null,
          redeemed_locally:     0
        });
      }

      tx.oncomplete = () => resolve();
      tx.onerror    = e  => reject(e.target.error);
    });
  });
}

/**
 * Get a single coupon by code.
 * @param {string} code
 * @returns {Promise<Object|null>}
 */
function getCoupon(code) {
  return initDB().then(db => {
    return new Promise((resolve, reject) => {
      const tx      = db.transaction('coupons', 'readonly');
      const request = tx.objectStore('coupons').get(code);

      request.onsuccess = e => resolve(e.target.result || null);
      request.onerror   = e => reject(e.target.error);
    });
  });
}

/**
 * Mark a coupon as locally redeemed and add it to pending_sync.
 * @param {string} code
 * @param {string} timestamp  ISO string
 * @param {number} barmanId
 * @returns {Promise<void>}
 */
function markRedeemed(code, timestamp, barmanId) {
  return initDB().then(db => {
    return new Promise((resolve, reject) => {
      const tx          = db.transaction(['coupons', 'pending_sync'], 'readwrite');
      const couponStore = tx.objectStore('coupons');
      const syncStore   = tx.objectStore('pending_sync');

      const getReq = couponStore.get(code);

      getReq.onsuccess = e => {
        const coupon = e.target.result;
        if (!coupon) {
          reject(new Error('Coupon not found: ' + code));
          return;
        }

        coupon.redeemed_locally = 1;
        coupon.redeemed_at      = timestamp;
        couponStore.put(coupon);

        syncStore.add({
          code:        code,
          redeemed_at: timestamp,
          barman_id:   barmanId
        });
      };

      tx.oncomplete = () => resolve();
      tx.onerror    = e  => reject(e.target.error);
    });
  });
}

/**
 * Mark a coupon as redeemed in the local cache without adding to pending_sync.
 * Used after a successful online redemption so stats stay accurate.
 */
function markRedeemedOnline(code, timestamp) {
  return initDB().then(db => {
    return new Promise((resolve, reject) => {
      const tx    = db.transaction('coupons', 'readwrite');
      const store = tx.objectStore('coupons');
      const req   = store.get(code);
      req.onsuccess = e => {
        const coupon = e.target.result;
        if (!coupon) { resolve(); return; }
        coupon.redeemed_locally = 1;
        coupon.redeemed_at      = timestamp;
        store.put(coupon);
      };
      tx.oncomplete = () => resolve();
      tx.onerror    = e  => reject(e.target.error);
    });
  });
}

/**
 * Return all records waiting to be synced to the server.
 * @returns {Promise<Array>}
 */
function getPendingSync() {
  return initDB().then(db => {
    return new Promise((resolve, reject) => {
      const tx      = db.transaction('pending_sync', 'readonly');
      const request = tx.objectStore('pending_sync').getAll();

      request.onsuccess = e => resolve(e.target.result);
      request.onerror   = e => reject(e.target.error);
    });
  });
}

/**
 * Remove all pending-sync records (call after a successful server sync).
 * @returns {Promise<void>}
 */
function clearPendingSync() {
  return initDB().then(db => {
    return new Promise((resolve, reject) => {
      const tx      = db.transaction('pending_sync', 'readwrite');
      const request = tx.objectStore('pending_sync').clear();

      request.onsuccess = () => resolve();
      request.onerror   = e  => reject(e.target.error);
    });
  });
}

/**
 * Get summary statistics from the local DB.
 * @returns {Promise<{total: number, redeemed: number, pending_sync: number}>}
 */
function getStats() {
  return initDB().then(db => {
    return new Promise((resolve, reject) => {
      const stats = { total: 0, redeemed: 0, pending_sync: 0 };
      let pending = 3;

      function done() {
        pending--;
        if (pending === 0) resolve(stats);
      }

      // total coupons
      const tx1 = db.transaction('coupons', 'readonly');
      tx1.objectStore('coupons').count().onsuccess = e => {
        stats.total = e.target.result;
        done();
      };

      // redeemed (locally or server-confirmed)
      const tx2  = db.transaction('coupons', 'readonly');
      const idx  = tx2.objectStore('coupons').index('redeemed_locally');
      idx.count(IDBKeyRange.only(1)).onsuccess = e => {
        stats.redeemed = e.target.result;
        done();
      };

      // pending sync
      const tx3 = db.transaction('pending_sync', 'readonly');
      tx3.objectStore('pending_sync').count().onsuccess = e => {
        stats.pending_sync = e.target.result;
        done();
      };

      // shared error handler
      [tx1, tx2, tx3].forEach(tx => {
        tx.onerror = e => reject(e.target.error);
      });
    });
  });
}
