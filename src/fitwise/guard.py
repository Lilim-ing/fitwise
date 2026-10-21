"""Refusal and injection defence.

Two rules that matter:
  1. Out-of-scope questions get a refusal, not a plausible guess.
  2. The refusal text never reveals which rule fired -- that is a map for the
     next attempt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

INJECTION_PATTERNS = [
    (r"(?i)ignore\s+(all\s+|the\s+)?(previous|above)\s+(instructions?|prompts?)", "ignore-instructions"),
    (r"(?i)(system|assistant)\s*[:：]\s*", "role-marker"),
    (r"(?i)(you\s+are\s+now|act\s+as|pretend\s+to\s+be)", "role-play"),
    (r"(你现在是|你现在扮演|假装你是|忽略(之前|上面)的(指令|提示))", "role-play-zh"),
    (r"<\|[^|]{0,40}\|>", "special-token"),
    (r"(?i)repeat\s+(the\s+)?(system|prompt|instructions)", "prompt-leak"),
]

MEDICAL_PATTERNS = [
    (r"(治疗|诊断|处方|用药|吃什么药|能治|会不会癌变)", "medical-advice"),
    (r"(乳腺炎|乳腺增生|结节|肿瘤|癌)", "medical-condition"),
]

# Questions that look in-scope but are actually about someone else's body in a
# way we cannot verify; the assistant should ask for measurements instead.
OUT_OF_SCOPE = [
    (r"(减肥|丰胸|矫正|塑形效果)", "unverifiable-claim"),
]


@dataclass
class GuardResult:
    action: str  # "allow" | "refuse"
    code: str = ""
    reply: str = ""

    @property
    def allowed(self) -> bool:
        return self.action == "allow"


REFUSAL_MEDICAL = (
    "这个问题涉及医疗判断，超出我能回答的范围。"
    "如果出现疼痛、肿块、异常分泌物等情况，建议尽快就医，由医生面诊判断。"
    "尺码与穿着相关的问题我可以继续帮你。"
)

REFUSAL_GENERIC = (
    "这个问题不在我的知识范围内（我只覆盖尺码测量、合身判断、面料与保养）。"
    "你可以换个问法，或者提供下胸围与上胸围的具体数值，我帮你算尺码。"
)


def check(question: str) -> GuardResult:
    text = str(question or "")
    for pattern, code in INJECTION_PATTERNS:
        if re.search(pattern, text):
            # Generic refusal on purpose: do not confirm which pattern matched.
            return GuardResult("refuse", code, REFUSAL_GENERIC)
    for pattern, code in MEDICAL_PATTERNS:
        if re.search(pattern, text):
            return GuardResult("refuse", code, REFUSAL_MEDICAL)
    for pattern, code in OUT_OF_SCOPE:
        if re.search(pattern, text):
            return GuardResult("refuse", code, REFUSAL_GENERIC)
    return GuardResult("allow")
