import os
import logging

import resend
from resend.exceptions import ResendError
from flask import Flask, request, redirect, url_for, render_template_string
from markupsafe import escape

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Settings come from environment variables, never from the code.
# RESEND_API_KEY : your Resend API key (secret)
# TO_EMAIL       : where submissions are sent (your own email)
# FROM_EMAIL     : sender; onboarding@resend.dev works for testing
FROM_EMAIL = os.environ.get("FROM_EMAIL", "Contact Form <onboarding@resend.dev>")


PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Contact</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 480px; margin: 40px auto; padding: 0 16px; }
    label { display: block; margin-top: 14px; font-weight: 600; }
    input, textarea { width: 100%; padding: 8px; margin-top: 4px; box-sizing: border-box; font: inherit; }
    button { margin-top: 18px; padding: 10px 18px; font: inherit; cursor: pointer; }
    .msg { padding: 10px; border-radius: 6px; margin-top: 14px; }
    .ok { background: #e6f4ea; } .err { background: #fdecea; }
    .hp { position: absolute; left: -9999px; }
  </style>
</head>
<body>
 <h1>Get in touch with 21Deploys</h1>
  {% if status == "sent" %}<div class="msg ok">Thanks! Your message was sent.</div>{% endif %}
  {% if error %}<div class="msg err">{{ error }}</div>{% endif %}
  <form method="post" action="{{ url_for('submit') }}">
    <label>Name <input name="name" required maxlength="100"></label>
    <label>Email <input name="email" type="email" required maxlength="200"></label>
    <label>Message <textarea name="message" rows="5" required maxlength="5000"></textarea></label>
    <!-- Honeypot: hidden from people, bots fill it in -->
    <label class="hp">Website <input name="website" tabindex="-1" autocomplete="off"></label>
    <button type="submit">Send</button>
  </form>
</body>
</html>
"""


@app.route("/")
def form():
    return render_template_string(PAGE, status=request.args.get("status"), error=None)


@app.route("/submit", methods=["POST"])
def submit():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    # Spam check: a real person never sees the hidden field.
    if request.form.get("website"):
        app.logger.info("Honeypot triggered; submission ignored")
        return redirect(url_for("form", status="sent"))

    if not (name and email and message):
        return render_template_string(PAGE, status=None, error="Please fill in every field."), 400

    api_key = os.environ.get("RESEND_API_KEY")
    to_email = os.environ.get("TO_EMAIL")
    if not api_key or not to_email:
        app.logger.error("RESEND_API_KEY or TO_EMAIL is not set")
        return render_template_string(PAGE, status=None, error="Email is not configured on the server."), 500

    resend.api_key = api_key
    params = {
        "from": FROM_EMAIL,
        "to": [to_email],                 # always you, never the visitor's address
        "reply_to": email,                # hitting Reply goes to the visitor
        "subject": f"New contact form message from {name}",
        "html": (
            f"<p><strong>Name:</strong> {escape(name)}</p>"
            f"<p><strong>Email:</strong> {escape(email)}</p>"
            f"<p><strong>Message:</strong><br>{escape(message)}</p>"
        ),
    }

    try:
        result = resend.Emails.send(params)
        app.logger.info("Email sent, id=%s", result.get("id"))
    except ResendError as error:
        app.logger.error("Resend error: %s", error)
        return render_template_string(PAGE, status=None, error="Sorry, the message could not be sent."), 502

    # Redirect after POST so refreshing the page doesn't resend the email.
    return redirect(url_for("form", status="sent"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
