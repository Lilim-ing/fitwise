"""Answer assembly: retrieval + deterministic sizing, no free-form generation.

Every sentence in the reply either comes from a knowledge entry (with its
source) or from the sizing function (with its arithmetic shown). Nothing is
paraphrased into a claim that cannot be traced.
"""

from __future__ import annotations

import re

from . import sizing
from .guard import check
from .knowledge import KnowledgeBase

SIZE_PATTERN = re.compile(r"(?<!\d)(\d{2,3})\s*([A-G]{1,2})(?!\w)", re.IGNORECASE)
MEASURE_PATTERN = re.compile(r"下胸围\s*[:：]?\s*(\d{2,3}(?:\.\d)?).{0,12}?上胸围\s*[:：]?\s*(\d{2,3}(?:\.\d)?)")
MIN_SCORE = 0.12


def _format_sizing(result: sizing.FitResult) -> str:
    lines = [
        f"按你给的测量值（围差 {result.diff_cm}cm），推荐尺码 **{result.size}**。",
    ]
    if result.sister_sizes:
        lines.append(f"姐妹尺码：{' / '.join(result.sister_sizes)}（罩杯容量相近，底围不同）。")
    if result.confidence != "high":
        lines.append(f"置信度：{result.confidence}。")
    lines.extend(result.notes)
    lines.append("围差法给的是起点，胸型与底盘宽度会影响最终合身度，建议同区间试 2-3 个尺码。")
    return "\n".join(lines)


def _format_sister(size_text: str) -> tuple[str, sizing.FitResult | None]:
    parsed = sizing.parse_size(size_text)
    if not parsed:
        return "", None
    band, cup = parsed
    cup_index = sizing.CUPS.index(cup)
    sisters = sizing.sister_sizes(band, cup_index)
    if not sisters:
        return f"{band}{cup} 处于尺码表边界，没有相邻的姐妹尺码。", None
    return (
        f"{band}{cup} 的姐妹尺码是 {' / '.join(sisters)}。"
        "姐妹尺码罩杯容量相近、底围不同：底围小一档罩杯升一级，反之亦然。",
        None,
    )


def answer(
    question: str,
    kb: KnowledgeBase,
    underbust: float | None = None,
    bust: float | None = None,
) -> dict:
    guard = check(question)
    if guard.action == "refuse":
        return {
            "ok": False,
            "refused": True,
            "reason": guard.code,
            "answer": guard.reply,
            "citations": [],
            "sizing": None,
        }

    sections: list[str] = []
    citations: list[dict] = []
    sizing_payload = None

    # 1) measurements present -> compute
    if underbust is not None and bust is not None:
        result = sizing.compute(underbust, bust)
        if result.ok:
            sections.append(_format_sizing(result))
            sizing_payload = result.to_dict()
        else:
            sections.append("测量值看起来不对：" + "；".join(result.notes))

    # 2) explicit size in the question -> sister sizes
    match = SIZE_PATTERN.search(question)
    if match and sizing_payload is None:
        text, _ = _format_sister(f"{match.group(1)}{match.group(2).upper()}")
        if text:
            sections.append(text)
            citations.append(
                {
                    "id": "kb-004",
                    "title": "姐妹尺码是什么",
                    "source": "尺码手册 v1.2 §2.5",
                    "score": 1.0,
                }
            )

    # 3) retrieval
    hits = kb.search(question, k=3)
    strong = [h for h in hits if h.score >= MIN_SCORE]
    if strong:
        for hit in strong[:2]:
            sections.append(f"**{hit.title}**：{hit.content}")
            citations.append(
                {"id": hit.id, "title": hit.title, "source": hit.source, "score": round(hit.score, 4)}
            )

    if not sections:
        detail = (
            f"（检索最高相关度 {hits[0].score:.2f}，低于 {MIN_SCORE} 的采纳阈值）" if hits else ""
        )
        return {
            "ok": False,
            "refused": True,
            "reason": "no_relevant_knowledge",
            "answer": (
                "我在知识库里没有找到与这个问题直接相关的内容。"
                "可以试试问：尺码怎么算、姐妹尺码、底围松紧、面料保养。" + detail
            ),
            "citations": [],
            "sizing": None,
        }

    body = "\n\n".join(sections)
    if citations:
        sources = "、".join(sorted({c["source"] for c in citations}))
        body += f"\n\n依据：{sources}"

    return {
        "ok": True,
        "refused": False,
        "reason": "",
        "answer": body,
        "citations": citations,
        "sizing": sizing_payload,
    }
