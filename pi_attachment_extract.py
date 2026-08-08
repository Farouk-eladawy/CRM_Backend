"""
MarkItDown-backed attachment extractor for Create with PI.

Converts uploaded files/images into Markdown text that can be injected into
the Pi agent prompt, so DeepSeek (non-vision) can still reason over content.

OpenAI Vision is OPT-IN only (enable_vision=True). By default we never call
OpenAI, because Create with PI is configured to run on DeepSeek credits.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Soft cap so huge PDFs/Excel dumps do not blow the LLM context.
MAX_EXTRACT_CHARS_PER_FILE = 60_000
MAX_TOTAL_EXTRACT_CHARS = 180_000

_BILLING_MARKERS = (
    "no credits remaining",
    "insufficient_quota",
    "billing",
    "exceeded your current quota",
    "rate limit",
    "429",
)


def markitdown_available() -> bool:
    try:
        from markitdown import MarkItDown  # noqa: F401
        return True
    except Exception:
        return False


def _is_billing_or_quota_error(err: Exception) -> bool:
    msg = str(err or "").lower()
    return any(m in msg for m in _BILLING_MARKERS)


def _build_converter(openai_api_key: Optional[str] = None, vision_model: str = "gpt-4o", enable_vision: bool = False):
    """
    Build a MarkItDown instance.
    Vision/LLM image description is only enabled when enable_vision=True AND a key is provided.
    """
    from markitdown import MarkItDown

    kwargs: Dict[str, Any] = {}
    if enable_vision and openai_api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_api_key)
            kwargs["llm_client"] = client
            kwargs["llm_model"] = vision_model or "gpt-4o"
        except Exception as e:
            logger.warning("MarkItDown LLM client setup failed; continuing without vision: %s", e)

    return MarkItDown(**kwargs)


def _truncate(text: str, limit: int) -> Tuple[str, bool]:
    raw = (text or "").strip()
    if len(raw) <= limit:
        return raw, False
    return raw[: max(0, limit - 80)].rstrip() + "\n\n…[truncated by Create with PI extractor]", True


def _basic_image_fallback(path: str, name: str) -> str:
    """Lightweight image metadata when Vision LLM is disabled/unavailable."""
    lines = [
        f"Image file: {name}",
        f"Path: `{path}`",
        "Note: OpenAI Vision is disabled for Create with PI (DeepSeek-only mode). "
        "Describe what you need from this image in text, or enable "
        "`ai.create_with_pi.enable_openai_vision` in config.json after adding OpenAI credits.",
    ]
    try:
        from PIL import Image
        with Image.open(path) as im:
            lines.append(f"Format: {im.format or 'unknown'}")
            lines.append(f"Size: {im.width}x{im.height}")
            lines.append(f"Mode: {im.mode}")
            exif = getattr(im, "getexif", lambda: None)()
            if exif:
                lines.append(f"EXIF tags: {len(exif)}")
    except Exception as e:
        lines.append(f"Metadata read note: {e}")
    return "\n".join(lines)


def _convert_one(converter, path: str) -> str:
    if hasattr(converter, "convert_local"):
        conversion = converter.convert_local(path)
    else:
        conversion = converter.convert(path)

    if conversion is None:
        return ""
    if hasattr(conversion, "text_content"):
        return str(conversion.text_content or "")
    return str(conversion or "")


def extract_attachments(
    attachments: List[Dict[str, Any]],
    openai_api_key: Optional[str] = None,
    vision_model: str = "gpt-4o",
    enable_vision: bool = False,
) -> Dict[str, Any]:
    """
    Extract Markdown from a list of saved attachment dicts.

    Each attachment is expected to include at least:
      - path (absolute)
      - original_name
      - is_image (optional)
    """
    vision_on = bool(enable_vision and openai_api_key)
    result: Dict[str, Any] = {
        "available": False,
        "engine": None,
        "vision_enabled": vision_on,
        "files": [],
        "combined_markdown": "",
        "ok_count": 0,
        "fail_count": 0,
    }

    if not attachments:
        result["available"] = True
        result["engine"] = "markitdown"
        return result

    if not markitdown_available():
        result["fail_count"] = len(attachments)
        for a in attachments:
            # Still provide image metadata fallback without MarkItDown
            name = a.get("original_name") or os.path.basename(a.get("path") or "")
            path = a.get("path") or ""
            if a.get("is_image") and path and os.path.exists(path):
                text = _basic_image_fallback(path, name)
                result["files"].append({
                    "name": name,
                    "ok": True,
                    "chars": len(text),
                    "truncated": False,
                    "error": "markitdown missing; used basic image metadata",
                    "preview": text[:240],
                    "is_image": True,
                })
                result["ok_count"] += 1
                result["combined_markdown"] = (
                    (result["combined_markdown"] + "\n\n---\n\n" if result["combined_markdown"] else "")
                    + f"### Attachment: {name} (image)\n\n{text}"
                )
            else:
                result["files"].append({
                    "name": name,
                    "ok": False,
                    "chars": 0,
                    "truncated": False,
                    "error": "markitdown is not installed. Run: pip install 'markitdown[pdf,docx,pptx,xlsx]'",
                    "preview": "",
                    "is_image": bool(a.get("is_image")),
                })
                result["fail_count"] += 1
        if result["combined_markdown"]:
            result["combined_markdown"] = (
                "[MarkItDown Extraction]\n"
                "The following content was extracted from user attachments.\n\n"
                + result["combined_markdown"]
            )
            result["available"] = True
            result["engine"] = "basic-fallback"
        return result

    try:
        converter = _build_converter(
            openai_api_key=openai_api_key if vision_on else None,
            vision_model=vision_model,
            enable_vision=vision_on,
        )
        # Always keep a no-vision converter for billing fallback / images without LLM
        converter_no_vision = (
            _build_converter(enable_vision=False)
            if vision_on
            else converter
        )
    except Exception as e:
        logger.error("Failed to initialize MarkItDown: %s", e, exc_info=True)
        result["fail_count"] = len(attachments)
        for a in attachments:
            result["files"].append({
                "name": a.get("original_name") or "file",
                "ok": False,
                "chars": 0,
                "truncated": False,
                "error": f"MarkItDown init failed: {e}",
                "preview": "",
                "is_image": bool(a.get("is_image")),
            })
        return result

    result["available"] = True
    result["engine"] = "markitdown"

    remaining_budget = MAX_TOTAL_EXTRACT_CHARS
    blocks: List[str] = []

    for a in attachments:
        name = a.get("original_name") or os.path.basename(a.get("path") or "file")
        path = a.get("path") or ""
        is_image = bool(a.get("is_image"))
        entry = {
            "name": name,
            "ok": False,
            "chars": 0,
            "truncated": False,
            "error": "",
            "preview": "",
            "is_image": is_image,
        }

        if remaining_budget <= 0:
            entry["error"] = "Skipped: total extraction budget exhausted"
            result["files"].append(entry)
            result["fail_count"] += 1
            continue

        if not path or not os.path.exists(path):
            entry["error"] = "File path missing or not found"
            result["files"].append(entry)
            result["fail_count"] += 1
            continue

        text = ""
        used = "markitdown"
        try:
            text = _convert_one(converter, path)
        except Exception as e:
            if vision_on and _is_billing_or_quota_error(e):
                logger.warning("OpenAI Vision billing/quota error for %s; retrying without vision: %s", name, e)
                result["vision_enabled"] = False
                try:
                    text = _convert_one(converter_no_vision, path)
                    used = "markitdown-no-vision"
                except Exception as e2:
                    logger.warning("MarkItDown no-vision retry failed for %s: %s", name, e2)
                    text = ""
                    entry["error"] = f"Vision quota exhausted; fallback failed: {e2}"
            else:
                logger.warning("MarkItDown failed for %s: %s", name, e, exc_info=True)
                entry["error"] = str(e)

        # Images often return little/no text without vision — add metadata fallback
        if is_image and not (text or "").strip():
            text = _basic_image_fallback(path, name)
            used = "image-metadata"
            if not entry["error"]:
                entry["error"] = ""

        per_file_limit = min(MAX_EXTRACT_CHARS_PER_FILE, remaining_budget)
        text, truncated = _truncate(text, per_file_limit)
        entry["truncated"] = truncated
        entry["chars"] = len(text)
        entry["preview"] = text[:240]
        entry["ok"] = bool(text.strip())
        if used != "markitdown" and entry["ok"] and not entry["error"]:
            entry["error"] = f"extracted via {used}"

        if not text.strip():
            if not entry["error"]:
                entry["error"] = "No extractable text (empty conversion)"
            result["fail_count"] += 1
        else:
            result["ok_count"] += 1
            remaining_budget -= len(text)
            kind = "image" if is_image else "file"
            blocks.append(
                f"### Attachment: {name} ({kind})\n"
                f"Source path: `{path}`\n"
                f"Extractor: {used}\n\n"
                f"{text}"
            )

        result["files"].append(entry)

    if blocks:
        header = (
            "[MarkItDown Extraction]\n"
            "The following content was extracted from user attachments. "
            "Treat it as the primary evidence for analysis. "
            "Do not invent content that is not present below.\n"
        )
        result["combined_markdown"] = header + "\n\n---\n\n".join(blocks)

    return result


def build_prompt_extraction_section(extraction: Dict[str, Any]) -> str:
    """Format extraction result for injection into the Pi prompt."""
    if not extraction:
        return ""

    if extraction.get("combined_markdown"):
        return "\n\n" + extraction["combined_markdown"]

    files = extraction.get("files") or []
    if not files:
        return ""

    lines = ["\n\n[MarkItDown Extraction Status]"]
    if not extraction.get("available"):
        lines.append("- MarkItDown is not installed or failed to initialize.")
    for f in files:
        status = "OK" if f.get("ok") else f"FAILED ({f.get('error') or 'unknown'})"
        lines.append(f"- {f.get('name')}: {status}")
    lines.append(
        "Original binary files are still attached via @path if the agent can read them."
    )
    return "\n".join(lines)
