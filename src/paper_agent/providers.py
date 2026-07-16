from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from paper_agent.models import ModelProfile


class ModelError(RuntimeError):
    pass


def extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ModelError("模型响应不包含有效 JSON") from None
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ModelError(f"模型 JSON 解析失败：{exc}") from exc
    if not isinstance(data, dict):
        raise ModelError("模型 JSON 顶层必须是对象")
    return data


class ModelClient(ABC):
    def __init__(self, profile: ModelProfile):
        self.profile = profile

    @property
    def label(self) -> str:
        return f"{self.profile.provider}:{self.profile.model}"

    @abstractmethod
    def generate(self, *, system: str, prompt: str) -> str:
        raise NotImplementedError

    def generate_json(self, *, system: str, prompt: str) -> dict[str, Any]:
        return extract_json(self.generate(system=system, prompt=prompt))


class OpenAICompatibleClient(ModelClient):
    def generate(self, *, system: str, prompt: str) -> str:
        base_url = (self.profile.base_url or "https://api.openai.com/v1").rstrip("/")
        api_key = _api_key(self.profile)
        payload = {
            "model": self.profile.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.profile.temperature,
        }
        try:
            response = httpx.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=self.profile.timeout_seconds,
            )
            response.raise_for_status()
            return str(response.json()["choices"][0]["message"]["content"])
        except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
            raise ModelError(f"OpenAI-compatible 调用失败：{exc}") from exc


class AnthropicClient(ModelClient):
    def generate(self, *, system: str, prompt: str) -> str:
        base_url = (self.profile.base_url or "https://api.anthropic.com").rstrip("/")
        api_key = _api_key(self.profile)
        payload = {
            "model": self.profile.model,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.profile.temperature,
            "max_tokens": 8192,
        }
        try:
            response = httpx.post(
                f"{base_url}/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                json=payload,
                timeout=self.profile.timeout_seconds,
            )
            response.raise_for_status()
            content = response.json()["content"]
            return "\n".join(str(item["text"]) for item in content if item.get("type") == "text")
        except (httpx.HTTPError, KeyError, TypeError) as exc:
            raise ModelError(f"Anthropic 调用失败：{exc}") from exc


class DeterministicClient(ModelClient):
    """Offline client for tests and pipeline demonstrations, not final prose quality."""

    def generate(self, *, system: str, prompt: str) -> str:
        del system
        if "OUTPUT_KIND:PLAN" in prompt:
            return json.dumps(
                {
                    "research_question": "如何在给定资料范围内形成清晰、可验证的课程论文论证？",
                    "thesis": "高质量课程论文需要把任务约束、证据组织与递归修订结合起来。",
                },
                ensure_ascii=False,
            )
        if "OUTPUT_KIND:DRAFT_SECTION" in prompt:
            title = _extract_marker(prompt, "SECTION_TITLE") or "本节"
            purpose = _extract_marker(prompt, "SECTION_PURPOSE") or "完成本节论述"
            evidence = re.findall(r"\[(E-[A-Za-z0-9-]+)\]", prompt)
            citation = f" [E:{evidence[0]}]" if evidence else ""
            return (
                f"{title}围绕“{purpose}”展开。首先需要界定问题及其适用范围，"
                f"随后结合已有材料说明主要判断与理由。现有证据提示，论证质量不仅取决于观点，"
                f"也取决于证据与结论之间的解释过程。{citation}\n\n"
                "在此基础上，本节还需要说明可能的限制与替代解释，避免把条件性结论表述为普遍事实。"
                "该处理能够为后续章节提供明确接口，并使全文结论可以回溯到已知材料。"
            )
        return "{}"


def _extract_marker(prompt: str, name: str) -> str | None:
    match = re.search(rf"^{re.escape(name)}:\s*(.+)$", prompt, re.MULTILINE)
    return match.group(1).strip() if match else None


def _api_key(profile: ModelProfile) -> str:
    if not profile.api_key_env:
        raise ModelError("模型配置缺少 api_key_env")
    value = os.getenv(profile.api_key_env)
    if not value:
        raise ModelError(f"环境变量 {profile.api_key_env} 未设置")
    return value


def create_client(profile: ModelProfile) -> ModelClient:
    provider = profile.provider.lower()
    if provider in {"openai", "openai-compatible", "ollama", "deepseek", "qwen"}:
        return OpenAICompatibleClient(profile)
    if provider == "anthropic":
        return AnthropicClient(profile)
    if provider in {"deterministic", "offline"}:
        return DeterministicClient(profile)
    raise ModelError(f"未知模型供应商：{profile.provider}")
