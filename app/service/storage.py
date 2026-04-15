from __future__ import annotations

from functools import lru_cache

import boto3

from app.config import settings


@lru_cache(maxsize=1)
def get_s3_client():
    region = settings.AWS_REGION or None
    return boto3.client("s3", region_name=region)
