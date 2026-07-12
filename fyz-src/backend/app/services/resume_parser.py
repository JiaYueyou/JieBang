from __future__ import annotations

import io
from pathlib import Path

from app.core.exceptions import InvalidParameterError


class ResumeParser:
    version = "resume-parser-v1"
    allowed_suffixes = {".txt", ".md", ".pdf", ".docx"}

    def parse(self, content: bytes, filename: str) -> tuple[str, list[str]]:
        if not content:
            raise InvalidParameterError("简历文件为空")
        if len(content) > 20 * 1024 * 1024:
            raise InvalidParameterError("简历文件不能超过 20MB")
        suffix = Path(filename).suffix.lower()
        if suffix not in self.allowed_suffixes:
            raise InvalidParameterError("仅支持 TXT、Markdown、PDF 和 DOCX 简历")
        warnings: list[str] = []
        if suffix in {".txt", ".md"}:
            text = self._decode(content)
        elif suffix == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError as exc:
                raise InvalidParameterError("服务端未安装 PDF 解析依赖 pypdf") from exc
            text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
            if len(text.strip()) < 30:
                warnings.append("PDF 可能是扫描件，请人工确认解析内容。")
        else:
            try:
                from docx import Document
            except ImportError as exc:
                raise InvalidParameterError("服务端未安装 Word 解析依赖 python-docx") from exc
            text = "\n".join(p.text for p in Document(io.BytesIO(content)).paragraphs)
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())[:20000]
        if not text:
            raise InvalidParameterError("未能从简历中解析出文本")
        return text, warnings

    @staticmethod
    def _decode(content: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                pass
        raise InvalidParameterError("无法识别文本文件编码")
