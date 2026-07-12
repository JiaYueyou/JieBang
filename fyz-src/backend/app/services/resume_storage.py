from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.core.config import LOCAL_STORAGE_PATH
from app.core.exceptions import ResourceNotFoundError


class ResumeStorage:
    def __init__(self, root: str | Path = LOCAL_STORAGE_PATH) -> None:
        self.root = Path(root).resolve() / "resumes"

    def save(self, content: bytes, filename: str) -> tuple[str, str]:
        suffix = Path(filename).suffix.lower()
        key = f"resumes/{uuid4().hex}{suffix}"
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key, sha256(content).hexdigest()

    def path_for(self, key: str) -> Path:
        path = self._resolve(key)
        if not path.is_file():
            raise ResourceNotFoundError("简历原文件不存在")
        return path

    def remove(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()

    def _resolve(self, key: str) -> Path:
        relative = key.replace("\\", "/")
        if not relative.startswith("resumes/"):
            raise ResourceNotFoundError("简历存储键无效")
        path = (self.root.parent / relative).resolve()
        if self.root not in path.parents:
            raise ResourceNotFoundError("简历存储键无效")
        return path
