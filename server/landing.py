"""
Servidor de página de bienvenida — puerto 8080.
Muestra la IP local del servidor y renderiza el README del proyecto.
Arrancar con: python landing.py
"""

import socket
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse
import uvicorn

app = FastAPI(title="Cupones — Landing")

README_PATH = Path(__file__).parent.parent / "README.md"


def get_local_ip() -> str:
    """Devuelve la IP local principal del servidor."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "No detectada"


@app.get("/readme.md", response_class=PlainTextResponse)
def get_readme():
    """Sirve el README en texto plano para que marked.js lo renderice."""
    return README_PATH.read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
def landing():
    ip = get_local_ip()
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Sistema de Cupones — Servidor</title>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0f1117;
      color: #e6edf3;
      min-height: 100vh;
    }}

    /* ── Header ── */
    header {{
      background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%);
      border-bottom: 1px solid #30363d;
      padding: 2rem 1.5rem;
      text-align: center;
    }}

    header h1 {{
      font-size: 2rem;
      font-weight: 700;
      color: #f0f6fc;
      margin-bottom: 1.5rem;
    }}

    /* ── IP card ── */
    .ip-card {{
      display: inline-block;
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 12px;
      padding: 1.2rem 2.5rem;
      margin-bottom: 1.5rem;
    }}

    .ip-label {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #8b949e;
      margin-bottom: 0.4rem;
    }}

    .ip-value {{
      font-size: 2.5rem;
      font-weight: 700;
      font-family: "Consolas", "Courier New", monospace;
      color: #58a6ff;
      letter-spacing: 0.05em;
      cursor: pointer;
      user-select: all;
    }}

    .ip-hint {{
      font-size: 0.7rem;
      color: #6e7681;
      margin-top: 0.3rem;
    }}

    /* ── Access links ── */
    .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      justify-content: center;
      margin-top: 0.5rem;
    }}

    .links a {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      background: #21262d;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 0.5rem 1.1rem;
      color: #e6edf3;
      text-decoration: none;
      font-size: 0.9rem;
      transition: background 0.15s, border-color 0.15s;
    }}

    .links a:hover {{
      background: #30363d;
      border-color: #58a6ff;
      color: #58a6ff;
    }}

    .links a.primary {{
      background: #1f6feb;
      border-color: #1f6feb;
      color: #fff;
    }}

    .links a.primary:hover {{
      background: #388bfd;
      border-color: #388bfd;
      color: #fff;
    }}

    /* ── README section ── */
    .readme-wrap {{
      max-width: 900px;
      margin: 2.5rem auto;
      padding: 0 1.5rem 4rem;
    }}

    .readme-wrap h2.section-title {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #8b949e;
      margin-bottom: 1.2rem;
      border-bottom: 1px solid #21262d;
      padding-bottom: 0.5rem;
    }}

    /* ── Markdown styles ── */
    #readme h1, #readme h2, #readme h3,
    #readme h4, #readme h5, #readme h6 {{
      color: #f0f6fc;
      margin: 1.5rem 0 0.6rem;
      line-height: 1.3;
    }}
    #readme h1 {{ font-size: 1.75rem; border-bottom: 1px solid #21262d; padding-bottom: 0.4rem; }}
    #readme h2 {{ font-size: 1.35rem; border-bottom: 1px solid #21262d; padding-bottom: 0.3rem; }}
    #readme h3 {{ font-size: 1.1rem; }}

    #readme p {{ margin: 0.6rem 0; line-height: 1.7; color: #c9d1d9; }}

    #readme a {{ color: #58a6ff; text-decoration: none; }}
    #readme a:hover {{ text-decoration: underline; }}

    #readme code {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 4px;
      padding: 0.15em 0.4em;
      font-family: "Consolas", "Courier New", monospace;
      font-size: 0.88em;
      color: #e6edf3;
    }}

    #readme pre {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 1rem 1.2rem;
      overflow-x: auto;
      margin: 0.8rem 0;
    }}

    #readme pre code {{
      background: none;
      border: none;
      padding: 0;
      font-size: 0.875rem;
      color: #e6edf3;
    }}

    #readme blockquote {{
      border-left: 3px solid #388bfd;
      margin: 0.8rem 0;
      padding: 0.4rem 1rem;
      background: #161b22;
      border-radius: 0 6px 6px 0;
      color: #8b949e;
    }}

    #readme table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1rem 0;
      font-size: 0.9rem;
    }}

    #readme th {{
      background: #161b22;
      color: #f0f6fc;
      font-weight: 600;
      padding: 0.5rem 0.8rem;
      border: 1px solid #30363d;
      text-align: left;
    }}

    #readme td {{
      padding: 0.45rem 0.8rem;
      border: 1px solid #30363d;
      color: #c9d1d9;
    }}

    #readme tr:nth-child(even) td {{ background: #161b22; }}

    #readme ul, #readme ol {{
      margin: 0.5rem 0 0.5rem 1.5rem;
      line-height: 1.7;
      color: #c9d1d9;
    }}

    #readme li {{ margin: 0.2rem 0; }}

    #readme hr {{
      border: none;
      border-top: 1px solid #21262d;
      margin: 1.5rem 0;
    }}

    /* ── Toast ── */
    #toast {{
      position: fixed;
      bottom: 1.5rem;
      left: 50%;
      transform: translateX(-50%) translateY(80px);
      background: #1f6feb;
      color: #fff;
      padding: 0.6rem 1.4rem;
      border-radius: 8px;
      font-size: 0.875rem;
      transition: transform 0.25s ease;
      pointer-events: none;
    }}

    #toast.show {{ transform: translateX(-50%) translateY(0); }}
  </style>
</head>
<body>

  <header>
    <h1>🎟️ Sistema de Cupones</h1>

    <div class="ip-card" onclick="copyIP()" title="Haz clic para copiar">
      <div class="ip-label">IP del servidor</div>
      <div class="ip-value" id="ip-display">{ip}</div>
      <div class="ip-hint">Haz clic para copiar · Puerto principal: 8000</div>
    </div>

    <div class="links">
      <a class="primary" href="http://{ip}:8000/barman/" target="_blank">
        📱 App Barman
      </a>
      <a href="http://{ip}:8000/admin/" target="_blank">
        🖥️ Panel Admin
      </a>
      <a href="http://{ip}:8000/docs" target="_blank">
        📖 API Docs
      </a>
    </div>
  </header>

  <div class="readme-wrap">
    <h2 class="section-title">Documentación del proyecto</h2>
    <div id="readme">Cargando documentación…</div>
  </div>

  <div id="toast">IP copiada al portapapeles ✓</div>

  <script>
    // Renderizar README
    fetch('/readme.md')
      .then(r => r.text())
      .then(md => {{
        document.getElementById('readme').innerHTML = marked.parse(md);
      }})
      .catch(() => {{
        document.getElementById('readme').textContent = 'No se pudo cargar la documentación.';
      }});

    // Copiar IP al portapapeles
    function copyIP() {{
      const ip = document.getElementById('ip-display').textContent.trim();
      navigator.clipboard.writeText(ip).then(() => {{
        const toast = document.getElementById('toast');
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2000);
      }});
    }}
  </script>

</body>
</html>"""
    return HTMLResponse(html)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)
