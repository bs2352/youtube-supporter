from typing import Optional, List
import logging
import os
from contextlib import asynccontextmanager
from youtube_transcript_api import YouTubeTranscriptApi

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from yts.summarize import YoutubeSummarize
from yts.qa import YoutubeQA
from yts.types import SummaryResultModel, YoutubeTranscriptType


STATIC_FILES_DIR = "frontend/dist"
DEFAULT_VIDEO_ID = "cEynsEWpXdA"
DEFAULT_QUESTION = "ファインチューニングをするとなぜ精度が落ちるのですか？"
DEFAULT_REF_SOURCES = 3
DEFAULT_TRANSCRIPT_LANGUAGES = ["ja", "en", "en-US"]


# 起動時と停止時の処理はここに書く
# ref. https://fastapi.tiangolo.com/advanced/events/#alternative-events-deprecated
@asynccontextmanager
async def lifespan (app: FastAPI):
    # 起動時の処理
    if os.path.exists(STATIC_FILES_DIR):
        app.mount("/", StaticFiles(directory=STATIC_FILES_DIR, html=True), name="static")
    yield
    # 停止時の処理
    # ...


app = FastAPI(lifespan=lifespan)


class SummaryRequestModel (BaseModel):
    vid: str = DEFAULT_VIDEO_ID

class SummaruResponseModel (BaseModel):
    vid: str
    summary: SummaryResultModel

class QARequestModel (BaseModel):
    vid: str = DEFAULT_VIDEO_ID
    question: str = DEFAULT_QUESTION
    ref_sources: int = DEFAULT_REF_SOURCES

class SourceModel (BaseModel):
    score: float
    time: str
    source: str

class QAResponseModel (BaseModel):
    vid: str
    question: str
    answer: str
    sources: List[SourceModel]

class TranscriptRequestModel (BaseModel):
    vid: str = DEFAULT_VIDEO_ID

class TranscriptModel (BaseModel):
    text: str
    start: float
    duration: float

class TranscriptResponseModel (BaseModel):
    vid: str
    transcripts: List[TranscriptModel]

class SampleVidModel (BaseModel):
    vid: List[str]


@app.post (
    "/summary",
    summary="Summarize Youtube video content",
    description="Please specify video ID (such as cEynsEWpXdA, nYx5UaKI8mE) for vid parameter.",
    tags=["Summary"]
)
async def summary (request_body: SummaryRequestModel):
    vid: str = request_body.vid
    try:
        summary: Optional[SummaryResultModel] = await YoutubeSummarize.asummary(vid=vid)
        if summary is None:
            raise Exception("summary not found")
    except Exception as e:
        logging.error(f"[{vid}] {str(e)}", exc_info=True)
        return {"vid": request_body.vid, "error": str(e)}, 500
    return SummaruResponseModel(vid=vid, summary=summary)


@app.post (
    "/qa",
    summary="QA about Youtube video content",
    description="Please specify video ID (such as cEynsEWpXdA, nYx5UaKI8mE) and question.",
    tags=["QA"]
)
async def qa (request_body: QARequestModel):
    vid: str = request_body.vid
    question: str = request_body.question
    ref_sources: int = request_body.ref_sources
    sources: List[SourceModel] = []
    try:
        yqa: YoutubeQA = YoutubeQA(vid, ref_sources, True, False, False)
        answer: str = await yqa.arun(question)
        for score, _, time, source in yqa.get_source():
            sources.append(SourceModel(score=score, time=time, source=source))
    except Exception as e:
        logging.error(f"[{vid}] {str(e)}", exc_info=True)
        return {"vid": request_body.vid, "error": str(e)}, 500
    return QAResponseModel(
        vid=vid, question=question, answer=answer, sources=sources
    )


@app.post (
    "/transcript",
    summary="get transcript",
    description="get transcript",
    tags=["Transcript"]
)
async def transcript (request_body: TranscriptRequestModel):
    vid: str = request_body.vid
    try:
        transcripts: List[YoutubeTranscriptType] = YouTubeTranscriptApi.get_transcript(vid, languages=DEFAULT_TRANSCRIPT_LANGUAGES)
    except Exception as e:
        logging.error(f"[{vid}] {str(e)}", exc_info=True)
        return {"vid": request_body.vid, "error": str(e)}, 500
    return TranscriptResponseModel(
        vid=vid,
        transcripts=[
            TranscriptModel(
                text=transcript["text"],
                start=transcript["start"],
                duration=transcript["duration"]
            ) for transcript in transcripts
        ]
    )


@app.get (
    "/sample",
    summary="get sample video IDs",
    description="get sample video IDs",
    tags=["Sample"]
)
async def sample ():
    if not os.path.exists("vid.txt"):
        raise HTTPException(status_code=404, detail="file not found")
    with open("vid.txt", "r") as f:
        vids: List[str] = f.read().splitlines()
    return SampleVidModel(vid=vids)



# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8080, loop='asyncio', reload=True)