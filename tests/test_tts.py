from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from claude_narrator.tts.base import TTSEngine
from claude_narrator.tts.edge import EdgeTTSEngine
from claude_narrator.tts import create_engine


class TestTTSEngineInterface:
    def test_cannot_instantiate_base(self):
        with pytest.raises(TypeError):
            TTSEngine()


class TestEdgeTTSEngine:
    @pytest.fixture
    def engine(self):
        return EdgeTTSEngine(voice="en-US-AriaNeural")

    async def test_synthesize_returns_bytes(self, engine):
        fake_audio = b"\x00\x01\x02\x03" * 100
        with patch("claude_narrator.tts.edge._communicate_to_bytes", new_callable=AsyncMock, return_value=fake_audio):
            with patch("claude_narrator.tts.edge.edge_tts.Communicate"):
                result = await engine.synthesize("Hello world", language="en")
                assert isinstance(result, bytes)
                assert len(result) > 0

    def test_supports_streaming_false(self, engine):
        assert engine.supports_streaming is False


class TestEngineFactory:
    def test_create_edge_engine(self):
        engine = create_engine({"tts": {"engine": "edge-tts", "voice": "en-US-AriaNeural"}})
        assert isinstance(engine, EdgeTTSEngine)

    def test_unknown_engine_falls_back_to_edge(self):
        engine = create_engine({"tts": {"engine": "nonexistent", "voice": "en-US-AriaNeural"}})
        assert isinstance(engine, EdgeTTSEngine)


class TestEngineFactoryAllEngines:
    def test_create_say_engine(self):
        from claude_narrator.tts.macos_say import MacOSSayEngine
        engine = create_engine({"tts": {"engine": "say", "voice": "Samantha"}})
        assert isinstance(engine, MacOSSayEngine)

    def test_create_espeak_engine(self):
        from claude_narrator.tts.espeak import EspeakEngine
        engine = create_engine({"tts": {"engine": "espeak", "voice": "en"}})
        assert isinstance(engine, EspeakEngine)

    def test_create_openai_engine(self):
        from claude_narrator.tts.openai_tts import OpenAITTSEngine
        engine = create_engine({"tts": {"engine": "openai", "voice": "nova", "openai": {"voice": "nova", "model": "tts-1"}}})
        assert isinstance(engine, OpenAITTSEngine)
