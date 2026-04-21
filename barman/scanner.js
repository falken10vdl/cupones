/* ============================================================
   scanner.js – QR Scanner wrapper using html5-qrcode
   ============================================================ */

let html5QrScanner = null;
let _onScanSuccess  = null;

/**
 * Initialise the scanner with a callback.
 * @param {function(string): void} onScanSuccess  Called with the decoded QR string.
 */
function initScanner(onScanSuccess) {
  _onScanSuccess = onScanSuccess;
}

/**
 * Start the camera and begin scanning.
 * Renders into the element with id="qr-reader".
 * @returns {Promise<void>}
 */
function startScanning() {
  return new Promise((resolve, reject) => {
    if (!window.Html5Qrcode) {
      reject(new Error('html5-qrcode library not loaded'));
      return;
    }

    // Stop any running instance first
    stopScanning().finally(() => {
      html5QrScanner = new Html5Qrcode('qr-reader');

      const config = {
        fps:            10,
        qrbox:          { width: 150, height: 150 },
        aspectRatio:    1.0,
        disableFlip:    false
      };

      html5QrScanner
        .start(
          { facingMode: 'environment' }, // prefer back camera
          config,
          (decodedText) => {
            if (typeof _onScanSuccess === 'function') {
              _onScanSuccess(decodedText);
            }
          },
          (errorMessage) => {
            // Scan errors are frequent (no QR in frame) – suppress noise
            void errorMessage;
          }
        )
        .then(resolve)
        .catch(err => {
          // Fallback: try any available camera
          if (err && err.toString().includes('facingMode')) {
            html5QrScanner
              .start(
                { facingMode: 'user' },
                config,
                (decodedText) => {
                  if (typeof _onScanSuccess === 'function') {
                    _onScanSuccess(decodedText);
                  }
                },
                () => {}
              )
              .then(resolve)
              .catch(reject);
          } else {
            reject(err);
          }
        });
    });
  });
}

/**
 * Stop the camera and clear the scanner instance.
 * @returns {Promise<void>}
 */
function stopScanning() {
  if (!html5QrScanner) return Promise.resolve();

  return html5QrScanner
    .stop()
    .then(() => {
      html5QrScanner.clear();
      html5QrScanner = null;
    })
    .catch(() => {
      html5QrScanner = null;
    });
}
