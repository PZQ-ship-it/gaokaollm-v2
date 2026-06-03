import asyncio
from types import SimpleNamespace

import pytest

from app.core.llm_client import (
    ainvoke_text_with_timeout,
    reset_text_stream_callback,
    set_text_stream_callback,
)


class FakeStreamingRunnable:
    def __init__(self, chunks: list[str], *, delay: float) -> None:
        self.chunks = chunks
        self.delay = delay

    async def astream(self, messages):
        for chunk in self.chunks:
            await asyncio.sleep(self.delay)
            yield SimpleNamespace(content=chunk)


@pytest.mark.asyncio
async def test_stream_timeout_is_idle_timeout_not_total_deadline():
    emitted: list[str] = []
    token = set_text_stream_callback(lambda delta, label: emitted.append(delta))
    try:
        text = await ainvoke_text_with_timeout(
            FakeStreamingRunnable(["甲", "乙", "丙", "丁"], delay=0.02),
            [],
            timeout=0.05,
            label="fake_stream",
        )
    finally:
        reset_text_stream_callback(token)

    assert text == "甲乙丙丁"
    assert emitted == ["甲", "乙", "丙", "丁"]


@pytest.mark.asyncio
async def test_stream_timeout_reports_stalled_stream():
    token = set_text_stream_callback(lambda delta, label: None)
    try:
        with pytest.raises(TimeoutError, match="fake_stream stream stalled"):
            await ainvoke_text_with_timeout(
                FakeStreamingRunnable(["甲"], delay=0.05),
                [],
                timeout=0.01,
                label="fake_stream",
            )
    finally:
        reset_text_stream_callback(token)
