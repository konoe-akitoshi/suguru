import httpx
import base64
from PIL import Image
import io
import json
import logging
import traceback
import sys
import re

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, base_url="http://172.21.173.115:11434"):
        self.base_url = base_url
        self.model = "gemma3:latest"

    def _extract_json(self, text: str) -> dict:
        """
        テキストからJSONを抽出します
        """
        # マークダウンのコードブロックを削除
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        
        # 余分な空白を削除
        text = text.strip()
        
        try:
            # 直接JSONとしてパースを試みる
            return json.loads(text)
        except json.JSONDecodeError:
            # JSON部分を探す
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    json_str = json_match.group()
                    # 余分な空白や改行を削除
                    json_str = re.sub(r'\s+', ' ', json_str)
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing JSON: {e}, Text: {text}")
                    return None
            return None

    async def evaluate_image(self, image_path: str) -> dict:
        """
        画像を評価し、スコアとコメントを返します
        """
        try:
            # 画像をbase64エンコード
            with Image.open(image_path) as img:
                # RGBA画像をRGBに変換
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                
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
                logger.info(f"Sending request to Ollama API for image: {image_path}")
                try:
                    response = await client.post(
                        f"{self.base_url}/api/chat",
                        json={
                            "model": self.model,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": prompt,
                                    "images": [img_str]
                                }
                            ]
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code != 200:
                        error_msg = f"Ollama API error: Status {response.status_code}, Response: {response.text}"
                        logger.error(error_msg)
                        raise Exception(error_msg)

                    # ストリーミングレスポンスを処理
                    full_response = ""
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                json_response = json.loads(line)
                                if json_response.get("done", False):
                                    break
                                content = json_response.get("message", {}).get("content", "")
                                full_response += content
                            except json.JSONDecodeError as e:
                                logger.error(f"Error parsing response line: {line}, Error: {e}")
                                continue
                            except Exception as e:
                                logger.error(f"Unexpected error processing response: {e}")
                                continue

                    logger.info(f"Received response from Ollama API: {full_response[:100]}...")

                    # JSONを抽出して処理
                    result = self._extract_json(full_response)
                    if result:
                        return {
                            "score": result.get("score", 0.0),
                            "comment": result.get("comment", "評価できませんでした")
                        }
                    else:
                        logger.warning(f"No valid JSON found in response: {full_response}")
                        return {
                            "score": 0.0,
                            "comment": full_response
                        }

                except httpx.TimeoutException as e:
                    error_msg = f"Request timeout: {str(e)}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                except httpx.RequestError as e:
                    error_msg = f"Request error: {str(e)}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

        except Exception as e:
            error_msg = f"Error evaluating image {image_path}: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return {
                "score": 0.0,
                "comment": f"評価中にエラーが発生しました: {str(e)}"
            } 