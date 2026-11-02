# Quick Start Guide

## 🚀 Local Development (5 minutes)

### Prerequisites
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y ffmpeg python3-dev libavcodec-dev libavformat-dev \
    libavutil-dev libavdevice-dev libavfilter-dev libswscale-dev \
    libswresample-dev pkg-config gcc g++
```

### Setup
```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Set environment variables
export VOLCENGINE_AGENT_PLAN_KEY="your_agent_plan_key"
# Optional:
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="your_llm_key"
export LLM_MODEL="gpt-3.5-turbo"

# 3. Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 4. Open browser
# Visit: http://localhost:8000
```

### Quick Test
```bash
# Test API endpoints
python3 test_smoke.py

# Or manually:
curl http://localhost:8000/health
curl http://localhost:8000/api/speakers
```

## 🌐 Render.com Deployment (10 minutes)

### Option 1: Using Blueprint (Easiest)
1. Fork this repository to your GitHub account
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click "New" → "Blueprint"
4. Connect your repository
5. Click "Apply" - Render will read `render.yaml` automatically
6. Add environment variables in Render dashboard:
   - `VOLCENGINE_AGENT_PLAN_KEY` (required - Agent Plan for correct billing)
   - `LLM_BASE_URL` (optional - for auto-translation)
   - `LLM_API_KEY` (optional - for auto-translation)
   - `LLM_MODEL` (optional, defaults to `gpt-3.5-turbo`)
7. Deploy! Your app will be available at `https://your-app.onrender.com`

### Option 2: Manual Setup
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "Web Service"
3. Connect your Git repository
4. Configure:
   - **Name**: `video-dubbing-tool`
   - **Environment**: Docker
   - **Region**: Choose closest to your users
   - **Instance Type**: Starter (2GB RAM minimum recommended)
5. Add environment variables (same as above)
6. Click "Create Web Service"

### Important Notes
- **Free Tier**: Spins down after 15 minutes of inactivity (cold start ~30-60s)
- **Starter Plan**: Recommended for production use (2GB RAM, no spin-down)
- **Memory**: Video processing needs at least 2GB RAM
- **Ephemeral Storage**: Uploaded files are lost on restart - consider S3 for production
- **Build Time**: First deploy takes 5-10 minutes to build dependencies

## 🎬 Using the Application

### Workflow
1. **Upload**: Drag & drop or click to upload a video (max 100MB)
2. **Wait**: Audio extraction and English transcription (1-2 minutes)
3. **Review**: Check English transcript (editable)
4. **Translate**: 
   - Option A: Click "AI 翻译成中文" for automatic translation
   - Option B: Click "手动编写中文" to write manually
5. **Edit**: Refine Chinese script as needed
6. **Synthesize**: Select voice and click "开始合成配音"
7. **Download**: Get your dubbed video!

### Processing Time
- Short video (30s): ~2-3 minutes total
- Medium video (2 min): ~5-8 minutes total
- Long video (5 min): ~15-20 minutes total

### Supported Formats
- Input: MP4, AVI, MOV, MKV, WebM
- Output: MP4 with AAC audio
- Max size: 100MB

### Available Voices
- 小和 (Xiaohe): Female, gentle, warm - **Default**
- 弯弯 (Wanwan): Female, lively, upbeat
- 清新 (Qingxin): Male, clear, crisp
- 爽快 (Shuangkuai): Female, bright, cheerful

## 🔧 Troubleshooting

### "VOLCENGINE_AGENT_PLAN_KEY 或 VOLCENGINE_TTS_KEY 环境变量未配置"
→ Set the `VOLCENGINE_AGENT_PLAN_KEY` environment variable with your Volcengine Agent Plan API key (preferred for correct billing), or use `VOLCENGINE_TTS_KEY` as fallback

### "LLM 环境变量未配置"
→ This is optional. Use manual Chinese script editing or set LLM env vars

### Server won't start
→ Check if port 8000 is available: `lsof -i :8000`

### Out of memory
→ Upgrade to larger Render instance or use smaller videos

### Demucs not working
→ Normal. App automatically falls back to ffmpeg (slightly lower quality)

### Build fails on Render
→ Check build logs. Usually resolved by clearing cache and rebuilding

## 📊 API Endpoints

```bash
# Health check
GET /health

# Get available speakers
GET /api/speakers

# Upload video
POST /api/upload
Content-Type: multipart/form-data

# Get job status
GET /api/jobs/{job_id}

# Update transcript
POST /api/jobs/{job_id}/transcript

# Translate to Chinese (LLM)
POST /api/jobs/{job_id}/translate

# Update Chinese script
POST /api/jobs/{job_id}/chinese-script

# Synthesize audio
POST /api/jobs/{job_id}/synthesize

# Download result
GET /api/jobs/{job_id}/download
```

## 🔐 Security Checklist

- [ ] Set `VOLCENGINE_TTS_KEY` in environment (not in code)
- [ ] Add authentication for production use
- [ ] Set up rate limiting
- [ ] Configure CORS properly
- [ ] Add file scanning for uploaded videos
- [ ] Monitor usage and costs
- [ ] Set up alerts for errors

## 📈 Production Recommendations

1. **Storage**: Use S3/GCS for file persistence
2. **Queue**: Replace in-memory jobs with Redis/Celery
3. **Database**: Store job history in PostgreSQL
4. **CDN**: Use CloudFlare/CloudFront for video delivery
5. **Monitoring**: Add Sentry, DataDog, or similar
6. **Backup**: Regular database and config backups
7. **Scaling**: Use horizontal scaling with load balancer

## 💡 Tips

- Use shorter videos for faster processing
- Natural paragraph breaks in Chinese improve TTS quality
- Test with sample video before processing important content
- Monitor server logs for debugging: `render logs -t {service-id}`
- For best quality, provide well-formatted Chinese script manually

## 🐛 Known Limitations

- Maximum 100MB upload size
- CPU-only processing (no GPU acceleration yet)
- Ephemeral storage on Render free tier
- Demucs may not install on all systems (fallback provided)
- No user authentication (add before production)
- No job cleanup (manual deletion required)

## 📚 Additional Resources

- [Render Documentation](https://render.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Faster Whisper](https://github.com/guillaumekln/faster-whisper)
- [Volcengine TTS API](https://www.volcengine.com/docs/6561/79823)
