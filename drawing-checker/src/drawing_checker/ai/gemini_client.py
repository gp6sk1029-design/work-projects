# -*- coding: utf-8 -*-
"""
Gemini API クライアント（2.5 Flash 使用）

- AI補完レイヤー（違和感検出）とルール学習モードで共通利用
- APIキーがない/ライブラリ未インストール時は静かに失敗（警告ログのみ）
- JSONパース失敗時はフォールバック（media-transcriberの教訓）
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)


MODEL_NAME = "gemini-2.5-flash"


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._client = None
        if not self.api_key:
            logger.warning("GEMINI_API_KEY が未設定のため、AI機能は無効です。")
            return
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        except ImportError:
            logger.warning("google-genai が未インストールのため、AI機能は無効です。")
            self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    # ------------------------------------------------------------------
    def generate_text(self, prompt: str, *, temperature: float = 0.2) -> str:
        if not self.available:
            return ""
        try:
            resp = self._client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={"temperature": temperature},
            )
            return resp.text or ""
        except Exception as e:
            logger.warning("Gemini呼び出し失敗: %s", e)
            return ""

    def generate_json(self, prompt: str, *, temperature: float = 0.2) -> Any:
        """JSONを返すよう指示してパース。失敗時は None。"""
        full_prompt = prompt + "\n\n必ず JSON だけを返してください。説明文や```は不要です。"
        text = self.generate_text(full_prompt, temperature=temperature)
        if not text:
            return None
        return _parse_json_robust(text)

    # ------------------------------------------------------------------
    def generate_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/png",
        *,
        temperature: float = 0.2,
    ) -> str:
        """画像＋テキストを入力にして応答テキストを得る"""
        if not self.available:
            return ""
        try:
            from google.genai import types
            resp = self._client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
                config={"temperature": temperature},
            )
            return resp.text or ""
        except Exception as e:
            logger.warning("Gemini画像呼び出し失敗: %s", e)
            return ""

    def generate_json_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/png",
        *,
        temperature: float = 0.2,
    ) -> Any:
        """画像入力でJSON応答"""
        full_prompt = prompt + "\n\n必ず JSON だけを返してください。説明文や```は不要です。"
        text = self.generate_with_image(
            full_prompt, image_bytes, mime_type, temperature=temperature,
        )
        if not text:
            return None
        return _parse_json_robust(text)


def _parse_json_robust(text: str) -> Any:
    """コードブロック混入や前後の説明文を除去してJSONパースする"""
    # コードブロック除去
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # オブジェクトの最初と最後の { } で囲まれる部分を抜き出して再試行
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    logger.warning("Geminiの応答をJSONパースできませんでした: %s", text[:200])
    return None
