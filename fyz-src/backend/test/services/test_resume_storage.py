from pathlib import Path

import pytest

from app.core.exceptions import ResourceNotFoundError
from app.services.resume_storage import ResumeStorage


def test_competition_resume_asset_is_readable(tmp_path: Path) -> None:
    storage = ResumeStorage(tmp_path)
    target = tmp_path / "competition" / "resume-01.pdf"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"pdf")

    assert storage.path_for("competition/resume-01.pdf") == target


def test_uploaded_resume_still_uses_resumes_namespace(tmp_path: Path) -> None:
    storage = ResumeStorage(tmp_path)

    key, _ = storage.save(b"resume", "candidate.pdf")

    assert key.startswith("resumes/")
    assert storage.path_for(key).read_bytes() == b"resume"


@pytest.mark.parametrize(
    "key",
    ["other/resume.pdf", "competition/../../outside.pdf", "resumes/../../outside.pdf"],
)
def test_resume_storage_rejects_unapproved_or_traversing_keys(
    tmp_path: Path, key: str
) -> None:
    storage = ResumeStorage(tmp_path)

    with pytest.raises(ResourceNotFoundError, match="简历存储键无效"):
        storage.path_for(key)
