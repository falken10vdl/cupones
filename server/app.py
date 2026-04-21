from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import socket

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse, PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import ADMIN_PIN, SECRET_KEY
from database import SessionLocal, create_tables, Event, Barman, Coupon

from coupon_utils import generate_code, sign_coupon, generate_qr_base64
from email_service import send_coupon_email

README_PATH = Path(__file__).parent.parent / "README.md"


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "No detectada"


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="Coupon System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_admin(pin: str):
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=403, detail="PIN de admin incorrecto")


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class CreateEvent(BaseModel):
    name: str
    date: str
    admin_pin: str


class CreateBarman(BaseModel):
    name: str
    pin: str
    event_id: int
    admin_pin: str


class HolderInfo(BaseModel):
    email: str
    name: str


class GenerateCoupons(BaseModel):
    event_id: int
    count: int
    holders: Optional[List[HolderInfo]] = None
    admin_pin: str


class RedeemRequest(BaseModel):
    code: str
    barman_id: int
    barman_pin: str


class SyncRedemption(BaseModel):
    code: str
    redeemed_at: str  # ISO format


class SyncRequest(BaseModel):
    barman_id: int
    barman_pin: str
    redemptions: List[SyncRedemption]


class SendEmailRequest(BaseModel):
    coupon_id: int
    admin_pin: str


class SendAllEmailsRequest(BaseModel):
    event_id: int
    admin_pin: str


class LoginRequest(BaseModel):
    pin: str
    event_id: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/")
def root():
    return RedirectResponse(url="/admin/")


# --- Events -----------------------------------------------------------------


@app.post("/api/events")
def create_event(payload: CreateEvent, db: Session = Depends(get_db)):
    verify_admin(payload.admin_pin)
    event = Event(name=payload.name, date=payload.date)
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"id": event.id, "name": event.name, "date": event.date}


@app.get("/api/events")
def list_events(db: Session = Depends(get_db)):
    events = db.query(Event).all()
    result = []
    for event in events:
        total = db.query(Coupon).filter(Coupon.event_id == event.id).count()
        redeemed = (
            db.query(Coupon)
            .filter(Coupon.event_id == event.id, Coupon.redeemed_at.isnot(None))
            .count()
        )
        result.append(
            {
                "id": event.id,
                "name": event.name,
                "date": event.date,
                "total_coupons": total,
                "redeemed": redeemed,
                "pending": total - redeemed,
            }
        )
    return result


@app.get("/api/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    total = db.query(Coupon).filter(Coupon.event_id == event_id).count()
    redeemed = (
        db.query(Coupon)
        .filter(Coupon.event_id == event_id, Coupon.redeemed_at.isnot(None))
        .count()
    )
    barmans_count = db.query(Barman).filter(Barman.event_id == event_id).count()
    return {
        "id": event.id,
        "name": event.name,
        "date": event.date,
        "total_coupons": total,
        "redeemed": redeemed,
        "pending": total - redeemed,
        "barmans_count": barmans_count,
    }


# --- Barmans ----------------------------------------------------------------


@app.post("/api/barmans")
def create_barman(payload: CreateBarman, db: Session = Depends(get_db)):
    verify_admin(payload.admin_pin)
    event = db.query(Event).filter(Event.id == payload.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    barman = Barman(name=payload.name, pin=payload.pin, event_id=payload.event_id)
    db.add(barman)
    db.commit()
    db.refresh(barman)
    return {"id": barman.id, "name": barman.name, "event_id": barman.event_id}


@app.get("/api/events/{event_id}/barmans")
def list_barmans(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    barmans = db.query(Barman).filter(Barman.event_id == event_id).all()
    return [{"id": b.id, "name": b.name, "event_id": b.event_id} for b in barmans]


# --- Coupons ----------------------------------------------------------------


@app.post("/api/coupons/generate")
def generate_coupons(payload: GenerateCoupons, db: Session = Depends(get_db)):
    verify_admin(payload.admin_pin)
    event = db.query(Event).filter(Event.id == payload.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    barmans = db.query(Barman).filter(Barman.event_id == payload.event_id).all()

    created = []
    for i in range(payload.count):
        code = generate_code()
        sig = sign_coupon(code, payload.event_id)

        # Assign holder info if provided
        holder_email = None
        holder_name = None
        if payload.holders and i < len(payload.holders):
            holder_email = payload.holders[i].email
            holder_name = payload.holders[i].name

        # Round-robin assignment to barmans
        assigned_barman_id = None
        if barmans:
            assigned_barman_id = barmans[i % len(barmans)].id

        coupon = Coupon(
            code=code,
            event_id=payload.event_id,
            hmac_signature=sig,
            holder_email=holder_email,
            holder_name=holder_name,
            assigned_barman_id=assigned_barman_id,
        )
        db.add(coupon)
        db.flush()  # get coupon.id without committing

        barman_name = None
        if assigned_barman_id:
            b = next((bm for bm in barmans if bm.id == assigned_barman_id), None)
            barman_name = b.name if b else None

        created.append(
            {
                "id": coupon.id,
                "code": coupon.code,
                "event_id": coupon.event_id,
                "hmac_signature": coupon.hmac_signature,
                "holder_email": coupon.holder_email,
                "holder_name": coupon.holder_name,
                "assigned_barman_id": coupon.assigned_barman_id,
                "assigned_barman_name": barman_name,
                "redeemed_at": coupon.redeemed_at,
            }
        )

    db.commit()
    return created


@app.post("/api/coupons/send-email")
def send_coupon_email_endpoint(
    payload: SendEmailRequest, db: Session = Depends(get_db)
):
    verify_admin(payload.admin_pin)
    coupon = db.query(Coupon).filter(Coupon.id == payload.coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado")
    if not coupon.holder_email:
        raise HTTPException(status_code=400, detail="El cupón no tiene email asignado")

    event = db.query(Event).filter(Event.id == coupon.event_id).first()
    qr_data = f"{coupon.code}|{coupon.event_id}|{coupon.hmac_signature}"
    qr_base64 = generate_qr_base64(qr_data)

    send_coupon_email(
        to_email=coupon.holder_email,
        holder_name=coupon.holder_name or "",
        coupon_code=coupon.code,
        event_name=event.name if event else "",
        qr_base64=qr_base64,
    )

    coupon.email_sent_at = datetime.utcnow()
    db.commit()

    return {"status": "sent", "coupon_id": coupon.id, "email": coupon.holder_email}


@app.post("/api/coupons/send-all")
def send_all_emails(payload: SendAllEmailsRequest, db: Session = Depends(get_db)):
    verify_admin(payload.admin_pin)
    event = db.query(Event).filter(Event.id == payload.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    coupons = (
        db.query(Coupon)
        .filter(
            Coupon.event_id == payload.event_id,
            Coupon.holder_email.isnot(None),
            Coupon.email_sent_at.is_(None),
        )
        .all()
    )

    sent_count = 0
    errors = []

    for coupon in coupons:
        try:
            qr_data = f"{coupon.code}|{coupon.event_id}|{coupon.hmac_signature}"
            qr_base64 = generate_qr_base64(qr_data)
            send_coupon_email(
                to_email=coupon.holder_email,
                holder_name=coupon.holder_name or "",
                coupon_code=coupon.code,
                event_name=event.name,
                qr_base64=qr_base64,
            )
            coupon.email_sent_at = datetime.utcnow()
            sent_count += 1
        except Exception as e:
            errors.append(
                {"coupon_id": coupon.id, "email": coupon.holder_email, "error": str(e)}
            )

    db.commit()
    return {"sent": sent_count, "errors": errors}


# --- Redeem -----------------------------------------------------------------


@app.post("/api/redeem")
def redeem_coupon(payload: RedeemRequest, db: Session = Depends(get_db)):
    coupon = db.query(Coupon).filter(Coupon.code == payload.code).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado")

    if coupon.redeemed_at is not None:
        redeemed_by_name = None
        if coupon.redeemed_by_barman_id:
            b = (
                db.query(Barman)
                .filter(Barman.id == coupon.redeemed_by_barman_id)
                .first()
            )
            redeemed_by_name = b.name if b else None
        return {
            "status": "already_redeemed",
            "redeemed_at": coupon.redeemed_at,
            "redeemed_by": redeemed_by_name,
        }

    barman = db.query(Barman).filter(Barman.id == payload.barman_id).first()
    if not barman or barman.pin != payload.barman_pin:
        raise HTTPException(status_code=403, detail="PIN de barman incorrecto")

    coupon.redeemed_at = datetime.utcnow()
    coupon.redeemed_by_barman_id = payload.barman_id
    db.commit()

    return {
        "status": "success",
        "holder_name": coupon.holder_name,
        "holder_email": coupon.holder_email,
        "code": coupon.code,
    }


# --- Sync -------------------------------------------------------------------


@app.post("/api/sync")
def sync_redemptions(payload: SyncRequest, db: Session = Depends(get_db)):
    barman = db.query(Barman).filter(Barman.id == payload.barman_id).first()
    if not barman or barman.pin != payload.barman_pin:
        raise HTTPException(status_code=403, detail="PIN de barman incorrecto")

    synced = 0
    conflicts = []

    for redemption in payload.redemptions:
        coupon = db.query(Coupon).filter(Coupon.code == redemption.code).first()
        if not coupon:
            continue  # skip unknown codes

        if coupon.redeemed_at is not None:
            if coupon.redeemed_by_barman_id == payload.barman_id:
                continue  # already synced by same barman — skip
            else:
                redeemed_by_name = None
                if coupon.redeemed_by_barman_id:
                    b = (
                        db.query(Barman)
                        .filter(Barman.id == coupon.redeemed_by_barman_id)
                        .first()
                    )
                    redeemed_by_name = (
                        b.name if b else str(coupon.redeemed_by_barman_id)
                    )
                conflicts.append(
                    {
                        "code": coupon.code,
                        "redeemed_by": redeemed_by_name,
                        "redeemed_at": coupon.redeemed_at,
                    }
                )
                continue

        try:
            coupon.redeemed_at = datetime.fromisoformat(
                redemption.redeemed_at.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            coupon.redeemed_at = datetime.utcnow()
        coupon.redeemed_by_barman_id = payload.barman_id
        synced += 1

    db.commit()
    return {"synced": synced, "conflicts": conflicts}


# --- Barman coupons & login -------------------------------------------------


@app.get("/api/barman/{barman_id}/coupons")
def get_barman_coupons(
    barman_id: int,
    barman_pin: str = Query(...),
    db: Session = Depends(get_db),
):
    barman = db.query(Barman).filter(Barman.id == barman_id).first()
    if not barman or barman.pin != barman_pin:
        raise HTTPException(status_code=403, detail="PIN de barman incorrecto")

    coupons = db.query(Coupon).filter(Coupon.assigned_barman_id == barman_id).all()

    coupon_list = []
    for c in coupons:
        assigned_barman_name = barman.name  # always this barman
        redeemed_by_name = None
        if c.redeemed_by_barman_id:
            rb = db.query(Barman).filter(Barman.id == c.redeemed_by_barman_id).first()
            redeemed_by_name = rb.name if rb else None

        coupon_list.append(
            {
                "code": c.code,
                "event_id": c.event_id,
                "holder_name": c.holder_name,
                "holder_email": c.holder_email,
                "assigned_barman_id": c.assigned_barman_id,
                "assigned_barman_name": assigned_barman_name,
                "hmac_signature": c.hmac_signature,
                "redeemed_at": c.redeemed_at,
                "redeemed_by_barman_name": redeemed_by_name,
            }
        )

    return {"hmac_key": SECRET_KEY, "coupons": coupon_list}


@app.post("/api/barman/login")
def barman_login(payload: LoginRequest, db: Session = Depends(get_db)):
    barman = (
        db.query(Barman)
        .filter(
            Barman.pin == payload.pin,
            Barman.event_id == payload.event_id,
        )
        .first()
    )
    if not barman:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    event = db.query(Event).filter(Event.id == barman.event_id).first()
    return {
        "id": barman.id,
        "name": barman.name,
        "event_id": barman.event_id,
        "event_name": event.name if event else None,
    }


# --- Admin coupon list ------------------------------------------------------


@app.get("/api/events/{event_id}/coupons")
def list_event_coupons(
    event_id: int,
    admin_pin: str = Query(...),
    db: Session = Depends(get_db),
):
    verify_admin(admin_pin)
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    coupons = db.query(Coupon).filter(Coupon.event_id == event_id).all()

    result = []
    for c in coupons:
        assigned_barman_name = None
        if c.assigned_barman_id:
            b = db.query(Barman).filter(Barman.id == c.assigned_barman_id).first()
            assigned_barman_name = b.name if b else None

        redeemed_by_barman_name = None
        if c.redeemed_by_barman_id:
            rb = db.query(Barman).filter(Barman.id == c.redeemed_by_barman_id).first()
            redeemed_by_barman_name = rb.name if rb else None

        result.append(
            {
                "id": c.id,
                "code": c.code,
                "event_id": c.event_id,
                "hmac_signature": c.hmac_signature,
                "holder_name": c.holder_name,
                "holder_email": c.holder_email,
                "email_sent_at": c.email_sent_at,
                "assigned_barman_id": c.assigned_barman_id,
                "assigned_barman_name": assigned_barman_name,
                "redeemed_at": c.redeemed_at,
                "redeemed_by_barman_id": c.redeemed_by_barman_id,
                "redeemed_by_barman_name": redeemed_by_barman_name,
            }
        )

    return result


# Mount static files (after API routes so they don't shadow /api/ paths)
app.mount("/barman", StaticFiles(directory="../barman", html=True), name="barman")
app.mount("/admin", StaticFiles(directory="../admin", html=True), name="admin")

# ---------------------------------------------------------------------------
# Landing page (puerto único 8080)
# ---------------------------------------------------------------------------

@app.get("/readme.md", response_class=PlainTextResponse, include_in_schema=False)
def get_readme():
    return README_PATH.read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
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
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f1117; color: #e6edf3; min-height: 100vh; }}
    header {{ background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%); border-bottom: 1px solid #30363d; padding: 2rem 1.5rem; text-align: center; }}
    header h1 {{ font-size: 2rem; font-weight: 700; color: #f0f6fc; margin-bottom: 1.5rem; }}
    .ip-card {{ display: inline-block; background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 1.2rem 2.5rem; margin-bottom: 1.5rem; }}
    .ip-label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: #8b949e; margin-bottom: 0.4rem; }}
    .ip-value {{ font-size: 2.5rem; font-weight: 700; font-family: "Consolas", monospace; color: #58a6ff; letter-spacing: 0.05em; cursor: pointer; user-select: all; }}
    .ip-hint {{ font-size: 0.7rem; color: #6e7681; margin-top: 0.3rem; }}
    .links {{ display: flex; flex-wrap: wrap; gap: 0.75rem; justify-content: center; margin-top: 0.5rem; }}
    .links a {{ display: inline-flex; align-items: center; gap: 0.4rem; background: #21262d; border: 1px solid #30363d; border-radius: 8px; padding: 0.5rem 1.1rem; color: #e6edf3; text-decoration: none; font-size: 0.9rem; transition: background 0.15s, border-color 0.15s; }}
    .links a:hover {{ background: #30363d; border-color: #58a6ff; color: #58a6ff; }}
    .links a.primary {{ background: #1f6feb; border-color: #1f6feb; color: #fff; }}
    .links a.primary:hover {{ background: #388bfd; border-color: #388bfd; }}
    .readme-wrap {{ max-width: 900px; margin: 2.5rem auto; padding: 0 1.5rem 4rem; }}
    .readme-wrap h2.section-title {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: #8b949e; margin-bottom: 1.2rem; border-bottom: 1px solid #21262d; padding-bottom: 0.5rem; }}
    #readme h1, #readme h2, #readme h3, #readme h4, #readme h5, #readme h6 {{ color: #f0f6fc; margin: 1.5rem 0 0.6rem; line-height: 1.3; }}
    #readme h1 {{ font-size: 1.75rem; border-bottom: 1px solid #21262d; padding-bottom: 0.4rem; }}
    #readme h2 {{ font-size: 1.35rem; border-bottom: 1px solid #21262d; padding-bottom: 0.3rem; }}
    #readme h3 {{ font-size: 1.1rem; }}
    #readme p {{ margin: 0.6rem 0; line-height: 1.7; color: #c9d1d9; }}
    #readme a {{ color: #58a6ff; text-decoration: none; }}
    #readme a:hover {{ text-decoration: underline; }}
    #readme code {{ background: #161b22; border: 1px solid #30363d; border-radius: 4px; padding: 0.15em 0.4em; font-family: "Consolas", monospace; font-size: 0.88em; color: #e6edf3; }}
    #readme pre {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1rem 1.2rem; overflow-x: auto; margin: 0.8rem 0; }}
    #readme pre code {{ background: none; border: none; padding: 0; font-size: 0.875rem; }}
    #readme blockquote {{ border-left: 3px solid #388bfd; margin: 0.8rem 0; padding: 0.4rem 1rem; background: #161b22; border-radius: 0 6px 6px 0; color: #8b949e; }}
    #readme table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.9rem; }}
    #readme th {{ background: #161b22; color: #f0f6fc; font-weight: 600; padding: 0.5rem 0.8rem; border: 1px solid #30363d; text-align: left; }}
    #readme td {{ padding: 0.45rem 0.8rem; border: 1px solid #30363d; color: #c9d1d9; }}
    #readme tr:nth-child(even) td {{ background: #161b22; }}
    #readme ul, #readme ol {{ margin: 0.5rem 0 0.5rem 1.5rem; line-height: 1.7; color: #c9d1d9; }}
    #readme li {{ margin: 0.2rem 0; }}
    #readme hr {{ border: none; border-top: 1px solid #21262d; margin: 1.5rem 0; }}
    #readme details {{ margin: 0.5rem 0; }}
    #readme summary {{ cursor: pointer; color: #58a6ff; }}
    #toast {{ position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%) translateY(80px); background: #1f6feb; color: #fff; padding: 0.6rem 1.4rem; border-radius: 8px; font-size: 0.875rem; transition: transform 0.25s ease; pointer-events: none; }}
    #toast.show {{ transform: translateX(-50%) translateY(0); }}
  </style>
</head>
<body>
  <header>
    <h1>🎟️ Sistema de Cupones</h1>
    <div class="ip-card" onclick="copyIP()" title="Haz clic para copiar">
      <div class="ip-label">IP del servidor</div>
      <div class="ip-value" id="ip-display">{ip}</div>
      <div class="ip-hint">Haz clic para copiar · Puerto: 8080</div>
    </div>
    <div class="links">
      <a class="primary" href="http://{ip}:8080/barman/" target="_blank">📱 App Barman</a>
      <a href="http://{ip}:8080/admin/" target="_blank">🖥️ Panel Admin</a>
      <a href="/docs" target="_blank">📖 API Docs</a>
    </div>
  </header>
  <div class="readme-wrap">
    <h2 class="section-title">Documentación del proyecto</h2>
    <div id="readme">Cargando documentación…</div>
  </div>
  <div id="toast">IP copiada al portapapeles ✓</div>
  <script>
    fetch('/readme.md').then(r => r.text()).then(md => {{
      document.getElementById('readme').innerHTML = marked.parse(md);
    }}).catch(() => {{
      document.getElementById('readme').textContent = 'No se pudo cargar la documentación.';
    }});
    function copyIP() {{
      const ip = document.getElementById('ip-display').textContent.trim();
      navigator.clipboard.writeText(ip).then(() => {{
        const t = document.getElementById('toast');
        t.classList.add('show');
        setTimeout(() => t.classList.remove('show'), 2000);
      }});
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(html)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
