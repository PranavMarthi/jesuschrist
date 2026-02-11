# Backend Deployment Guide

## 🚀 Deploy FastAPI Backend to Render

### Option 1: Deploy via Render Dashboard (Recommended)

1. **Go to [render.com](https://render.com)** and sign up/log in with GitHub

2. **Click "New +" → "Web Service"**

3. **Connect your GitHub repository**: `PranavMarthi/jesuschrist`

4. **Configure the service**:
   - **Name**: `polyworld-api`
   - **Region**: Oregon (US West) - closest to your users
   - **Root Directory**: `big_backend`
   - **Runtime**: Python 3
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && uvicorn app:app --host 0.0.0.0 --port $PORT`

5. **Environment Variables** (click "Advanced" → "Add Environment Variable"):
   ```
   POLYWORLD_RESULTS_FILE = ../polymarket_all_results.json
   POLYWORLD_CACHE_FILE = ../.geolocate_cache.json
   POLYWORLD_CORS_ORIGINS = https://jesuschrist-ruddy.vercel.app
   PYTHON_VERSION = 3.11.0
   ```
   
   **Optional** (if you want Google Places integration):
   ```
   GOOGLE_MAPS_API_KEY = AIzaSyAg9farJkHbqQ0mihOw1b31PG-wKADSRBg
   ```

6. **Plan**: Free (sufficient for this project)

7. **Click "Create Web Service"**

8. **Wait for deployment** (~3-5 minutes)

9. **Get your API URL**: It will be something like `https://polyworld-api-xyz.onrender.com`

---

### Step 2: Update Frontend to Use Production Backend

Once deployed, update your frontend environment variable in Vercel:

1. Go to [vercel.com](https://vercel.com) → Your project → Settings → Environment Variables
2. Add/Update:
   ```
   VITE_POLYWORLD_API_URL = https://polyworld-api-xyz.onrender.com
   ```
   (Replace with your actual Render URL)
3. Redeploy frontend: `vercel --prod`

---

## 🔧 Alternative: Deploy to Railway

Railway is another excellent option with similar setup:

1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select `PranavMarthi/jesuschrist`
4. Set:
   - **Root Directory**: `big_backend`
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Add environment variables (same as above)
6. Deploy!

---

## 📊 Checking Backend Health

After deployment, test your backend:

```bash
# Replace with your actual backend URL
curl https://polyworld-api-xyz.onrender.com/health
```

Expected response:
```json
{
  "status": "ok",
  "results_file": "../polymarket_all_results.json",
  "index_token_count": 12345,
  "index_record_count": 5678
}
```

---

## ⚠️ Important Notes

### Free Tier Limitations
- **Render Free**: Spins down after 15 minutes of inactivity, cold start ~30 seconds
- **Railway Free**: 500 hours/month, then sleeps

### CORS Configuration
The backend is configured to accept requests from:
- `https://jesuschrist-ruddy.vercel.app`

If you change your Vercel domain, update `POLYWORLD_CORS_ORIGINS` environment variable.

### Data Files
The backend needs access to:
- `polymarket_all_results.json` (1.6MB) - geocoded market data
- `.geolocate_cache.json` - optional cache file

These are included in your repository.

---

## 🐛 Troubleshooting

### Backend returns 404
- Check that the Root Directory is set to `big_backend`
- Verify Start Command includes `cd backend && ...`

### CORS errors in frontend
- Add your Vercel domain to `POLYWORLD_CORS_ORIGINS`
- Make sure no trailing slashes in the URL

### Backend returns 500 on /markets
- Check that `POLYWORLD_RESULTS_FILE` path is correct
- Verify the JSON file is in the repository

---

## 📝 Backend API Endpoints

Once deployed, your backend will expose:

- `GET /health` - Health check with index stats
- `GET /api/v1/markets/coordinates` - All market coordinates
- `GET /markets?query={location}` - Query markets by location
- `GET /api/v1/events/by-location?location={name}` - Paginated location events
- `POST /api/v1/events/by-place` - Structured place lookup
