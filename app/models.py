from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel


class JobState(str, Enum):
    UPLOADED = "uploaded"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    WAITING_EDIT = "waiting_edit"
    TRANSLATING = "translating"
    WAITING_TTS = "waiting_tts"
    SYNTHESIZING = "synthesizing"
    SEPARATING = "separating"
    MIXING = "mixing"
    MUXING = "muxing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(BaseModel):
    job_id: str
    state: JobState
    message: str
    created_at: str
    transcript: Optional[List[Dict]] = None
    chinese_script: Optional[str] = None
    output_path: Optional[str] = None
    error: Optional[str] = None
