# 🚀 Deployment Guide

## Option 1: Render (Recommended - Free Tier)

### Steps:
1. **Sign up** at [render.com](https://render.com)
2. **Connect GitHub** account
3. **Create New Web Service**
4. **Select your repository**: `Government-ID-OCR-Data-Extractor`
5. **Configure settings**:
   - **Build Command**: `apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-hin && pip install -r requirements.txt`
   - **Start Command**: `cd backend && python app.py`
   - **Environment**: `Python 3`
6. **Add Environment Variables**:
   - `FLASK_ENV` = `production`
   - `PYTHONPATH` = `/opt/render/project/src/backend`
7. **Deploy** - Render will automatically build and deploy

### Free Tier Limits:
- 750 hours/month
- Sleeps after 15 minutes of inactivity
- 512MB RAM

---

## Option 2: Railway

### Steps:
1. **Sign up** at [railway.app](https://railway.app)
2. **Connect GitHub** account
3. **Deploy from GitHub**
4. **Select repository**
5. **Railway auto-detects** Python and deploys
6. **Add Environment Variables**:
   - `FLASK_ENV` = `production`

### Pricing:
- $5/month after free trial
- Better performance than free tiers

---

## Option 3: Docker Deployment

### Local Docker:
```bash
# Build image
docker build -t ocr-extractor .

# Run container
docker run -p 7000:7000 ocr-extractor
```

### Docker Hub:
```bash
# Tag and push
docker tag ocr-extractor yourusername/ocr-extractor
docker push yourusername/ocr-extractor
```

---

## Option 4: Heroku

### Steps:
1. **Install Heroku CLI**
2. **Login**: `heroku login`
3. **Create app**: `heroku create your-ocr-app`
4. **Add buildpacks**:
   ```bash
   heroku buildpacks:add --index 1 https://github.com/heroku/heroku-buildpack-apt
   heroku buildpacks:add --index 2 heroku/python
   ```
5. **Create Aptfile**:
   ```
   tesseract-ocr
   tesseract-ocr-hin
   ```
6. **Deploy**: `git push heroku main`

---

## Option 5: DigitalOcean App Platform

### Steps:
1. **Sign up** at DigitalOcean
2. **Create App**
3. **Connect GitHub**
4. **Configure**:
   - **Source**: Your repository
   - **Build Command**: `pip install -r requirements.txt`
   - **Run Command**: `cd backend && python app.py`

---

## Environment Variables Needed:

- `FLASK_ENV` = `production`
- `PORT` = `7000` (or platform default)
- `PYTHONPATH` = `/path/to/backend` (if needed)

## Post-Deployment:

1. **Test the API**: `https://your-app.com/api/health`
2. **Upload a document** to test OCR functionality
3. **Monitor logs** for any Tesseract issues

## Troubleshooting:

### Common Issues:
- **Tesseract not found**: Ensure buildpack installs tesseract-ocr
- **Memory issues**: OCR processing is memory-intensive
- **Timeout**: Large images may take time to process

### Solutions:
- Use `opencv-python-headless` for smaller memory footprint
- Implement image compression before OCR
- Add request timeouts and error handling