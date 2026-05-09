from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
import shutil
import os
import uuid
from engine import VideoEngine

app = FastAPI(title="Video Merger API")

# Pasta temporária para processamento
UPLOAD_DIR = "temp_videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
def read_root():
    return {"status": "online", "message": "Video Merger API is running"}

@app.post("/merge")
async def merge_videos(
    intro: UploadFile = File(...), 
    body: UploadFile = File(...)
):
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    intro_path = os.path.join(job_dir, "intro.mp4")
    body_path = os.path.join(job_dir, "body.mp4")
    output_path = os.path.join(job_dir, "output.mp4")

    # Salvar arquivos enviados
    with open(intro_path, "wb") as buffer:
        shutil.copyfileobj(intro.file, buffer)
    with open(body_path, "wb") as buffer:
        shutil.copyfileobj(body.file, buffer)

    # Executar o merge
    engine = VideoEngine()
    success, msg = engine.merge_videos(intro_path, body_path, output_path)

    if success:
        return FileResponse(
            output_path, 
            media_type="video/mp4", 
            filename=f"merged_{intro.filename}"
        )
    else:
        return {"error": msg}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
