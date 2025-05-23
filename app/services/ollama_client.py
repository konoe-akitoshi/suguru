import httpx
import base64
from PIL import Image
import io

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.model = "gemma:3b"

    async def evaluate_image(self, image_path: str) -> dict:
        """
        画像を評価し、スコアとコメントを返します
        """
        # 画像をbase64エンコード
        with Image.open(image_path) as img:
            # 画像をリサイズ（メモリ使用量を抑えるため）
            img.thumbnail((800, 800))
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

        # Ollama APIにリクエスト
        prompt = """
        この写真を以下の観点で評価し、0から10のスコアと、その理由を日本語で説明してください：
        1. 構図
        2. 光の使い方
        3. 被写体の魅力度
        4. 全体的な印象

        回答は以下のJSON形式で返してください：
        {
            "score": 数値,
            "comment": "評価コメント"
        }
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [img_str],
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.text}")

            result = response.json()
            # ここでJSONをパースして返す
            # 実際のレスポンス形式に応じて適切に処理する必要があります
            return {
                "score": 7.5,  # 仮の値
                "comment": result.get("response", "評価できませんでした")
            } 