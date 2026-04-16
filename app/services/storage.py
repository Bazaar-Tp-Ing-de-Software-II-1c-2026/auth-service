from __future__ import annotations

from functools import lru_cache

import boto3

from app.config import settings


@lru_cache(maxsize=1)
def get_s3_client():
    region = settings.AWS_REGION or None
    aws_access_key_id = settings.AWS_ACCESS_KEY_ID or None
    aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY or None
    return boto3.client(
    "s3",
    region_name=region, 
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    )
