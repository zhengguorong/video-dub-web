import os
import subprocess
import json
import base64
from pathlib import Path
from typing import List, Dict, Optional
import httpx
from faster_whisper import WhisperModel


class VideoProcessor:
    """Handles video processing pipeline"""
    
    def __init__(self, job_id: str, video_path: str, temp_dir: str, output_dir: str):
        self.job_id = job_id
        self.video_path = video_path
        self.temp_dir = Path(temp_dir)
        self.output_dir = Path(output_dir)
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        
        self.audio_path = self.temp_dir / "audio.wav"
        self.chinese_audio_path = self.temp_dir / "chinese_vo.mp3"
        self.vocals_path = self.temp_dir / "vocals.wav"
        self.no_vocals_path = self.temp_dir / "no_vocals.wav"
        self.mixed_audio_path = self.temp_dir / "mixed_audio.wav"
        self.final_output_path = self.output_dir / f"{job_id}_output.mp4"
    
    def extract_audio(self):
        """Extract audio from video using ffmpeg"""
        cmd = [
            "ffmpeg", "-y", "-i", self.video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(self.audio_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"音频提取失败: {result.stderr}")
    
    def transcribe_audio(self) -> List[Dict]:
        """Transcribe audio using faster-whisper"""
        model = WhisperModel("small", device="cpu", compute_type="int8")
        
        segments, info = model.transcribe(str(self.audio_path), language="en")
        
        transcript = []
        for segment in segments:
            transcript.append({
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip()
            })
        
        with open(self.temp_dir / "transcript.json", "w", encoding="utf-8") as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)
        
        return transcript
    
    def translate_to_chinese(self, english_text: str) -> str:
        """Translate English to Chinese using LLM (optional)"""
        llm_base_url = os.environ.get("LLM_BASE_URL")
        llm_api_key = os.environ.get("LLM_API_KEY")
        llm_model = os.environ.get("LLM_MODEL", "gpt-3.5-turbo")
        
        if not llm_base_url or not llm_api_key:
            raise Exception("LLM 环境变量未配置 (LLM_BASE_URL, LLM_API_KEY)")
        
        prompt = f"""请将以下英文视频旁白翻译成中文，要求：
1. 使用儿童绘本的温柔、生动的口吻
2. 不要逐字直译，要自然流畅、富有童趣
3. 适合作为配音旁白，句子简洁优美
4. 保持原意但可以适当意译

英文原文：
{english_text}

请只返回中文译文："""
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {llm_api_key}"},
                json={
                    "model": llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                }
            )
            response.raise_for_status()
            result = response.json()
            chinese_text = result["choices"][0]["message"]["content"].strip()
        
        with open(self.temp_dir / "chinese_script.txt", "w", encoding="utf-8") as f:
            f.write(chinese_text)
        
        return chinese_text
    
    def synthesize_chinese_audio(self, chinese_script: str, speaker: str = "zh_female_xiaohe_uranus_bigtts"):
        """
        Synthesize Chinese audio using Volcengine TTS Agent Plan.
        CRITICAL: Synthesizes the WHOLE script or large paragraphs in ONE call
        to avoid choppy sentence-by-sentence stitching.
        """
        api_key = os.environ.get("VOLCENGINE_AGENT_PLAN_KEY") or os.environ.get("VOLCENGINE_TTS_KEY")
        if not api_key:
            raise Exception("VOLCENGINE_AGENT_PLAN_KEY 或 VOLCENGINE_TTS_KEY 环境变量未配置")
        
        paragraphs = [p.strip() for p in chinese_script.split("\n\n") if p.strip()]
        
        if not paragraphs:
            paragraphs = [chinese_script]
        
        if len(paragraphs) == 1:
            audio_data = self._synthesize_paragraph(paragraphs[0], speaker, api_key)
            with open(self.chinese_audio_path, "wb") as f:
                f.write(audio_data)
        else:
            audio_segments = []
            for i, para in enumerate(paragraphs):
                print(f"合成段落 {i+1}/{len(paragraphs)}")
                audio_data = self._synthesize_paragraph(para, speaker, api_key)
                
                temp_segment = self.temp_dir / f"segment_{i}.mp3"
                with open(temp_segment, "wb") as f:
                    f.write(audio_data)
                audio_segments.append(temp_segment)
            
            self._concatenate_audio_segments(audio_segments, self.chinese_audio_path)
    
    def _synthesize_paragraph(self, text: str, speaker: str, api_key: str) -> bytes:
        """Synthesize a single paragraph using Volcengine TTS Agent Plan API"""
        import uuid
        
        url = "https://openspeech.bytedance.com/api/v3/plan/tts/unidirectional"
        
        headers = {
            "X-Api-Key": api_key,
            "X-Api-Resource-Id": "seed-tts-2.0",
            "X-Api-Request-Id": str(uuid.uuid4()),
            "X-Control-Require-Usage-Tokens-Return": "*",
            "Content-Type": "application/json"
        }
        
        payload = {
            "req_params": {
                "text": text,
                "speaker": speaker,
                "context_texts": ["温柔的绘本旁白"],
                "audio_params": {
                    "format": "mp3",
                    "sample_rate": 24000
                },
                "speech_rate": 0
            }
        }
        
        audio_chunks = []
        
        with httpx.Client(timeout=120.0) as client:
            with client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        
                        if "data" in data:
                            audio_b64 = data["data"]
                            audio_chunk = base64.b64decode(audio_b64)
                            audio_chunks.append(audio_chunk)
                        
                        if data.get("end"):
                            break
                    
                    except json.JSONDecodeError:
                        continue
        
        if not audio_chunks:
            raise Exception("TTS 合成失败：未返回音频数据")
        
        return b"".join(audio_chunks)
    
    def _concatenate_audio_segments(self, segments: List[Path], output_path: Path):
        """Concatenate multiple audio segments with natural spacing"""
        concat_list = self.temp_dir / "concat_list.txt"
        
        with open(concat_list, "w") as f:
            for seg in segments:
                f.write(f"file '{seg.absolute()}'\n")
        
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy", str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"音频拼接失败: {result.stderr}")
    
    def separate_vocals(self):
        """
        Separate vocals and instrumentals.
        Try demucs if available, otherwise use ffmpeg-based fallback.
        """
        try:
            cmd = [
                "demucs", "--two-stems", "vocals",
                "-o", str(self.temp_dir),
                "-n", "htdemucs",
                str(self.audio_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                demucs_output = self.temp_dir / "htdemucs" / "audio"
                if (demucs_output / "vocals.wav").exists():
                    (demucs_output / "vocals.wav").rename(self.vocals_path)
                    (demucs_output / "no_vocals.wav").rename(self.no_vocals_path)
                    print("使用 demucs 分离人声成功")
                    return
        
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"Demucs 分离失败或不可用，使用 ffmpeg 降级方案: {e}")
        
        self._ffmpeg_vocal_separation_fallback()
    
    def _ffmpeg_vocal_separation_fallback(self):
        """
        Fallback: Use ffmpeg to create a pseudo-vocal-reduced track.
        NOTE: This is NOT true stem separation - it's a simple channel-based approach.
        """
        print("警告：使用 ffmpeg 降级分离方案（非真实人声分离）")
        
        cmd_vocals = [
            "ffmpeg", "-y", "-i", str(self.audio_path),
            "-af", "pan=mono|c0=c0",
            str(self.vocals_path)
        ]
        subprocess.run(cmd_vocals, capture_output=True)
        
        cmd_no_vocals = [
            "ffmpeg", "-y", "-i", str(self.audio_path),
            "-af", "pan=stereo|c0=c0-c1|c1=c1-c0,volume=0.5",
            str(self.no_vocals_path)
        ]
        subprocess.run(cmd_no_vocals, capture_output=True)
    
    def mix_audio(self):
        """Mix Chinese VO with background music (ducked)"""
        
        if not self.chinese_audio_path.exists():
            raise Exception("中文配音文件不存在")
        
        if not self.no_vocals_path.exists():
            raise Exception("伴奏文件不存在")
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(self.chinese_audio_path),
            "-i", str(self.no_vocals_path),
            "-filter_complex",
            "[1:a]volume=0.3[bg]; [0:a][bg]amix=inputs=2:duration=longest:dropout_transition=2",
            "-ar", "44100", "-ac", "2",
            str(self.mixed_audio_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"音频混音失败: {result.stderr}")
    
    def mux_video(self) -> str:
        """Mux the mixed audio with original video"""
        
        if not self.mixed_audio_path.exists():
            raise Exception("混音文件不存在")
        
        cmd = [
            "ffmpeg", "-y",
            "-i", self.video_path,
            "-i", str(self.mixed_audio_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(self.final_output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"视频封装失败: {result.stderr}")
        
        return str(self.final_output_path)
