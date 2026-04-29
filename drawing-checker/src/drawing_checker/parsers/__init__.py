# -*- coding: utf-8 -*-
"""パーサー群。拡張子別にモジュールを呼び分ける dispatch を経由することを推奨。"""
from . import dispatch  # noqa: F401

__all__ = ["dispatch"]
