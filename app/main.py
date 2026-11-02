import os
import uuid
import asyncio
import json
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.processor import VideoProcessor
from app.models import JobStatus, JobState

app = FastAPI(title="视频配音工具")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMP_DIR = BASE_DIR / "temp"

for dir_path in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
    dir_path.mkdir(exist_ok=True)

MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB

jobs: Dict[str, JobStatus] = {}


class TranscriptUpdate(BaseModel):
    segments: List[Dict]


class ChineseScriptUpdate(BaseModel):
    script: str


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main UI"""
    html_path = BASE_DIR / "static" / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>视频配音工具</h1><p>请访问 /docs 查看 API 文档</p>")


@app.post("/api/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Upload a video file and start processing"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
        raise HTTPException(status_code=400, detail="仅支持视频文件 (mp4, avi, mov, mkv, webm)")
    
    job_id = str(uuid.uuid4())
    
    file_ext = Path(file.filename).suffix
    video_path = UPLOAD_DIR / f"{job_id}{file_ext}"
    
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小超过 {MAX_UPLOAD_SIZE // 1024 // 1024}MB 限制")
    
    with open(video_path, "wb") as f:
        f.write(content)
    
    jobs[job_id] = JobStatus(
        job_id=job_id,
        state=JobState.UPLOADED,
        message="视频已上传",
        created_at=datetime.now().isoformat()
    )
    
    processor = VideoProcessor(job_id, str(video_path), str(TEMP_DIR / job_id), str(OUTPUT_DIR))
    background_tasks.add_task(process_video_task, job_id, processor)
    
    return {"job_id": job_id, "message": "视频上传成功，开始处理"}


async def process_video_task(job_id: str, processor: VideoProcessor):
    """Background task to process video"""
    try:
        jobs[job_id].state = JobState.EXTRACTING_AUDIO
        jobs[job_id].message = "提取音频中..."
        
        await asyncio.to_thread(processor.extract_audio)
        
        jobs[job_id].state = JobState.TRANSCRIBING
        jobs[job_id].message = "转写英文字幕中..."
        
        transcript = await asyncio.to_thread(processor.transcribe_audio)
        jobs[job_id].transcript = transcript
        
        jobs[job_id].state = JobState.WAITING_EDIT
        jobs[job_id].message = "英文字幕已生成，等待编辑或继续"
        
    except Exception as e:
        jobs[job_id].state = JobState.FAILED
        jobs[job_id].message = f"处理失败: {str(e)}"
        jobs[job_id].error = str(e)


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get job status and data"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="任务不存在")
    return jobs[job_id]


@app.post("/api/jobs/{job_id}/transcript")
async def update_transcript(job_id: str, data: TranscriptUpdate):
    """Update the English transcript"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    jobs[job_id].transcript = data.segments
    jobs[job_id].message = "英文字幕已更新"
    
    return {"message": "更新成功"}


@app.post("/api/jobs/{job_id}/translate")
async def translate_script(
    job_id: str,
    background_tasks: BackgroundTasks
):
    """Translate English transcript to Chinese using LLM"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    job = jobs[job_id]
    
    if not job.transcript:
        raise HTTPException(status_code=400, detail="请先完成英文字幕转写")
    
    processor = VideoProcessor(
        job_id, 
        str(UPLOAD_DIR / f"{job_id}.mp4"),
        str(TEMP_DIR / job_id),
        str(OUTPUT_DIR)
    )
    
    background_tasks.add_task(translate_task, job_id, processor)
    
    return {"message": "开始翻译"}


async def translate_task(job_id: str, processor: VideoProcessor):
    """Background task to translate"""
    try:
        jobs[job_id].state = JobState.TRANSLATING
        jobs[job_id].message = "翻译成中文绘本风格..."
        
        transcript_text = "\n".join([seg["text"] for seg in jobs[job_id].transcript])
        
        chinese_script = await asyncio.to_thread(processor.translate_to_chinese, transcript_text)
        
        jobs[job_id].chinese_script = chinese_script
        jobs[job_id].state = JobState.WAITING_TTS
        jobs[job_id].message = "中文脚本已生成，可编辑或继续"
        
    except Exception as e:
        jobs[job_id].state = JobState.FAILED
        jobs[job_id].message = f"翻译失败: {str(e)}"
        jobs[job_id].error = str(e)


@app.post("/api/jobs/{job_id}/chinese-script")
async def update_chinese_script(job_id: str, data: ChineseScriptUpdate):
    """Update the Chinese script manually"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    jobs[job_id].chinese_script = data.script
    jobs[job_id].state = JobState.WAITING_TTS
    jobs[job_id].message = "中文脚本已更新"
    
    return {"message": "更新成功"}


@app.post("/api/jobs/{job_id}/synthesize")
async def synthesize_audio(
    job_id: str,
    background_tasks: BackgroundTasks,
    speaker: str = Form("zh_female_xiaohe_uranus_bigtts")
):
    """Synthesize Chinese audio using TTS"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    job = jobs[job_id]
    
    if not job.chinese_script:
        raise HTTPException(status_code=400, detail="请先完成中文脚本")
    
    processor = VideoProcessor(
        job_id,
        str(UPLOAD_DIR / f"{job_id}.mp4"),
        str(TEMP_DIR / job_id),
        str(OUTPUT_DIR)
    )
    
    background_tasks.add_task(synthesize_task, job_id, processor, speaker)
    
    return {"message": "开始合成配音"}


async def synthesize_task(job_id: str, processor: VideoProcessor, speaker: str):
    """Background task to synthesize and mix audio"""
    try:
        jobs[job_id].state = JobState.SYNTHESIZING
        jobs[job_id].message = "合成中文配音..."
        
        await asyncio.to_thread(
            processor.synthesize_chinese_audio,
            jobs[job_id].chinese_script,
            speaker
        )
        
        jobs[job_id].state = JobState.SEPARATING
        jobs[job_id].message = "分离人声和伴奏..."
        
        await asyncio.to_thread(processor.separate_vocals)
        
        jobs[job_id].state = JobState.MIXING
        jobs[job_id].message = "混音中..."
        
        await asyncio.to_thread(processor.mix_audio)
        
        jobs[job_id].state = JobState.MUXING
        jobs[job_id].message = "合成最终视频..."
        
        output_path = await asyncio.to_thread(processor.mux_video)
        
        jobs[job_id].state = JobState.COMPLETED
        jobs[job_id].message = "处理完成！"
        jobs[job_id].output_path = output_path
        
    except Exception as e:
        jobs[job_id].state = JobState.FAILED
        jobs[job_id].message = f"处理失败: {str(e)}"
        jobs[job_id].error = str(e)


@app.get("/api/jobs/{job_id}/download")
async def download_result(job_id: str):
    """Download the processed video"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    job = jobs[job_id]
    
    if job.state != JobState.COMPLETED or not job.output_path:
        raise HTTPException(status_code=400, detail="视频还未处理完成")
    
    if not Path(job.output_path).exists():
        raise HTTPException(status_code=404, detail="输出文件不存在")
    
    return FileResponse(
        job.output_path,
        media_type="video/mp4",
        filename=f"dubbed_{job_id}.mp4"
    )


@app.get("/api/speakers")
async def get_speakers():
    """Get available TTS speakers"""
    return {
        "speakers": [
            {"id": "zh_female_xiaohe_uranus_bigtts", "name": "小和（女声，温柔）", "default": True},
            {"id": "zh_female_wanwanyaya_uranus_bigtts", "name": "弯弯（女声，活泼）", "default": False},
            {"id": "zh_male_qingxin_uranus_bigtts", "name": "清新（男声，清晰）", "default": False},
            {"id": "zh_female_shuangkuai_uranus_bigtts", "name": "爽快（女声，明快）", "default": False},
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "jobs": len(jobs)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
