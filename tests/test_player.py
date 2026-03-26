from unittest.mock import patch, MagicMock

import pytest

from claude_narrator.player import AudioPlayer


class TestAudioPlayer:
    @pytest.fixture
    def player(self):
        with patch("claude_narrator.player.pygame") as mock_pg:
            mock_pg.mixer = MagicMock()
            p = AudioPlayer()
            yield p, mock_pg

    async def test_play_calls_pygame(self, player):
        p, mock_pg = player
        fake_audio = b"\x00\x01\x02" * 100
        await p.play(fake_audio)
        mock_pg.mixer.music.load.assert_called_once()
        mock_pg.mixer.music.play.assert_called_once()

    async def test_stop_calls_pygame_stop(self, player):
        p, mock_pg = player
        await p.stop()
        mock_pg.mixer.music.stop.assert_called_once()

    async def test_is_playing(self, player):
        p, mock_pg = player
        mock_pg.mixer.music.get_busy.return_value = True
        assert p.is_playing is True
        mock_pg.mixer.music.get_busy.return_value = False
        assert p.is_playing is False
