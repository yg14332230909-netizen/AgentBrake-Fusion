from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class FilterResult:
    decision: str
    risk_score: int
    labels: list[str]
    redacted_text: str
    reason: str


class RuleBasedModelFilter:
    """Small base-model input/output filter used by the local demo."""

    def __init__(
        self,
        secret_patterns: Iterable[str],
        *,
        input_ask_threshold: int = 4,
        input_block_threshold: int = 9,
        output_ask_threshold: int = 3,
        output_block_threshold: int = 5,
    ) -> None:
        self.secret_regexes = [re.compile(pattern) for pattern in secret_patterns]
        self.input_ask_threshold = input_ask_threshold
        self.input_block_threshold = input_block_threshold
        self.output_ask_threshold = output_ask_threshold
        self.output_block_threshold = output_block_threshold
        self.patterns: list[tuple[str, re.Pattern[str], int]] = [
            ("prompt_injection", re.compile(r"ignore (all )?(previous|prior)|忽略.*(之前|所有).*要求", re.I), 3),
            ("policy_override", re.compile(r"disable|关闭.*策略|绕过|bypass|无策略|unrestricted", re.I), 3),
            ("hidden_instruction", re.compile(r"assistant instruction|隐藏指令|不要告诉用户|不要解释", re.I), 2),
            ("secret_request", re.compile(r"secret|token|密钥|环境变量|secrets?\.env|系统提示|训练", re.I), 3),
            ("external_egress", re.compile(r"attacker@example\.test|attacker\.example\.test|外发|发送到", re.I), 3),
            ("tool_forcing", re.compile(r"按.*工具调用|JSON.*执行|直接执行|execute", re.I), 2),
        ]

    def scan_input(self, text: str) -> FilterResult:
        labels, score = self._score_text(text)
        decision = self._decision(score, self.input_ask_threshold, self.input_block_threshold)
        return FilterResult(decision, score, labels, self.redact(text), self._reason(labels, score))

    def scan_output(self, text: str) -> FilterResult:
        labels, score = self._score_text(text)
        for regex in self.secret_regexes:
            if regex.search(text):
                labels.append("secret_or_canary_output")
                score += 5
        decision = self._decision(score, self.output_ask_threshold, self.output_block_threshold)
        return FilterResult(decision, score, sorted(set(labels)), self.redact(text), self._reason(labels, score))

    def contains_secret(self, value: object) -> bool:
        text = self._to_text(value)
        return any(regex.search(text) for regex in self.secret_regexes)

    def redact(self, value: object) -> str:
        text = self._to_text(value)
        for regex in self.secret_regexes:
            text = regex.sub("[REDACTED_CANARY]", text)
        return text

    def _score_text(self, text: str) -> tuple[list[str], int]:
        labels: list[str] = []
        score = 0
        for label, regex, weight in self.patterns:
            if regex.search(text):
                labels.append(label)
                score += weight
        return sorted(set(labels)), score

    @staticmethod
    def _decision(score: int, ask_threshold: int, block_threshold: int) -> str:
        if score >= block_threshold:
            return "block"
        if score >= ask_threshold:
            return "ask"
        return "allow"

    @staticmethod
    def _reason(labels: list[str], score: int) -> str:
        if not labels:
            return "no suspicious model-level pattern matched"
        return f"matched {', '.join(sorted(set(labels)))}; risk_score={score}"

    @staticmethod
    def _to_text(value: object) -> str:
        if isinstance(value, str):
            return value
        return repr(value)
