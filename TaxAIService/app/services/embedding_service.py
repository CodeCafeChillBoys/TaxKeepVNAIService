import os
from typing import List
from google import genai
from google.genai import types
from app.core.config import settings


class EmbeddingService:
    def __init__(self):
        # Đảm bảo đồng bộ API key từ file .env vào môi trường runtime
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY chưa được thiết lập trong file .env!")

        # Xóa biến GOOGLE_API_KEY cũ của Windows nếu có
        os.environ.pop("GOOGLE_API_KEY", None)
        os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY

        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION

    def get_embedding(self, text: str) -> List[float]:
        """Tạo embedding cho 1 đoạn văn bản đơn lẻ.
        Trả về danh sách đúng 768 số thực (List[float]).
        """
        text = text.strip()
        if not text:
            return []

        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=self.dimension),
        )
        return response.embeddings[0].values

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Tạo embedding hàng loạt cho nhiều đoạn văn bản (batch processing).
        Trả về danh sách các vector 768 chiều.
        """
        cleaned_texts = [t.strip() for t in texts if t.strip()]
        if not cleaned_texts:
            return []

        response = self.client.models.embed_content(
            model=self.model,
            contents=cleaned_texts,
            config=types.EmbedContentConfig(output_dimensionality=self.dimension),
        )
        return [emb.values for emb in response.embeddings]


# Singleton instance để tái sử dụng ở mọi nơi
embedding_service = EmbeddingService()
