from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
from pathlib import Path
from typing import List, Dict
import asyncio
from datetime import datetime
from sqlalchemy import select

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
async def evaluate_photos(directory: Dict[str, str] = Body(...)):
    """
    指定されたディレクトリ内の写真を評価します
    """
    dir_path = directory.get("directory")
    if not dir_path or not os.path.exists(dir_path):
        raise HTTPException(status_code=404, detail="Directory not found")
    
    # 写真ファイルの拡張子
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
    
    # 写真ファイルのリストを取得
    photo_files = []
    for ext in valid_extensions:
        photo_files.extend(list(Path(dir_path).rglob(f"*{ext}")))
    
    # 評価結果を保存するリスト
    evaluations = []
    
    # Ollamaクライアントの初期化
    ollama_client = OllamaClient()
    
    # 各写真を評価
    async for db in get_db():
        for photo_path in photo_files:
            try:
                # 写真の評価
                evaluation = await evaluate_photo(str(photo_path), ollama_client)
                
                # 既存の写真を検索
                query = select(Photo).where(Photo.file_path == str(photo_path))
                result = await db.execute(query)
                existing_photo = result.scalar_one_or_none()
                
                if existing_photo:
                    # 既存の写真を更新
                    existing_photo.evaluation_score = evaluation['score']
                    existing_photo.evaluation_comment = evaluation['comment']
                    existing_photo.evaluated_at = datetime.now()
                else:
                    # 新しい写真を追加
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

from fastapi.responses import FileResponse

@app.get("/api/photos/image/{file_path:path}")
async def get_photo_image(file_path: str):
    """
    指定されたパスの画像ファイルを返す
    """
    from urllib.parse import unquote
    decoded_path = unquote(file_path)
    # 先頭の余分なスラッシュを除去
    while decoded_path.startswith("//"):
        decoded_path = decoded_path[1:]
    if not os.path.exists(decoded_path):
        raise HTTPException(status_code=404, detail="Image not found")
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
    ext = os.path.splitext(decoded_path)[1].lower()
    if ext not in valid_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type")
    return FileResponse(decoded_path)
@app.get("/api/photos")
async def get_photos(skip: int = 0, limit: int = 20):
    """
    評価済みの写真一覧を取得します
    """
    async for db in get_db():
        from sqlalchemy import desc
        query = select(Photo).order_by(desc(Photo.id)).offset(skip).limit(limit)
        result = await db.execute(query)
        photos = result.scalars().all()
        # evaluated_atを文字列化して返す
        photo_dicts = []
        for photo in photos:
            photo_dicts.append({
                "id": photo.id,
                "file_path": photo.file_path,
                "file_name": photo.file_name,
                "evaluation_score": photo.evaluation_score,
                "evaluation_comment": photo.evaluation_comment,
                "evaluated_at": photo.evaluated_at.isoformat() if photo.evaluated_at else None
            })
        return photo_dicts

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 