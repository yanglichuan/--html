import os
import re
import mimetypes
import concurrent.futures
import time
from pathlib import Path
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Local Media Server")

# 简单的内存缓存
VIDEO_CACHE: Dict = {
    "data": [],
    "last_updated": 0,
    "expiry": 600  # 10分钟缓存
}

# 配置 CORS
# ... (keep existing middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VIDEO_DIR = Path("/Volumes/T2")
EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"}

def scan_directory(directory: Path) -> List[dict]:
    """扫描单个目录及其子目录中的视频文件，但归类到顶层目录"""
    local_videos = []
    # 确定该目录相对于 VIDEO_DIR 的顶层名称
    try:
        rel_top = directory.relative_to(VIDEO_DIR)
        top_folder_name = rel_top.parts[0] if rel_top.parts else "根目录"
    except Exception:
        top_folder_name = "未知目录"

    try:
        for root, dirs, files in os.walk(directory):
            # 过滤掉隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "System Volume Information" and d != ".Trashes"]
            
            for file in files:
                if file.startswith("._") or file.startswith("."):
                    continue
                    
                ext = os.path.splitext(file)[1].lower()
                if ext in EXTENSIONS:
                    file_path = Path(root) / file
                    try:
                        rel_path = file_path.relative_to(VIDEO_DIR)
                        local_videos.append({
                            "name": file,
                            "folder": top_folder_name, # 只记录顶层目录名
                            "path": str(rel_path),
                            "size": file_path.stat().st_size
                        })
                    except Exception:
                        continue
    except Exception as e:
        print(f"Error scanning {directory}: {e}")
    return local_videos

@app.get("/api/videos")
async def list_videos(refresh: bool = False):
    global VIDEO_CACHE
    
    # 检查缓存是否有效
    now = time.time()
    if not refresh and VIDEO_CACHE["data"] and (now - VIDEO_CACHE["last_updated"] < VIDEO_CACHE["expiry"]):
        return VIDEO_CACHE["data"]

    # 获取第一层目录进行并行扫描
    try:
        top_level_items = [VIDEO_DIR / item for item in os.listdir(VIDEO_DIR) 
                          if (VIDEO_DIR / item).is_dir() and not item.startswith(".")]
        # 也包含根目录下的文件
        root_files = [VIDEO_DIR / item for item in os.listdir(VIDEO_DIR) 
                     if (VIDEO_DIR / item).is_file() and not item.startswith(".")]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"无法访问磁盘: {e}")

    all_videos = []
    
    # 使用线程池并行扫描
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        # 扫描子目录
        future_to_dir = {executor.submit(scan_directory, d): d for d in top_level_items}
        
        # 处理根目录下的文件
        for file_path in root_files:
            ext = file_path.suffix.lower()
            if ext in EXTENSIONS:
                all_videos.append({
                    "name": file_path.name,
                    "folder": "根目录",
                    "path": file_path.name,
                    "size": file_path.stat().st_size
                })

        for future in concurrent.futures.as_completed(future_to_dir):
            all_videos.extend(future.result())
    
    # 先按文件夹排序，再按文件名排序
    sorted_videos = sorted(all_videos, key=lambda x: (x["folder"], x["name"]))
    
    # 更新缓存
    VIDEO_CACHE["data"] = sorted_videos
    VIDEO_CACHE["last_updated"] = time.time()
    
    return sorted_videos

@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = Path("/Users/jjjj/Documents/股票/media_server/index.html")
    if not index_path.exists():
        return HTMLResponse("<h1>Index file not found</h1>", status_code=404)
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

def get_video_path(video_name: str) -> Path:
    # FastAPI path 自动处理了 URL 解码，但为了保险我们手动处理一下可能存在的编码问题
    from urllib.parse import unquote
    decoded_name = unquote(video_name)
    
    # 尝试多种路径拼接方式
    potential_paths = [
        VIDEO_DIR / decoded_name,
        VIDEO_DIR / video_name
    ]
    
    for path in potential_paths:
        if path.exists() and path.is_file():
            # 安全检查：确保路径在 VIDEO_DIR 范围内
            if str(path.resolve()).startswith(str(VIDEO_DIR.resolve())):
                return path
    
    # 如果都没找到，打印详细信息用于调试
    print(f"DEBUG: Video not found. VIDEO_DIR={VIDEO_DIR}, video_name={video_name}, decoded_name={decoded_name}")
    raise HTTPException(status_code=404, detail=f"Video not found: {decoded_name}")

@app.get("/video/{video_name:path}")
async def stream_video(video_name: str, request: Request, range: Optional[str] = Header(None)):
    video_path = get_video_path(video_name)
    file_size = video_path.stat().st_size
    
    mime_type, _ = mimetypes.guess_type(video_path)
    if not mime_type:
        mime_type = "video/mp4"
    
    start, end = 0, file_size - 1
    status_code = 200

    if range:
        match = re.search(r"bytes=(\d+)-(\d*)", range)
        if match:
            start = int(match.group(1))
            if match.group(2):
                end = int(match.group(2))
            status_code = 206
    
    # 确保范围有效
    if start > end or start < 0 or end >= file_size:
        raise HTTPException(status_code=416, detail="Requested range not satisfiable")

    content_length = end - start + 1
    
    def generate_chunks(chunk_size=1024 * 1024): # 1MB chunks
        with open(video_path, "rb") as video:
            video.seek(start)
            remaining = content_length
            while remaining > 0:
                to_read = min(chunk_size, remaining)
                data = video.read(to_read)
                if not data:
                    break
                yield data
                remaining -= len(data)

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": mime_type,
    }
    
    return StreamingResponse(generate_chunks(), status_code=status_code, headers=headers)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
