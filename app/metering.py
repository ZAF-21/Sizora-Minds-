"""
R4: Metering callback — counts tokens, seconds, and cost per agent/model call.
Even with free providers, judges need to see the cost table.
"""

from __future__ import annotations
import time
from langchain_core.callbacks import BaseCallbackHandler
from app.config import MODEL_COSTS


class Meter(BaseCallbackHandler):
    """Counts tokens, seconds and dollars for every model call that happens under it."""

    def __init__(self):
        self.calls: list[dict] = []
        self._open: dict = {}

    def on_chat_model_start(self, serialized, messages, *, run_id, **kw):
        inv = kw.get("invocation_params", {}) or {}
        meta = kw.get("metadata", {}) or {}
        model = inv.get("model") or inv.get("model_name") or meta.get("ls_model_name")
        self._open[run_id] = (time.perf_counter(), model)

    def on_llm_end(self, response, *, run_id, **kw):
        t0, model = self._open.pop(run_id, (time.perf_counter(), None))
        usage, msg = {}, None
        try:
            msg = response.generations[0][0].message
            usage = msg.usage_metadata or {}
        except Exception:
            pass
        if not model and msg is not None:
            model = (getattr(msg, "response_metadata", None) or {}).get("model_name")
        self.calls.append({
            "model": model or "unknown",
            "in": usage.get("input_tokens", 0),
            "out": usage.get("output_tokens", 0),
            "sec": time.perf_counter() - t0,
        })

    def on_llm_error(self, error, *, run_id, **kw):
        self._open.pop(run_id, None)

    def summary(self) -> dict:
        by_model: dict = {}
        for c in self.calls:
            m = by_model.setdefault(c["model"], {"calls": 0, "in": 0, "out": 0, "sec": 0.0, "usd": 0.0})
            prices = MODEL_COSTS.get(c["model"], {"input": 0.0, "output": 0.0})
            m["calls"] += 1
            m["in"] += c["in"]
            m["out"] += c["out"]
            m["sec"] += c["sec"]
            m["usd"] += (c["in"] * prices["input"] + c["out"] * prices["output"]) / 1e6
        total = {
            "calls": len(self.calls),
            "in": sum(c["in"] for c in self.calls),
            "out": sum(c["out"] for c in self.calls),
            "sec": sum(c["sec"] for c in self.calls),
            "usd": sum(m["usd"] for m in by_model.values()),
        }
        return {"by_model": by_model, "total": total}

    def print_summary(self, title: str = "Cost Table") -> None:
        s = self.summary()
        print(f"\n{'=' * 70}")
        print(f"  {title}")
        print(f"{'=' * 70}")
        for model, v in s["by_model"].items():
            print(f"  {model:30} calls={v['calls']:3}  in={v['in']:6}  out={v['out']:5}  ${v['usd']:.5f}  {v['sec']:.1f}s")
        t = s["total"]
        print(f"  {'TOTAL':30} calls={t['calls']:3}  in={t['in']:6}  out={t['out']:5}  ${t['usd']:.5f}  {t['sec']:.1f}s")
        print(f"{'=' * 70}\n")
