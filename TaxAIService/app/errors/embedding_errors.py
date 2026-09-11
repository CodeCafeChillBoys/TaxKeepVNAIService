class EmbeddingErrorMessages:
    """Bảng thông báo lỗi chuẩn cho tính năng Embedding & Vector AI."""
    API_KEY_MISSING = "GEMINI_API_KEY chưa được thiết lập trong file .env!"
    EMPTY_INPUT_TEXT = "Nội dung văn bản để tạo embedding không được để trống."

    @staticmethod
    def embedding_failed(detail: str) -> str:
        return f"Lỗi khi gọi mô hình embedding Gemini: {detail}"


class EmbeddingError(Exception):
    """Exception khi xảy ra lỗi tạo vector embedding."""
    def __init__(self, message: str = EmbeddingErrorMessages.EMPTY_INPUT_TEXT):
        self.message = message
        super().__init__(message)
