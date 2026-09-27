# simple-fe: Flask contact form with email delivery

A small contact form that emails each submission to the site owner through the [Resend](https://resend.com) API. It's containerized with Docker and deployed on Render, with every push to `main` going live automatically.

**Live demo:** https://YOUR-SERVICE.onrender.com
(Free Render instance: the first visit after 15 minutes idle takes about a minute to wake up.)

## How it works

```
Visitor fills the form
      │  POST /submit
      ▼
Render (HTTPS) ──► container port 5000 ──► Gunicorn ──► Flask app
                                                            │  HTTPS (port 443)
                                                            ▼
                                                      Resend API ──► owner's inbox
```

- The visitor's email is set as **reply-to**, so replying goes straight to them.
- Email is always sent **to the owner only**. The form can't be used to email arbitrary addresses.
- A hidden **honeypot field** silently drops simple spam bots.
- After a successful send, the app **redirects** so refreshing the page doesn't resend the email.
- Resend is called over HTTPS because Render's free plan blocks outbound SMTP ports (25, 465, 587).

## Tech stack

| Layer | Choice |
|---|---|
| App | Python, Flask |
| Server | Gunicorn (production WSGI server) |
| Email | Resend Python SDK |
| Container | Docker, `python:3-slim` base |
| Hosting | Render (Git-backed web service, auto-deploy on commit) |

## Configuration

All settings come from environment variables. Nothing secret is stored in the code or the image.

| Variable | Required | Description |
|---|---|---|
| `RESEND_API_KEY` | Yes | Resend API key |
| `TO_EMAIL` | Yes | Address that receives submissions |
| `FROM_EMAIL` | No | Sender address. Defaults to Resend's test sender `onboarding@resend.dev`, which can only deliver to the Resend account owner until a domain is verified. |

## Run locally with Docker

1. Copy `.env.example` to `.env` and fill in your values (`.env` is git-ignored).
2. Build and run:

```bash
docker build -t simple-fe .
docker run --rm -it -p 5001:5000 --env-file .env simple-fe
```

3. Open http://localhost:5001

## Deployment

Render is connected to this repository through the Render GitHub App and builds the image from the `Dockerfile` on every push to `main`:

```
git push ──► GitHub notifies Render ──► Render builds from Dockerfile ──► new container goes live
```

The environment variables above are set in Render's **Environment** settings. Earlier versions were deployed through a GitHub Actions pipeline that built multi-platform images (amd64/arm64), pushed them to Docker Hub, and triggered Render with a deploy hook.

## Docker image notes

- `python:3-slim` base keeps the image small (no compilers or build tools that aren't needed at runtime).
- `pip install --no-cache-dir` avoids storing pip's download cache in the image.
- `CMD` uses the JSON (exec) form, so Gunicorn runs as PID 1, receives stop signals directly, and shuts down gracefully.
- `.dockerignore` keeps `.env`, `.venv` and other local files out of the build context.