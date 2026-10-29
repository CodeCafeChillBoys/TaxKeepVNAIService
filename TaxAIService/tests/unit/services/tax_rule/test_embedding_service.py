import pytest
from unittest.mock import MagicMock, patch

from app.services.tax_rule.embedding_service import EmbeddingService


def test_embedding_service_init_missing_api_key():
    with patch("app.services.tax_rule.embedding_service.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = ""
        with pytest.raises(ValueError, match="GEMINI_API_KEY chưa được thiết lập"):
            EmbeddingService()


def test_get_embedding_empty_text():
    with patch("app.services.tax_rule.embedding_service.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = "fake-key"
        mock_settings.EMBEDDING_MODEL = "text-embedding-004"
        mock_settings.EMBEDDING_DIMENSION = 768

        with patch("app.services.tax_rule.embedding_service.genai.Client"):
            service = EmbeddingService()
            assert service.get_embedding("") == []
            assert service.get_embedding("   ") == []


def test_get_embedding_success():
    with patch("app.services.tax_rule.embedding_service.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = "fake-key"
        mock_settings.EMBEDDING_MODEL = "text-embedding-004"
        mock_settings.EMBEDDING_DIMENSION = 768

        with patch("app.services.tax_rule.embedding_service.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client

            fake_emb = MagicMock()
            fake_emb.values = [0.1, 0.2, 0.3]
            mock_resp = MagicMock()
            mock_resp.embeddings = [fake_emb]
            mock_client.models.embed_content.return_value = mock_resp

            service = EmbeddingService()
            result = service.get_embedding("Văn bản thuế")

            assert result == [0.1, 0.2, 0.3]
            mock_client.models.embed_content.assert_called_once()


def test_get_embeddings_batch_empty():
    with patch("app.services.tax_rule.embedding_service.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = "fake-key"
        with patch("app.services.tax_rule.embedding_service.genai.Client"):
            service = EmbeddingService()
            assert service.get_embeddings_batch([]) == []
            assert service.get_embeddings_batch(["  ", ""]) == []


def test_get_embeddings_batch_success():
    with patch("app.services.tax_rule.embedding_service.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = "fake-key"
        mock_settings.EMBEDDING_MODEL = "text-embedding-004"
        mock_settings.EMBEDDING_DIMENSION = 768

        with patch("app.services.tax_rule.embedding_service.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client

            emb1 = MagicMock()
            emb1.values = [0.1, 0.1]
            emb2 = MagicMock()
            emb2.values = [0.2, 0.2]
            mock_resp = MagicMock()
            mock_resp.embeddings = [emb1, emb2]
            mock_client.models.embed_content.return_value = mock_resp

            service = EmbeddingService()
            result = service.get_embeddings_batch(["Câu 1", "Câu 2"])

            assert len(result) == 2
            assert result[0] == [0.1, 0.1]
            assert result[1] == [0.2, 0.2]
