# -*- coding: utf-8 -*-
"""
drawing-checker CLIエントリポイント

使い方：
  python -m drawing_checker check <file_or_dir>
  python -m drawing_checker check <file> --ai
  python -m drawing_checker learn <sample_dir_or_files>
  python -m drawing_checker --help
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from .checkers.dimension_checker import DimensionChecker
from .checkers.line_style_checker import LineStyleChecker
from .checkers.symbol_checker import SymbolChecker
from .checkers.title_block_checker import TitleBlockChecker
from .model import CheckReport
from .parsers import dispatch
from .reporter import html_reporter, pdf_annotator
from .rule_engine import RuleEngine
from .utils.logger import get_logger

logger = get_logger(__name__)


SUPPORTED_EXT = {".pdf", ".dxf", ".dwg", ".slddrw", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="drawing_checker",
        description="SolidWorks 2D図面の自動検図ツール",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # check コマンド
    p_check = sub.add_parser("check", help="検図を実行する")
    p_check.add_argument("target", help="対象ファイル or ディレクトリ")
    p_check.add_argument("--rules", type=Path, default=None,
                         help="カスタムルールJSONへのパス（learned_rules.json相当）")
    p_check.add_argument("--ai", action="store_true",
                         help="Gemini AI補完レイヤーを有効化")
    p_check.add_argument("--no-pdf", action="store_true",
                         help="PDF注釈出力をスキップ")
    p_check.add_argument("--no-html", action="store_true",
                         help="HTMLレポート出力をスキップ")
    p_check.add_argument("--json", action="store_true",
                         help="検図結果をJSON形式でstdoutに出力（Web/API連携用）")
    p_check.add_argument("--output-dir", type=Path, default=None,
                         help="PDF/HTMLの出力先ディレクトリ（既定：入力と同じ場所）")
    p_check.set_defaults(func=_cmd_check)

    # learn コマンド
    p_learn = sub.add_parser("learn", help="サンプル図面からルールを学習する")
    p_learn.add_argument("samples", nargs="+", help="サンプルファイルまたはディレクトリ")
    p_learn.add_argument("--no-ai", action="store_true", help="AI補完を使わずに統計のみで生成")
    p_learn.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent.parent / "config" / "learned_rules.json",
        help="出力先JSONパス",
    )
    p_learn.set_defaults(func=_cmd_learn)

    return p


# ----------------------------------------------------------------------
# check
# ----------------------------------------------------------------------
def _cmd_check(args: argparse.Namespace) -> int:
    target = Path(args.target)
    if not target.exists():
        _emit_json_error(args, f"対象が存在しません: {target}")
        logger.error("対象が存在しません: %s", target)
        return 2

    targets = _collect_files(target)
    if not targets:
        _emit_json_error(args, f"対応形式のファイルが見つかりません: {target}")
        logger.error("対応形式のファイルが見つかりません: %s", target)
        return 2

    rule_engine = RuleEngine(custom_rules_path=args.rules)
    checkers = [
        DimensionChecker(rule_engine),
        TitleBlockChecker(rule_engine),
        LineStyleChecker(rule_engine),
        SymbolChecker(rule_engine),
    ]

    overall_ok = True
    json_results: list[dict] = []
    for f in targets:
        ok, report, pdf_path = _check_single(f, checkers, args)
        overall_ok = overall_ok and ok
        if args.json:
            json_results.append(_report_to_dict(f, report, pdf_path))

    if args.json:
        _emit_json({"results": json_results, "pass": overall_ok})
    return 0 if overall_ok else 1


def _emit_json(payload: dict) -> None:
    """UTF-8でstdoutにJSONを書き出す（Windows cp932対策）"""
    import json as _json
    data = _json.dumps(payload, ensure_ascii=False)
    try:
        sys.stdout.buffer.write(data.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    except AttributeError:
        print(data)


def _report_to_dict(file_path: Path, report: "CheckReport", pdf_path: Path | None) -> dict:
    """CheckReportをJSON化（Web UI向け）"""
    # ページごとに座標とサイズも渡すと、フロント側でCanvasに赤丸重ねられる
    return {
        "drawing_path": str(file_path),
        "drawing_name": file_path.name,
        "checked_pdf_path": str(pdf_path) if pdf_path else None,
        "pass": report.is_pass,
        "errors_count": report.errors_count,
        "warnings_count": report.warnings_count,
        "info_count": report.info_count,
        "processing_time_sec": round(report.processing_time_sec, 3),
        "findings": [f.to_dict() for f in report.findings],
    }


def _emit_json_error(args: argparse.Namespace, message: str) -> None:
    if getattr(args, "json", False):
        _emit_json({"error": message, "results": [], "pass": False})


def _check_single(
    file_path: Path,
    checkers: list,
    args: argparse.Namespace,
) -> tuple[bool, CheckReport, Path | None]:
    logger.info("検図開始: %s", file_path)
    start = time.time()
    report = CheckReport(drawing_path=str(file_path))
    pdf_path: Path | None = None

    try:
        drawing = dispatch.parse(file_path)
    except Exception as e:
        logger.error("パース失敗 %s: %s", file_path, e)
        return False, report, None

    for checker in checkers:
        try:
            checker.check(drawing, report)
        except Exception as e:
            logger.exception("%s で例外: %s", checker.name, e)

    if getattr(args, "ai", False):
        try:
            from .ai import manufacturability
            manufacturability.run(drawing, report)
        except Exception as e:
            logger.warning("製作可能性チェック失敗: %s", e)

    report.processing_time_sec = time.time() - start

    output_dir = getattr(args, "output_dir", None)

    # 結果出力
    if not args.no_pdf:
        try:
            pdf_path = pdf_annotator.annotate(drawing, report, output_dir=output_dir)
            logger.info("→ 注釈PDF: %s", pdf_path)
        except Exception as e:
            logger.exception("PDF注釈出力失敗: %s", e)

    if not args.no_html:
        try:
            html_path = html_reporter.write(report, output_dir=output_dir)
            logger.info("→ HTMLレポート: %s", html_path)
        except Exception as e:
            logger.exception("HTML出力失敗: %s", e)

    logger.info(
        "検図完了: %s | ERROR:%d WARNING:%d INFO:%d | %s | %.2f秒",
        file_path.name,
        report.errors_count,
        report.warnings_count,
        report.info_count,
        "合格" if report.is_pass else "不合格",
        report.processing_time_sec,
    )
    return report.is_pass, report, pdf_path


def _collect_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() in SUPPORTED_EXT else []
    return sorted(
        p for p in target.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXT
    )


# ----------------------------------------------------------------------
# learn
# ----------------------------------------------------------------------
def _cmd_learn(args: argparse.Namespace) -> int:
    samples: list[Path] = []
    for s in args.samples:
        p = Path(s)
        if p.is_dir():
            samples.extend(
                [q for q in p.rglob("*") if q.is_file() and q.suffix.lower() in SUPPORTED_EXT]
            )
        elif p.is_file():
            samples.append(p)
        else:
            logger.warning("存在しないサンプル: %s", s)

    if not samples:
        logger.error("サンプルファイルが1つも見つかりません")
        return 2

    from .ai import rule_learner
    rule_learner.learn(samples, args.output, use_ai=not args.no_ai)
    return 0


# ----------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
