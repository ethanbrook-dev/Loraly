# Loraly Demo Site Deployment Guide

This document explains how to set up the **frontend** (Netlify) and **backend** (Render) for the Loraly demo site, including environment variables and start commands.

---

## 1. Backend: Render Setup

**Service type:** Web Service  <br />
**Repository:** `https://github.com/AfterVoiceAI/Loraly`  <br />
**Language:** `python 3`<br />
**Branch:** `master`  <br />
**Region:** Oregon (US West)  <br />
(Do not set the "Root Directory" value - default would be the root of the repo)<br />
**Build Command:** `pip install -r backend/requirements.txt`<br />
**Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`<br />
**Instance Type:** Free (0.1 CPU, 512 MB)<br />

### Environment Variables

| Key | Example Value | Notes |
|-----|---------------|-------|
| `HF_MODEL_ID` | `microsoft/phi-2` | HuggingFace model ID used for training |
| `HF_TOKEN` | `hf_XXXXXXXXXXXXXXXXXXXX` | HuggingFace API token |
| `HF_USERNAME` | `avai-hf` | HuggingFace username |
| `MODAL_API_TOKEN` | `as-XXXXXXXXXXXXXXXX` | Modal API token for persistent chat workers |
| `NEXT_PUBLIC_PYTHON_BACKEND_URL` | `https://loraly.onrender.com` | Backend URL for frontend to call |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `e.....` | Supabase anon key |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://mgwnjahogrgmsbtcrnkj.supabase.co` | Supabase project URL |
| `RUNPOD_API_KEY` | `rpa_XXXXXXXXXXXXXXXX` | RunPod API key |
| `SUPABASE_SERVICE_ROLE_KEY` | `e.....` | Supabase service role key |
| `PORT` | *Leave empty (Render auto-sets to 10000)* | Optional, default is 10000 |

> Notes:
> - Render will automatically provide the $PORT variable. No need to set it manually unless you want a custom port.
> - Bind the host to 0.0.0.0 so the service is accessible externally.
> - Make sure MODAL_API_TOKEN is set for persistent chat worker functionality.
> - Logs and errors can be viewed in the Render dashboard under Logs.
> - Training failures often occur if the Modal token is missing or environment variables are misconfigured.

---

## 2. Frontend: Netlify Setup

**Site:** Loraly Demo Site  
**Repository:** `https://github.com/AfterVoiceAI/Loraly`

### Environment Variables
Set all of the following under `Project configuration` > `Environment variables`:

| Key | Example Value | Notes |
|-----|---------------|-------|
| `HF_MODEL_ID` | `microsoft/phi-2` | Same as backend |
| `HF_TOKEN` | `hf_XXXXXXXXXXXXXXXXXXXX` | Same as backend |
| `HF_USERNAME` | `avai-hf` | Same as backend |
| `NEXT_PUBLIC_PYTHON_BACKEND_URL` | `https://loraly.onrender.com` | Points to Render backend |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `e.....` | Supabase anon key |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://mgwnjahogrgmsbtcrnkj.supabase.co` | Supabase project URL |
| `RUNPOD_API_KEY` | `rpa_XXXXXXXXXXXXXXXX` | Same as backend |
| `SUPABASE_SERVICE_ROLE_KEY` | `e.....` | Same as backend |

> Notes:
> - Use the same environment variable values as the backend where applicable.
> - Make sure the backend URL matches the deployed Render backend for CORS requests.
> - Build command (if using default React/Vite/Next.js): TODO: `npm run build`
> - Publish directory example: TODO: `dist` (or `.next`, `build` depending on framework)

---

## 3. Summary

- **Backend** runs on **Render** with uvicorn and **requires all HuggingFace, Modal, and Supabase keys**.
- **Frontend** runs on **Netlify** with **environment variables pointing to the backend**.
- **Modal API token** is **critical** for **chat worker functionality**.