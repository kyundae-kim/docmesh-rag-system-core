from __future__ import annotations

import dms
from sqlalchemy.engine import Engine


def create_dms_sdk_from_clients(
    *,
    engine: Engine,
    minio_client: object,
    bucket_name: str,
) -> dms.DefaultDocumentManagementSDK:
    """Create DMS from host-owned SQLAlchemy and MinIO clients.

    The injected clients remain caller-owned; this helper does not register
    them as SDK-owned resources.
    """
    return dms.DocumentManagementSDKFactory(
        engine=engine,
        minio_client=minio_client,
        bucket_name=bucket_name,
    ).create()


__all__ = [
    "create_dms_sdk_from_clients",
]
