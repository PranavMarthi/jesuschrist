# PolyWorld Deployment Guide

## 🚀 Deploy to Vercel

### Step 1: Import Project
1. Go to [vercel.com/new](https://vercel.com/new)
2. Click "Import Git Repository"
3. Select `PranavMarthi/jesuschrist`

### Step 2: Configure Build Settings
Vercel should auto-detect these, but verify:
- **Framework Preset**: Vite
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`

### Step 3: **CRITICAL** - Add Environment Variables
Click on "Environment Variables" and add these **REQUIRED** variables:

```
VITE_MAPBOX_ACCESS_TOKEN
Value: pk.eyJ1IjoicG1hcnRoaSIsImEiOiJjbWxjbm1qYXQxMWRlM2Zwb2J1YThhODcwIn0.pWp7Uy5gzAy7I_0r7HAujQ
```

```
VITE_GOOGLE_MAPS_API_KEY
Value: AIzaSyAg9farJkHbqQ0mihOw1b31PG-wKADSRBg
```

**⚠️ IMPORTANT**: Without these environment variables, the map will not render!

### Step 4: Deploy
Click "Deploy" and wait ~2 minutes.

---

## 🔧 Troubleshooting

### Map doesn't render (blank gray screen)
**Cause**: Environment variables not set in Vercel
**Fix**: 
1. Go to your project settings in Vercel dashboard
2. Navigate to "Settings" → "Environment Variables"
3. Add the two required variables above
4. Redeploy by going to "Deployments" → click "..." on latest deployment → "Redeploy"

### Search doesn't work
**Cause**: Google Maps API key missing or invalid
**Fix**: Verify `VITE_GOOGLE_MAPS_API_KEY` is set correctly in environment variables

---

## 🌐 Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_MAPBOX_ACCESS_TOKEN` | ✅ Yes | Mapbox token for map rendering |
| `VITE_GOOGLE_MAPS_API_KEY` | ✅ Yes | Google Maps API for place search |
| `VITE_POLYWORLD_API_URL` | ❌ Optional | Backend API URL (defaults to localhost) |

---

## 📱 After Deployment

1. **Test the map loads** - Should see spinning globe
2. **Test search** - Try searching "Tokyo" or "Madison Square Garden"
3. **Check console** - Open browser DevTools and check for errors

If you see an error about missing tokens, you forgot to set environment variables in Vercel!
