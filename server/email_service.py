import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64

from config import GMAIL_APP_PASSWORD, GMAIL_USER


def send_coupon_email(
    to_email: str,
    holder_name: str,
    coupon_code: str,
    event_name: str,
    qr_base64: str,
    barman_name: str = "",
) -> None:
    """Send a coupon email via Gmail SMTP with the QR code embedded as an inline image.

    Raises:
        RuntimeError: if GMAIL_USER or GMAIL_APP_PASSWORD are not configured.
        smtplib.SMTPException: on SMTP errors.
    """
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise RuntimeError(
            "GMAIL_USER and GMAIL_APP_PASSWORD environment variables must be set "
            "before sending emails."
        )

    subject = f"Tu cupón para {event_name}"

    # Build the multipart/related message so we can embed the QR image inline.
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = to_email

    # Wrap the visible content in a multipart/alternative block so clients that
    # don't render HTML still get something readable.
    alt_part = MIMEMultipart("alternative")
    msg.attach(alt_part)

    barman_note = (
        f"Por favor usa preferentemente el barman: {barman_name}.\n"
        if barman_name
        else ""
    )
    plain_body = (
        f"Hola {holder_name},\n\n"
        f"Aquí tienes tu cupón de bebida gratuita. Muéstraselo al barman al llegar.\n\n"
        f"{barman_note}"
        f"Tu cupón para el evento '{event_name}' es:\n\n"
        f"  {coupon_code}\n\n"
        "Presenta este código o el QR adjunto para canjear tu copa.\n\n"
        "¡Disfruta del evento!"
    )

    html_body = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{subject}</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      background: #f4f4f4;
      margin: 0;
      padding: 0;
    }}
    .container {{
      max-width: 520px;
      margin: 32px auto;
      background: #ffffff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 2px 12px rgba(0,0,0,0.12);
    }}
    .header {{
      background: #1a1a2e;
      color: #e0c97f;
      padding: 28px 24px;
      text-align: center;
    }}
    .header h1 {{
      margin: 0;
      font-size: 22px;
      letter-spacing: 1px;
    }}
    .body {{
      padding: 28px 24px;
      text-align: center;
      color: #333;
    }}
    .body p {{
      font-size: 15px;
      line-height: 1.6;
    }}
    .code-box {{
      display: inline-block;
      margin: 16px auto;
      padding: 12px 24px;
      background: #f0f0f0;
      border: 2px dashed #1a1a2e;
      border-radius: 8px;
      font-family: monospace;
      font-size: 22px;
      font-weight: bold;
      letter-spacing: 3px;
      color: #1a1a2e;
    }}
    .qr-wrapper {{
      margin: 20px auto;
    }}
    .qr-wrapper img {{
      width: 200px;
      height: 200px;
      border: 4px solid #1a1a2e;
      border-radius: 8px;
    }}
    .footer {{
      background: #f9f9f9;
      padding: 16px 24px;
      text-align: center;
      font-size: 12px;
      color: #999;
      border-top: 1px solid #eee;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🎟️ {event_name}</h1>
    </div>
    <div class="body">
      <p>¡Hola, <strong>{holder_name}</strong>! 🎉</p>
      <p>Aquí tienes tu cupón de bebida gratuita. Muéstraselo al barman al llegar.</p>
      {f'<p style="font-size:14px;color:#555;">Por favor usa preferentemente el barman: <strong>{barman_name}</strong>.</p>' if barman_name else ''}
      <div class="qr-wrapper">
        <img src="cid:qr_code_image" alt="QR del cupón" />
      </div>
      <div class="code-box">{coupon_code}</div>
      <p>Guarda este correo y preséntalo (QR o código) para canjear tu copa.</p>
    </div>
    <div class="footer">
      Este cupón es personal e intransferible. Válido únicamente en {event_name}.
    </div>
  </div>
</body>
</html>"""

    alt_part.attach(MIMEText(plain_body, "plain", "utf-8"))
    alt_part.attach(MIMEText(html_body, "html", "utf-8"))

    # Attach the QR image inline with Content-ID "qr_code_image"
    qr_bytes = base64.b64decode(qr_base64)
    qr_image = MIMEImage(qr_bytes, _subtype="png")
    qr_image.add_header("Content-ID", "<qr_code_image>")
    qr_image.add_header("Content-Disposition", "inline", filename="qr_coupon.png")
    msg.attach(qr_image)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())
