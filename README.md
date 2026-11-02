# 视频配音工具 / Video Dubbing Tool

A production-ready web application that automatically dubs English videos with natural Chinese narration in a children's storybook style.

## Features

- 📹 **Video Upload**: Support for MP4, AVI, MOV, MKV, WebM (max 100MB)
- 🎤 **Audio Extraction**: Automatic audio extraction from video
- 📝 **ASR Transcription**: English transcription using faster-whisper
- 🤖 **LLM Translation**: Optional AI translation to natural Chinese (kids/storybook tone)
- 🗣️ **Chinese TTS**: High-quality Chinese text-to-speech via Volcengine Doubao
- 🎵 **Vocal/BGM Separation**: Using demucs or ffmpeg fallback
- 🎛️ **Audio Mixing**: Intelligent BGM ducking under voice-over
- 🎬 **Video Muxing**: Final video output with Chinese narration
- 🌐 **Chinese UI**: User-friendly Chinese interface
- 📊 **Job Status API**: Real-time processing status updates

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla HTML/CSS/JS
- **ASR**: faster-whisper (CPU-optimized)
- **TTS**: Volcengine Doubao seed-tts-2.0
- **Audio Processing**: ffmpeg, demucs (optional)
- **Containerization**: Docker

## Key Design Decisions

**⚠️ IMPORTANT - Whole-Paragraph TTS**: The TTS synthesis is done in **whole paragraphs or large chunks** in a single API call, NOT sentence-by-sentence. This avoids choppy audio with awkward tails that result from stitching many small segments together.

**⚠️ IMPORTANT - Natural Speech Rate**: The TTS uses `speech_rate=0` (natural pace), NOT slowed down to artificially fill video gaps. Background music naturally fills gaps between narration. This maintains natural, engaging pacing.

## Prerequisites

- Python 3.11+
- ffmpeg
- Docker (for containerized deployment)

## Environment Variables

### Required for TTS

- `VOLCENGINE_AGENT_PLAN_KEY`: API key for Volcengine Doubao TTS Agent Plan (preferred for correct billing)
- `VOLCENGINE_TTS_KEY`: Alternative/fallback API key (used if Agent Plan key not set)

**Important**: The app uses the Volcengine **Agent Plan** endpoint (`/api/v3/plan/tts/unidirectional`) for correct billing. Set `VOLCENGINE_AGENT_PLAN_KEY` for production use.

### Optional for LLM Translation

- `LLM_BASE_URL`: OpenAI-compatible API endpoint (e.g., `https://api.openai.com/v1`)
- `LLM_API_KEY`: API key for LLM service
- `LLM_MODEL`: Model name (default: `gpt-3.5-turbo`)

**Note**: If LLM variables are not set, the app will skip automatic translation and allow manual Chinese script editing.

## Local Setup

### 1. Clone and Install Dependencies

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y ffmpeg python3.11 python3-pip

# Install Python dependencies
pip install -r requirements.txt

# Optional: Install demucs for better vocal separation
pip install demucs
```

### 2. Set Environment Variables

```bash
# Required: Volcengine Agent Plan API key (for correct billing)
export VOLCENGINE_AGENT_PLAN_KEY="your_agent_plan_key_here"
# Or use the generic key as fallback:
# export VOLCENGINE_TTS_KEY="your_generic_key_here"

# Optional LLM configuration
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="your_llm_api_key_here"
export LLM_MODEL="gpt-3.5-turbo"
```

### 3. Run Locally

```bash
# Run with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or run directly
python -m app.main
```

Visit `http://localhost:8000` in your browser.

## Docker Deployment

### Build and Run with Docker

```bash
# Build the Docker image
docker build -t video-dubbing-tool .

# Run the container
docker run -p 8000:8000 \
  -e VOLCENGINE_AGENT_PLAN_KEY="your_agent_plan_key" \
  -e LLM_BASE_URL="https://api.openai.com/v1" \
  -e LLM_API_KEY="your_llm_key" \
  -e LLM_MODEL="gpt-3.5-turbo" \
  video-dubbing-tool
```

## Render.com Deployment

### Step 1: Create a New Web Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "Web Service"
3. Connect your Git repository

### Step 2: Configure Service

- **Name**: `video-dubbing-tool`
- **Environment**: `Docker`
- **Region**: Choose closest to your users
- **Branch**: `main`
- **Instance Type**: Start with "Free" or "Starter" (at least 2GB RAM recommended)

### Step 3: Set Environment Variables

In the Render dashboard, add these environment variables:

| Key | Value | Notes |
|-----|-------|-------|
| `VOLCENGINE_AGENT_PLAN_KEY` | `your_agent_plan_key` | **Required** (Agent Plan for correct billing) |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Optional (for auto-translation) |
| `LLM_API_KEY` | `your_llm_key` | Optional (for auto-translation) |
| `LLM_MODEL` | `gpt-3.5-turbo` | Optional (defaults to gpt-3.5-turbo) |

**Note**: If you have a generic Volcengine key instead, use `VOLCENGINE_TTS_KEY` as the environment variable name (the app will use it as fallback).

### Step 4: Deploy

Click "Create Web Service". Render will:
1. Detect the Dockerfile
2. Build the container
3. Deploy to a public URL like `https://video-dubbing-tool.onrender.com`

### Step 5: Important Render Considerations

- **Ephemeral Filesystem**: Uploaded files are lost on restart/redeploy. For production, consider using object storage (AWS S3, etc.)
- **Free Tier Spin-down**: Free instances spin down after 15 minutes of inactivity (cold start ~30s)
- **Memory**: Video processing is memory-intensive. Use at least "Starter" plan (2GB RAM) for reliable processing
- **Upload Size Limit**: The app enforces a 100MB limit per file
- **Docker Image**: The Dockerfile is optimized for Render (based on `python:3.11-slim`, ~800MB final image). Build time: 5-10 minutes on first deploy. Compatible with Free and Starter plans.

## API Endpoints

### Upload Video
```
POST /api/upload
Content-Type: multipart/form-data
Body: file (video file)

Response: { "job_id": "uuid", "message": "..." }
```

### Get Job Status
```
GET /api/jobs/{job_id}

Response: {
  "job_id": "uuid",
  "state": "waiting_edit",
  "message": "...",
  "transcript": [...],
  "chinese_script": "...",
  ...
}
```

### Update Transcript
```
POST /api/jobs/{job_id}/transcript
Content-Type: application/json
Body: { "segments": [...] }
```

### Translate to Chinese (LLM)
```
POST /api/jobs/{job_id}/translate
```

### Update Chinese Script
```
POST /api/jobs/{job_id}/chinese-script
Content-Type: application/json
Body: { "script": "中文配音稿..." }
```

### Synthesize Audio
```
POST /api/jobs/{job_id}/synthesize
Content-Type: multipart/form-data
Body: speaker=zh_female_xiaohe_uranus_bigtts
```

### Download Result
```
GET /api/jobs/{job_id}/download
```

### Get Available Speakers
```
GET /api/speakers
```

## Available TTS Voices

- `zh_female_xiaohe_uranus_bigtts` - 小和（女声，温柔）**[Default]**
- `zh_female_wanwanyaya_uranus_bigtts` - 弯弯（女声，活泼）
- `zh_male_qingxin_uranus_bigtts` - 清新（男声，清晰）
- `zh_female_shuangkuai_uranus_bigtts` - 爽快（女声，明快）

## Workflow

1. User uploads video → Backend extracts audio
2. Faster-whisper transcribes to English with timestamps
3. (Optional) LLM translates to natural Chinese kids-style narration
4. User can edit Chinese script manually
5. **TTS synthesizes Chinese audio in large paragraphs** (not sentence-by-sentence)
6. Demucs separates vocals/BGM (or ffmpeg fallback)
7. Mix Chinese VO with ducked BGM
8. Mux audio back into video
9. Download result

## Vocal Separation Strategy

The app tries two methods in order:

1. **Demucs** (preferred): High-quality deep learning-based separation
2. **FFmpeg fallback** (degraded): Simple channel-based pseudo-separation

If demucs is unavailable or times out, the app automatically falls back to ffmpeg with a clear warning. For production with high-quality requirements, ensure demucs is installed.

## Smoke Test

### Manual Test
1. Upload a short test video (e.g., 30 seconds)
2. Wait for English transcription
3. Click "手动编写中文" to skip LLM
4. Enter a sample Chinese script (see `uploads/sample_zh_script.txt`)
5. Click "开始合成配音"
6. Download and verify the output video

### Automated Test Script

```bash
# Test the API endpoints
curl -X POST -F "file=@test_video.mp4" http://localhost:8000/api/upload

# Get job status (replace JOB_ID with actual ID from upload response)
curl http://localhost:8000/api/jobs/{JOB_ID}
```

## Troubleshooting

### Issue: "VOLCENGINE_TTS_KEY 环境变量未配置"
**Solution**: Set the `VOLCENGINE_TTS_KEY` environment variable with your valid API key.

### Issue: "LLM 环境变量未配置"
**Solution**: This is optional. Either:
- Set `LLM_BASE_URL` and `LLM_API_KEY` environment variables, or
- Click "手动编写中文" to manually write the Chinese script

### Issue: Demucs not working
**Solution**: The app will automatically fall back to ffmpeg. For better quality:
```bash
pip install demucs
```

### Issue: Out of memory during processing
**Solution**: 
- Use a smaller video
- Increase instance memory (on Render: upgrade to a larger plan)
- Reduce video quality before upload

### Issue: Render deployment shows "The application path is not writable"
**Solution**: This is expected on Render's ephemeral filesystem. The app uses designated directories (`uploads/`, `outputs/`, `temp/`) which are created at runtime.

## Security Notes

- ⚠️ Never commit API keys to the repository
- ✅ Always use environment variables for secrets
- ✅ File uploads are isolated per job (UUID-based naming)
- ✅ 100MB upload size limit enforced
- ⚠️ For production: add authentication, rate limiting, and file scanning

## Future Improvements

- Replace in-memory job storage with Redis or database
- Add user authentication
- Integrate object storage (S3) for file persistence on Render
- Add job cleanup/expiration
- Support batch processing
- Add webhook notifications
- Improve demucs GPU acceleration
- Add video thumbnail preview

## License

MIT

## Author

Built for production-ready English → Chinese video dubbing with natural storybook narration.
