from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import qrcode
from io import BytesIO
from pathlib import Path

app = FastAPI(title="QR Code Service")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

QRCODE_DIR = Path("/Users/jjjj/Documents/股票/qrcode_service")

@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = QRCODE_DIR / "static" / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>QR Code Service Index not found</h1>", status_code=404)
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/generate")
async def generate_qr(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        # 创建二维码对象
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # 创建图片
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 将图片保存到内存流
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
