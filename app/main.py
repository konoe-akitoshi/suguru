from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
from pathlib import Path
from typing import List
import asyncio
from datetime import datetime

from .database import init_db, get_db
from .models import Photo, PhotoEvaluation
from .services.photo_evaluator import evaluate_photo
from .services.ollama_client import OllamaClient

app = FastAPI(title="Photo Evaluator")

# CORSの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルのマウント
app.mount("/static", StaticFiles(directory="static"), name="static")

# データベースの初期化
@app.on_event("startup")
async def startup_event():
    await init_db()

@app.post("/api/evaluate-photos")
async def evaluate_photos(directory: str):
    """
    指定されたディレクトリ内の写真を評価します
    """
    if not os.path.exists(directory):
        raise HTTPException(status_code=404, detail="Directory not found")
    
    # 写真ファイルの拡張子
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
    
    # 写真ファイルのリストを取得
    photo_files = []
    for ext in valid_extensions:
        photo_files.extend(list(Path(directory).rglob(f"*{ext}")))
    
    # 評価結果を保存するリスト
    evaluations = []
    
    # Ollamaクライアントの初期化
    ollama_client = OllamaClient()
    
    # 各写真を評価
    for photo_path in photo_files:
        try:
            # 写真の評価
            evaluation = await evaluate_photo(str(photo_path), ollama_client)
            
            # データベースに保存
            async with get_db() as db:
                photo = Photo(
                    file_path=str(photo_path),
                    file_name=photo_path.name,
                    evaluation_score=evaluation['score'],
                    evaluation_comment=evaluation['comment'],
                    evaluated_at=datetime.now()
                )
                db.add(photo)
                await db.commit()
            
            evaluations.append({
                'file_path': str(photo_path),
                'score': evaluation['score'],
                'comment': evaluation['comment']
            })
            
        except Exception as e:
            print(f"Error evaluating {photo_path}: {str(e)}")
            continue
    
    return JSONResponse(content={
        'message': f'Evaluated {len(evaluations)} photos',
        'evaluations': evaluations
    })

@app.get("/api/photos")
async def get_photos(skip: int = 0, limit: int = 20):
    """
    評価済みの写真一覧を取得します
    """
    async with get_db() as db:
        photos = await db.query(Photo).offset(skip).limit(limit).all()
        return photos

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 