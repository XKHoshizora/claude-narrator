import pytest
from claude_narrator.cache import AudioCache


class TestAudioCache:
    @pytest.fixture
    def cache(self, tmp_path):
        return AudioCache(cache_dir=tmp_path / "cache", max_size_mb=1)

    def test_get_miss(self, cache):
        assert cache.get("edge-tts", "voice", "en", "hello") is None

    def test_put_and_get(self, cache):
        audio = b"\x00\x01\x02" * 100
        cache.put("edge-tts", "voice", "en", "hello", audio)
        result = cache.get("edge-tts", "voice", "en", "hello")
        assert result == audio

    def test_eviction_on_size_limit(self, cache):
        big_audio = b"\x00" * (600 * 1024)  # 600KB
        cache.put("e", "v", "en", "a", big_audio)
        cache.put("e", "v", "en", "b", big_audio)
        cache.put("e", "v", "en", "c", big_audio)
        total = sum(1 for x in [cache.get("e", "v", "en", k) for k in "abc"] if x)
        assert total <= 2

    def test_clear(self, cache):
        cache.put("e", "v", "en", "hello", b"audio")
        cache.clear()
        assert cache.get("e", "v", "en", "hello") is None
