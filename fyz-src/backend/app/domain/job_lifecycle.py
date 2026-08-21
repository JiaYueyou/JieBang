"""Shared predicates for projecting only the current external-job version."""

from sqlalchemy import and_, exists, or_, select

from app.models import ExternalJobIdentity, ExternalJobVersion, SourceDocument


def current_external_job_condition():
    """Keep legacy rows, but only the active current version for lifecycle-aware rows."""
    return or_(
        SourceDocument.external_job_identity_id.is_(None),
        exists(
            select(1)
            .select_from(ExternalJobIdentity)
            .join(
                ExternalJobVersion,
                ExternalJobVersion.id == ExternalJobIdentity.current_version_id,
            )
            .where(
                and_(
                    ExternalJobIdentity.id == SourceDocument.external_job_identity_id,
                    ExternalJobIdentity.lifecycle_status == "active",
                    ExternalJobVersion.source_document_id == SourceDocument.id,
                    ExternalJobVersion.is_current.is_(True),
                )
            )
        ),
    )
