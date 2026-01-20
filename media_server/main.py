import os
import re
import mimetypes
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Local Media Server")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VIDEO_DIR = Path("/Users/jjjj/Documents/股票/media_server/videos")
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

def get_video_path(video_name: str) -> Path:
    # 确保视频名称安全并正确连接
    path = (VIDEO_DIR / video_name).resolve()
    if not path.is_relative_to(VIDEO_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Video not found: {video_name}")
    return path

@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = Path("/Users/jjjj/Documents/股票/media_server/index.html")
    if not index_path.exists():
        return HTMLResponse("<h1>Index file not found</h1>", status_code=404)
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/videos")
async def list_videos():
    videos = []
    # 支持更多常见格式
    extensions = [".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"]
    for ext in extensions:
        videos.extend(list(VIDEO_DIR.glob(f"*{ext}")))
    return [{"name": v.name, "size": v.stat().st_size} for v in sorted(videos)]

@app.get("/video/{video_name}")
async def stream_video(video_name: str, request: Request, range: Optional[str] = Header(None)):
    video_path = get_video_path(video_name)
    file_size = video_path.stat().st_size
    
    # 自动识别 MIME 类型
    mime_type, _ = mimetypes.guess_type(video_path)
    if not mime_type:
        mime_type = "video/mp4"  # 默认值
    
    start, end = 0, file_size - 1
    status_code = 200

    if range:
        match = re.search(r"bytes=(\d+)-(\d*)", range)
        if match:
            start = int(match.group(1))
            if match.group(2):
                end = int(match.group(2))
            status_code = 206
    
    # 限制单次读取大小，防止占用过多内存，但保持响应范围逻辑正确
    requested_length = end - start + 1
    max_chunk = 1024 * 1024 * 2  # 2MB chunks
    actual_end = min(start + max_chunk - 1, end)
    content_length = actual_end - start + 1

    def generate():
        with open(video_path, "rb") as video:
            video.seek(start)
            yield video.read(content_length)

    headers = {
        "Content-Range": f"bytes {start}-{actual_end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": mime_type,
    }
    
    return StreamingResponse(generate(), status_code=status_code, headers=headers)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
