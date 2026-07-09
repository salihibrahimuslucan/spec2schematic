# Deploying the demo

**Live now:** https://spec2schematic.onrender.com (Render.com free tier — first request
after 15 minutes of idle takes ~30-50s to wake the instance up).

The service in [`service/`](service/) is a self-contained FastAPI app (Dockerfile at the
repo root) that serves both the JSON API and the mini UI at `/`. It listens on `$PORT` if
the host sets one, otherwise defaults to `7860` — so the same image works unmodified on
either target below.

**Recommendation: Render.com's free tier.** Hugging Face Spaces now requires a paid PRO
subscription to run the Docker SDK (Static Spaces are the only free option, and those can't
run a Python backend) — Render's free Web Services still support Docker with no card
required, so that's the path below. The Hugging Face steps are kept further down in case
you upgrade later or the free tier changes back.

## Option A — Render.com (free, recommended)

1. Sign up at [render.com](https://render.com) (GitHub login works, no credit card needed
   for the free tier).
2. **New** → **Web Service** → connect the `spec2schematic` GitHub repo.
3. **Runtime**: Render auto-detects the root `Dockerfile` — leave it on **Docker**.
4. **Instance type**: **Free**.
5. Leave the port field blank/default — Render injects `$PORT` and the Dockerfile's `CMD`
   already honors it (`${PORT:-7860}`).
6. Click **Create Web Service**. First build takes ~2-3 minutes (installs fastapi, uvicorn,
   ezdxf). Once it says "Live", the demo is at the URL Render assigns (this repo's is
   already deployed at https://spec2schematic.onrender.com).

**Free-tier trade-off:** the service spins down after 15 minutes of no traffic and takes
~30-50 seconds to wake up on the next request (cold start). Fine for a recruiter clicking a
portfolio link; not fine for anything latency-sensitive.

## Option B — Hugging Face Spaces (requires PRO)

Only worth it if you already have (or plan to get) an HF PRO subscription — otherwise
Spaces' Docker SDK is greyed out and only the Static template (no backend) is free.

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space).
2. **Owner**: your account. **Space name**: e.g. `spec2schematic`.
3. **Select the Space SDK**: **Docker** → template **Blank**. **Visibility**: Public.
4. Add this YAML front-matter to the top of the *Space's* `README.md` (not this repo's own
   README — keep them separate):
   ```yaml
   ---
   title: spec2schematic
   emoji: 🔌
   colorFrom: blue
   colorTo: gray
   sdk: docker
   app_port: 7860
   pinned: false
   license: mit
   ---
   ```
5. Push the code:
   ```bash
   git remote add hf https://huggingface.co/spaces/<your-username>/spec2schematic
   git push hf master:main
   ```
   Needs a write-scope access token (Settings → Access Tokens) as the git password.
6. Watch the Space's build log; once "Running", the demo is at
   `https://huggingface.co/spaces/<your-username>/spec2schematic`.

## Local verification before pushing

```bash
docker build -t spec2schematic:local .
docker run --rm -p 7860:7860 spec2schematic:local
curl http://localhost:7860/api/examples
```

If Docker isn't available locally, verify with uvicorn instead (same app):

```bash
pip install -e ".[dxf,service]"
uvicorn service.main:app --host 0.0.0.0 --port 7860
curl http://localhost:7860/api/examples
```

---

## SALİH'İN ADIMLARI — TAMAMLANDI ✓

Deploy edildi: **https://spec2schematic.onrender.com** (Render.com free tier, servis
`srv-d97r5qmq1p3s73fb69sg`). Doğrulandı: `/api/examples`, `/api/generate`,
`/api/generate/dxf`, `/` hepsi 200 dönüyor. İlk açılış 30-50 saniye sürebilir (ücretsiz tier
15 dk hareketsizlikten sonra uyuyor), sonrakiler hızlı.
