# Deploying the demo to Hugging Face Spaces

The service in [`service/`](service/) is a self-contained FastAPI app (Dockerfile at the
repo root) that serves both the JSON API and the mini UI at `/`. Hugging Face Spaces can
run it directly with its Docker SDK — no code changes needed beyond what's already in this
repo.

## 1. Create the Space

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space).
2. **Owner**: your account. **Space name**: e.g. `spec2schematic`.
3. **License**: MIT (matches this repo).
4. **Select the Space SDK**: choose **Docker** → template **Blank**.
5. **Space hardware**: CPU basic (free tier) is enough — rendering a spec takes
   milliseconds.
6. **Visibility**: Public (so it's clickable without login).
7. Click **Create Space**. HF creates an empty git repo for the Space.

## 2. Add the required Space metadata

Hugging Face reads a YAML front-matter block from the Space's `README.md` to know how to
run it. Put this at the very top of the Space's README (a separate file from this repo's
own README):

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

`app_port: 7860` must match the `EXPOSE`/`--port` value in the [`Dockerfile`](Dockerfile).

## 3. Push the code to the Space

The Space is just another git remote. Two ways to get the code there:

**Option A — web UI (no git needed):** on the Space page, use "Files" → "Add file" →
upload `Dockerfile`, `pyproject.toml`, `README.md`, `LICENSE`, and the `spec2schematic/`,
`service/`, `examples/` directories. Slower for a multi-file repo, but works with zero
local setup.

**Option B — git push (recommended):**

```bash
# from this repo's root
git remote add hf https://huggingface.co/spaces/<your-username>/spec2schematic
git push hf master:main
```

Pushing requires a Hugging Face access token with write scope (Settings → Access Tokens on
huggingface.co) — Git will prompt for a username/password; use the token as the password.
If the Space's default README metadata block differs from this repo's README, keep them
separate: the Space's `README.md` is the one with the YAML block from step 2, so either
merge that block into a copy of this repo's README before pushing, or push everything else
first and add the metadata block via the web UI's file editor afterward.

## 4. Watch the build

The Space page shows build logs. First build takes 2-3 minutes (installs fastapi, uvicorn,
ezdxf). Once it says "Running", the demo is live at:

```
https://huggingface.co/spaces/<your-username>/spec2schematic
```

## Local verification before pushing

```bash
docker build -t spec2schematic:local .
docker run --rm -p 7860:7860 spec2schematic:local
curl http://localhost:7860/api/examples
```

If Docker isn't available locally, verify with uvicorn instead (same app, same port
mapping doesn't matter locally):

```bash
pip install -e ".[dxf,service]"
uvicorn service.main:app --host 0.0.0.0 --port 7860
curl http://localhost:7860/api/examples
```

---

## SALİH'İN ADIMLARI (10 dakika)

1. **Hesap**: huggingface.co'da hesabın yoksa oluştur (Google ile giriş de olur).
2. **Space oluştur**: [huggingface.co/new-space](https://huggingface.co/new-space) →
   isim `spec2schematic` → SDK **Docker** → Blank template → Public → Create Space.
3. **Token al**: Settings → Access Tokens → New token → scope **Write** → kopyala
   (bir daha gösterilmez, güvenli bir yere kaydet).
4. **Push et** (repo kökünde, bu terminalde):
   ```bash
   git remote add hf https://huggingface.co/spaces/<kullanici-adin>/spec2schematic
   git push hf master:main
   ```
   Kullanıcı adı sorulunca HF kullanıcı adını, şifre sorulunca **token'ı** yapıştır.
5. **Metadata ekle**: Space sayfasında Files → `README.md` → düzenle → en üste yukarıdaki
   YAML bloğunu ekle (title/emoji/sdk/app_port) → commit.
6. **Bekle**: Build sekmesinde loglar akar, "Running" yazınca link hazır:
   `https://huggingface.co/spaces/<kullanici-adin>/spec2schematic`
7. **Doğrula**: Sayfa açılınca örnek bir spec seç, "Render" bas, SVG görünüyor mu bak.

Token'ı Claude Code oturumunda paylaşırsan 4. adımdaki push'u ben de yapabilirim; paylaşmak
istemezsen bu liste tek başına yeterli.
