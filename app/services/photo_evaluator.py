from .ollama_client import OllamaClient
import asyncio
from typing import Dict, Any

async def evaluate_photo(photo_path: str, ollama_client: OllamaClient) -> Dict[str, Any]:
    """
    写真を評価し、スコアとコメントを返します
    """
    try:
        evaluation = await ollama_client.evaluate_image(photo_path)
        return evaluation
    except Exception as e:
        print(f"Error evaluating photo {photo_path}: {str(e)}")
        return {
            "score": 0,
            "comment": f"評価中にエラーが発生しました: {str(e)}"
        } 