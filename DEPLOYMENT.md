# SkyRecon – Deployment & Mobile App Guide

> **By: S. Khadanga** · NIT Rourkela Drone Internship 2026

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Step 1 — Push to GitHub](#step-1--push-to-github)
3. [Step 2 — Deploy Database (Neon)](#step-2--deploy-database-neon--free)
4. [Step 3 — Deploy Backend (Render)](#step-3--deploy-backend-render--free)
5. [Step 4 — Deploy Frontend (Vercel)](#step-4--deploy-frontend-vercel--free)
6. [Step 5 — Connect Frontend ↔ Backend](#step-5--connect-frontend--backend)
7. [Mobile App via PWA](#-mobile-app-via-pwa-no-app-store-needed)
8. [Alternative: Railway (All-in-One)](#alternative-railway-all-in-one)
9. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Internet Users                       │
└───────────────────────┬─────────────────────────────────┘
                        │  HTTPS
          ┌─────────────▼──────────────┐
          │   Vercel (Frontend)         │  ← React + Vite (FREE)
          │   skyrecon.vercel.app       │
          └─────────────┬──────────────┘
                        │  REST API calls
          ┌─────────────▼──────────────┐
          │   Render (Backend)          │  ← FastAPI + Python (FREE)
          │   skyrecon-api.onrender.com │
          └─────────────┬──────────────┘
                        │  SQL
          ┌─────────────▼──────────────┐
          │   Neon (Database)           │  ← PostgreSQL (FREE)
          │   ep-xxx.neon.tech          │
          └────────────────────────────┘
```

---

## Step 1 — Push to GitHub

> You must have the code on GitHub for Vercel and Render to auto-deploy.

### 1.1 Create a GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. Repository name: `SkyRecon`
3. Set to **Private** (recommended for internship project)
4. Click **Create repository** — do NOT check "Add README"

### 1.2 Push Your Local Code

Open **PowerShell** in your project folder and run:

```powershell
cd "f:\Programs\2026 Drone Internship NITR\SkyRecon"

# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit: SkyRecon AI Drone Intelligence Platform"

# Add your GitHub remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/SkyRecon.git
git branch -M main
git push -u origin main
```

> ⚠️ **Model weights (*.pt files) are in .gitignore** — they are too large for GitHub.
> You will upload them manually to Render (see Step 3.4).

---

## Step 2 — Deploy Database (Neon) — FREE

Neon gives you a free serverless PostgreSQL database — no credit card needed.

### 2.1 Create a Neon Account

1. Go to [neon.tech](https://neon.tech) → **Sign up free** (use GitHub login)
2. Click **New Project**
3. Name it: `skyrecon`
4. Region: **Asia Pacific (Singapore)** — closest to NIT Rourkela
5. Click **Create project**

### 2.2 Get the Connection String

1. In the Neon dashboard, click your project → **Connection Details**
2. Copy the **Connection string** — it looks like:
   ```
   postgresql://skyrecon_owner:xxxx@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```
3. **Save this string** — you'll need it in Step 3.

### 2.3 Create the Database

In Neon's **SQL Editor** tab, run:

```sql
CREATE DATABASE skyrecon;
```

> The app will auto-create all tables and seed 25 categories on first startup.

---

## Step 3 — Deploy Backend (Render) — FREE

Render gives 750 free hours/month (enough for one always-on service).

### 3.1 Sign Up for Render

1. Go to [render.com](https://render.com) → **Sign up with GitHub**
2. Allow Render to access your GitHub repositories

### 3.2 Create a New Web Service

1. Dashboard → **New +** → **Web Service**
2. Connect your **SkyRecon** GitHub repo
3. Fill in the settings:

| Field | Value |
|---|---|
| **Name** | `skyrecon-backend` |
| **Root Directory** | `backend` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | `Free` |

### 3.3 Set Environment Variables

In Render → **Environment** tab → add these:

| Key | Value |
|---|---|
| `DATABASE_URL` | *(paste your Neon connection string from Step 2.2)* |
| `DB_HOST` | *(from Neon: host part of connection string)* |
| `DB_PORT` | `5432` |
| `DB_NAME` | `skyrecon` |
| `DB_USER` | *(from Neon)* |
| `DB_PASSWORD` | *(from Neon)* |
| `DEBUG` | `false` |
| `YOLO_MODEL` | `yolov8n.pt` |
| `CONFIDENCE_THRESHOLD` | `0.35` |
| `ALLOWED_ORIGINS` | `https://skyrecon.vercel.app` *(update after Step 4)* |

### 3.4 Upload Model Weights

> GitHub blocks files > 100MB. Upload model weights directly to Render.

**Option A — Render Disk (Recommended):**
1. In your Render service → **Disks** → Add disk
   - Name: `models`
   - Mount Path: `/opt/render/project/src`
   - Size: `10 GB` (free tier allows up to 1 GB — use `yolov8n.pt` only)
2. Use Render's **Shell** tab to upload via `curl`:
   ```bash
   # In Render shell — download from a public URL or your Google Drive
   wget -O /opt/render/project/src/yolov8n.pt "YOUR_PUBLIC_URL"
   ```

**Option B — Cloud Storage (Google Drive + gdown):**
1. Upload `.pt` files to Google Drive → share as "Anyone with link"
2. Add to `requirements.txt`:
   ```
   gdown>=5.1.0
   ```
3. Add a `download_models.py` script to `backend/`:
   ```python
   import gdown, os
   models = {
       "yolov8n.pt": "YOUR_GDRIVE_FILE_ID",
   }
   for name, file_id in models.items():
       if not os.path.exists(name):
           gdown.download(f"https://drive.google.com/uc?id={file_id}", name)
   ```
4. Update build command: `pip install -r requirements.txt && python download_models.py`

### 3.5 Deploy

1. Click **Create Web Service**
2. Watch the build logs — first deploy takes ~5 minutes
3. When done, you'll get a URL like: `https://skyrecon-backend.onrender.com`
4. Test it: `https://skyrecon-backend.onrender.com/api/health`

> ⚠️ **Free tier spins down after 15 min of inactivity.** First request after sleep takes ~30s. This is normal on the free plan.

---

## Step 4 — Deploy Frontend (Vercel) — FREE

Vercel is the best free platform for React + Vite apps.

### 4.1 Sign Up for Vercel

1. Go to [vercel.com](https://vercel.com) → **Sign up with GitHub**
2. Allow Vercel to access your GitHub account

### 4.2 Import Your Project

1. Vercel Dashboard → **Add New Project**
2. Find and select your **SkyRecon** repository → **Import**
3. Vercel auto-detects Vite — confirm these settings:

| Field | Value |
|---|---|
| **Framework Preset** | `Vite` |
| **Root Directory** | `.` *(project root, not backend)* |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Install Command** | `npm install` |

### 4.3 Set Environment Variable

In **Environment Variables** section, add:

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://skyrecon-backend.onrender.com` |

### 4.4 Deploy

1. Click **Deploy**
2. Build takes ~2 minutes
3. You'll get a URL like: `https://skyrecon.vercel.app`

---

## Step 5 — Connect Frontend ↔ Backend

After both are deployed, update the CORS setting on Render:

1. Render Dashboard → **skyrecon-backend** → **Environment**
2. Update `ALLOWED_ORIGINS`:
   ```
   https://skyrecon.vercel.app,https://skyrecon-xyz.vercel.app
   ```
3. Click **Save Changes** — Render auto-redeploys

### 5.1 Verify Everything Works

Open `https://skyrecon.vercel.app` and check:
- ✅ Landing page loads
- ✅ Dashboard shows (even if empty)
- ✅ No CORS errors in browser console (F12 → Console)
- ✅ `/api/health` on your Render URL returns `{"status": "ok"}`

---

## 📱 Mobile App via PWA (No App Store Needed!)

SkyRecon is a **Progressive Web App (PWA)**. Users can install it on any phone directly from the browser — it looks and feels like a native app.

### Android (Chrome) — Easiest

1. Open your deployed URL in **Chrome**
   ```
   https://skyrecon.vercel.app
   ```
2. Wait for the page to load fully
3. Tap the **⋮ (three dots)** menu in top-right
4. Tap **"Add to Home Screen"** or **"Install App"**
5. Tap **"Install"** in the popup
6. ✅ SkyRecon icon appears on your home screen — tap to open like any app!

> **On newer Android Chrome**, you may see an automatic install banner at the bottom of the screen.

### iOS (iPhone / iPad) — Safari Required

> ⚠️ Must use **Safari** — Chrome on iOS does not support PWA install.

1. Open your deployed URL in **Safari**:
   ```
   https://skyrecon.vercel.app
   ```
2. Tap the **Share button** (box with arrow pointing up) at the bottom
3. Scroll down and tap **"Add to Home Screen"**
4. Tap **"Add"** in top-right
5. ✅ SkyRecon icon appears on your home screen!

### What the PWA Can Do

| Feature | Web Browser | PWA (Installed) |
|---|---|---|
| Full-screen mode | ❌ (browser UI visible) | ✅ No browser chrome |
| Home screen icon | ❌ | ✅ |
| Works offline (cached UI) | ❌ | ✅ |
| Camera access | ✅ | ✅ |
| File upload | ✅ | ✅ |
| GPS location | ✅ | ✅ |
| Push notifications | ❌ | ✅ (with extra setup) |

---

## Alternative: Railway (All-in-One)

Railway is simpler — one platform for backend + database together.

### Railway Setup

1. Go to [railway.app](https://railway.app) → **Login with GitHub**
2. Click **New Project** → **Deploy from GitHub repo**
3. Select **SkyRecon** repo
4. Railway detects Python — set:
   - **Root Directory**: `backend`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Click **New** → **Database** → **Add PostgreSQL**
   - Railway auto-injects `DATABASE_URL` into your service ✅
6. Add environment variables (same as Render Step 3.3)
7. Deploy — get URL like `skyrecon-production.up.railway.app`

> Railway gives **$5 free credits/month** — enough for light usage.

---

## Troubleshooting

### "CORS Error" in browser console
- Check `ALLOWED_ORIGINS` on Render includes your Vercel URL exactly
- No trailing slash: ✅ `https://skyrecon.vercel.app` ❌ `https://skyrecon.vercel.app/`

### Render service is sleeping / slow first load
- Free tier sleeps after 15 min. This is expected.
- **Fix**: Use [UptimeRobot](https://uptimerobot.com) (free) to ping your `/api/health` endpoint every 14 minutes to keep it awake.

### "Module not found" on Render
- Make sure `Root Directory` in Render is set to `backend`
- Check `requirements.txt` is inside `backend/`

### Model weights not found
- `.pt` files are gitignored — you must upload them separately (see Step 3.4)
- For free tier, only use `yolov8n.pt` (6MB) — the large models need GPU servers

### Frontend page not found (404) on Vercel
- `vercel.json` handles this — all routes → `index.html`
- Make sure `vercel.json` is in the project root and committed to git

### PWA not installable
- Must be served over **HTTPS** (Vercel does this automatically ✅)
- `manifest.json` must be linked in `index.html` (already done ✅)
- Open `https://skyrecon.vercel.app` in Chrome → F12 → **Application** → **Manifest** to debug

---

## 💰 Cost Summary

| Service | Free Tier Limits | Paid (if needed) |
|---|---|---|
| **Vercel** | Unlimited deploys, 100GB bandwidth | $20/mo Pro |
| **Render** | 750 hrs/month, sleeps after 15min | $7/mo to stay awake |
| **Neon** | 512MB storage, 1 compute unit | $19/mo for more |
| **Railway** | $5 credit/month | Pay-as-you-go |

**Total monthly cost on free tier: $0** ✅

---

<p align="center">
  <b>SkyRecon</b> – Deployment Guide<br/>
  NIT Rourkela · 2026 Drone Internship · <strong>By: S. Khadanga</strong>
</p>
