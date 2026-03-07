import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


@pytest.fixture
def ws():
    import importlib
    return importlib.import_module("weekend_sweep")


class TestScoreSentiment:
    def test_bullish_keyword(self, ws):
        sentiment, conf = ws.score_sentiment("Markets rally on strong GDP growth")
        assert sentiment == "BULLISH"
        assert 0.5 < conf <= 0.95

    def test_bearish_keyword(self, ws):
        sentiment, conf = ws.score_sentiment("Nifty crash as recession fears mount")
        assert sentiment == "BEARISH"
        assert 0.5 < conf <= 0.95

    def test_neutral_no_keywords(self, ws):
        sentiment, conf = ws.score_sentiment("Trading hours today are normal")
        assert sentiment == "NEUTRAL"
        assert conf == 0.5

    def test_mixed_returns_neutral(self, ws):
        sentiment, _ = ws.score_sentiment("rally crash")
        assert sentiment == "NEUTRAL"

    def test_summary_contributes(self, ws):
        sentiment, _ = ws.score_sentiment(
            "Markets close flat",
            "FII buying surge as rate cut expectations rise"
        )
        assert sentiment == "BULLISH"


class TestIsMacroRelevant:
    def test_rbi_relevant(self, ws):
        assert ws.is_macro_relevant("RBI keeps repo rate unchanged") is True

    def test_nifty_relevant(self, ws):
        assert ws.is_macro_relevant("Nifty hits all-time high") is True

    def test_irrelevant(self, ws):
        assert ws.is_macro_relevant("Celebrity wedding news") is False

    def test_crude_relevant(self, ws):
        assert ws.is_macro_relevant("Crude oil falls 3 percent") is True


class TestAggregateSnapshot:
    def _make_articles(self, bull=3, bear=1, neutral=2):
        arts = []
        for _ in range(bull):
            arts.append({"sentiment": "BULLISH", "confidence": 0.8,
                         "macro_relevant": True, "title": "Rally",
                         "source": "et", "published": None, "link": ""})
        for _ in range(bear):
            arts.append({"sentiment": "BEARISH", "confidence": 0.75,
                         "macro_relevant": False, "title": "Crash",
                         "source": "mc", "published": None, "link": ""})
        for _ in range(neutral):
            arts.append({"sentiment": "NEUTRAL", "confidence": 0.5,
                         "macro_relevant": False, "title": "Flat",
                         "source": "reuters", "published": None, "link": ""})
        return arts

    def test_snapshot_keys(self, ws):
        snap = ws.aggregate_snapshot(self._make_articles(), 48)
        required = {
            "timestamp", "lookback_hours", "total_articles",
            "sentiment_breakdown", "net_sentiment_score",
            "overall_sentiment", "signal_strength", "top_headlines",
            "feed_breakdown", "source", "version"
        }
        assert required.issubset(snap.keys())

    def test_total_articles_correct(self, ws):
        arts = self._make_articles(bull=4, bear=2, neutral=3)
        snap = ws.aggregate_snapshot(arts, 48)
        assert snap["total_articles"] == 9

    def test_bullish_overall(self, ws):
        arts = self._make_articles(bull=8, bear=1, neutral=1)
        snap = ws.aggregate_snapshot(arts, 48)
        assert snap["overall_sentiment"] == "BULLISH"

    def test_bearish_overall(self, ws):
        arts = self._make_articles(bull=1, bear=8, neutral=1)
        snap = ws.aggregate_snapshot(arts, 48)
        assert snap["overall_sentiment"] == "BEARISH"

    def test_neutral_overall_balanced(self, ws):
        arts = self._make_articles(bull=5, bear=5, neutral=0)
        snap = ws.aggregate_snapshot(arts, 48)
        assert snap["overall_sentiment"] == "NEUTRAL"

    def test_empty_articles(self, ws):
        snap = ws.aggregate_snapshot([], 48)
        assert snap["total_articles"] == 0
        assert snap["net_sentiment_score"] == 0.0

    def test_pct_sums_to_100(self, ws):
        snap = ws.aggregate_snapshot(self._make_articles(), 48)
        bd = snap["sentiment_breakdown"]
        total = bd["bullish_pct"] + bd["bearish_pct"] + bd["neutral_pct"]
        assert abs(total - 100.0) < 0.5

    def test_signal_strength_non_negative(self, ws):
        snap = ws.aggregate_snapshot(self._make_articles(), 48)
        assert snap["signal_strength"] >= 0

    def test_top_headlines_max_10(self, ws):
        arts = self._make_articles(bull=15, bear=5, neutral=5)
        snap = ws.aggregate_snapshot(arts, 48)
        assert len(snap["top_headlines"]) <= 10

    def test_snapshot_json_serialisable(self, ws):
        snap = ws.aggregate_snapshot(self._make_articles(), 48)
        dumped = json.dumps(snap)
        assert len(dumped) > 10


class TestWriteToFile:
    def test_writes_valid_json(self, ws, tmp_path):
        snap = {"test": True, "value": 42}
        out = tmp_path / "snap.json"
        ws.write_to_file(snap, out)
        loaded = json.loads(out.read_text())
        assert loaded["test"] is True
        assert loaded["value"] == 42

    def test_creates_parent_dirs(self, ws, tmp_path):
        snap = {"ok": 1}
        out = tmp_path / "nested" / "dir" / "snap.json"
        ws.write_to_file(snap, out)
        assert out.exists()


class TestWriteToRedis:
    def test_skips_when_no_redis(self, ws):
        original = ws.HAS_REDIS
        ws.HAS_REDIS = False
        try:
            ws.write_to_redis({"test": 1})
        finally:
            ws.HAS_REDIS = original

    def test_calls_setex_on_success(self, ws):
        if not ws.HAS_REDIS:
            pytest.skip("redis-py not installed")
        mock_r = MagicMock()
        mock_r.ping.return_value = True
        with patch("weekend_sweep.redis_lib.Redis", return_value=mock_r):
            ws.write_to_redis({"data": "test"})
        mock_r.setex.assert_called_once()
        key = mock_r.setex.call_args[0][0]
        assert key == "WEEKEND_MACRO_SNAPSHOT"

    def test_handles_redis_connection_error(self, ws):
        if not ws.HAS_REDIS:
            pytest.skip("redis-py not installed")
        import redis as redis_lib_inner
        with patch("weekend_sweep.redis_lib.Redis") as mock_cls:
            mock_cls.return_value.ping.side_effect = redis_lib_inner.ConnectionError("refused")
            ws.write_to_redis({"data": "test"})


class TestParseFeedEntryTime:
    def test_returns_datetime_from_published_parsed(self, ws):
        from datetime import timezone
        entry = MagicMock()
        entry.published_parsed = (2026, 3, 6, 12, 0, 0, 0, 0, 0)
        entry.updated_parsed = None
        entry.created_parsed = None
        result = ws.parse_feed_entry_time(entry)
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.year == 2026

    def test_returns_none_when_no_time(self, ws):
        entry = MagicMock()
        entry.published_parsed = None
        entry.updated_parsed = None
        entry.created_parsed = None
        result = ws.parse_feed_entry_time(entry)
        assert result is None
