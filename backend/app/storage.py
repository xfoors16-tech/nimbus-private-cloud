import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings


class ObjectStorage:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = None
        if self.settings.storage_backend == "s3":
            self.client = boto3.client(
                "s3",
                endpoint_url=self.settings.s3_endpoint_url,
                region_name=self.settings.s3_region,
                aws_access_key_id=self.settings.s3_access_key,
                aws_secret_access_key=self.settings.s3_secret_key,
            )
            try:
                self.client.head_bucket(Bucket=self.settings.s3_bucket)
            except ClientError:
                self.client.create_bucket(Bucket=self.settings.s3_bucket)
        else:
            self.settings.storage_root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.settings.storage_root / key

    def put(self, key: str, content: bytes, content_type: str) -> None:
        if self.client:
            self.client.put_object(
                Bucket=self.settings.s3_bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
        else:
            path = self._path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

    def get(self, key: str) -> bytes:
        if self.client:
            response = self.client.get_object(Bucket=self.settings.s3_bucket, Key=key)
            return response["Body"].read()
        return self._path(key).read_bytes()

    def stream(self, key: str, chunk_size: int = 64 * 1024):
        if self.client:
            body = self.client.get_object(Bucket=self.settings.s3_bucket, Key=key)["Body"]
            try:
                while chunk := body.read(chunk_size):
                    yield chunk
            finally:
                body.close()
            return
        with self._path(key).open("rb") as source:
            while chunk := source.read(chunk_size):
                yield chunk

    def delete(self, key: str) -> None:
        if self.client:
            self.client.delete_object(Bucket=self.settings.s3_bucket, Key=key)
        else:
            try:
                os.remove(self._path(key))
            except FileNotFoundError:
                pass


storage = ObjectStorage()
