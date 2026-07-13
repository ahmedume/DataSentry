from __future__ import annotations

import io
import json
import os
import re
from abc import ABC, abstractmethod
from typing import Tuple

import pandas as pd

# Supported connector types. Keep in sync with Connector.type column.
LOCAL = "local"
POSTGRES = "postgres"
S3 = "s3"

REDACTED_KEYS = {"password", "secret", "secret_key", "access_key", "token", "api_key"}


def redact_config(config: dict) -> dict:
    """Return a copy with secret values masked (for API responses)."""
    out = {}
    for k, v in (config or {}).items():
        if any(s in k.lower() for s in REDACTED_KEYS):
            out[k] = "********" if v else v
        else:
            out[k] = v
    return out


class SourceConnector(ABC):
    def __init__(self, config: dict):
        self.config = config or {}

    @abstractmethod
    def pull(self) -> Tuple[bytes, str]:
        """Return (csv_bytes, suggested_filename)."""

    @abstractmethod
    def test(self) -> bool:
        """Verify the source is reachable / query valid."""


class LocalFileConnector(SourceConnector):
    def _resolve_path(self) -> str:
        path = self.config.get("path", "")
        if not path:
            raise ValueError("Local connector requires 'path'.")
        path = os.path.abspath(os.path.normpath(path))
        if os.path.isdir(path):
            csvs = sorted(f for f in os.listdir(path) if f.lower().endswith(".csv"))
            if not csvs:
                raise ValueError("No .csv files found in directory.")
            return os.path.join(path, csvs[0])
        return path

    def pull(self) -> Tuple[bytes, str]:
        p = self._resolve_path()
        if not os.path.exists(p):
            raise FileNotFoundError(f"File not found: {p}")
        with open(p, "rb") as f:
            return f.read(), os.path.basename(p)

    def test(self) -> bool:
        try:
            return os.path.exists(self._resolve_path())
        except Exception:
            return False


class PostgresConnector(SourceConnector):
    def _engine(self):
        try:
            from sqlalchemy import create_engine  # local import keeps dep optional
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("sqlalchemy is required for postgres connectors.") from e
        cfg = self.config
        uri = (
            f"postgresql+psycopg://{cfg.get('user','')}:{cfg.get('password','')}"
            f"@{cfg.get('host','localhost')}:{cfg.get('port',5432)}/{cfg.get('database','')}"
        )
        return create_engine(uri)

    def _query(self) -> str:
        q = self.config.get("query")
        if q:
            return q
        table = self.config.get("table", "")
        if not table:
            raise ValueError("Postgres connector requires 'query' or 'table'.")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
            raise ValueError(f"Invalid table name: {table!r}")
        return f"SELECT * FROM {table}"

    def pull(self) -> Tuple[bytes, str]:
        df = pd.read_sql(self._query(), self._engine())
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        name = self.config.get("name") or f"{self.config.get('table','query')}.csv"
        return buf.getvalue().encode("utf-8"), name

    def test(self) -> bool:
        try:
            with self._engine().connect() as conn:
                conn.execution_options()  # noqa
            return True
        except Exception:
            return False


class S3Connector(SourceConnector):
    def _client(self):
        try:
            import boto3  # local import keeps dep optional
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("boto3 is required for S3 connectors.") from e
        cfg = self.config
        return boto3.client(
            "s3",
            endpoint_url=cfg.get("endpoint_url"),
            aws_access_key_id=cfg.get("access_key"),
            aws_secret_access_key=cfg.get("secret_key"),
            region_name=cfg.get("region", "us-east-1"),
        )

    def _key(self) -> str:
        key = self.config.get("key")
        if key:
            return key
        prefix = self.config.get("prefix", "")
        bucket = self.config.get("bucket")
        client = self._client()
        objs = client.list_objects_v2(Bucket=bucket, Prefix=prefix).get("Contents", [])
        if not objs:
            raise ValueError("No objects found under prefix.")
        return sorted(objs, key=lambda o: o["LastModified"])[-1]["Key"]

    def pull(self) -> Tuple[bytes, str]:
        client = self._client()
        bucket = self.config.get("bucket")
        key = self._key()
        obj = client.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read(), key.split("/")[-1]

    def test(self) -> bool:
        try:
            self._client().list_buckets()
            return True
        except Exception:
            return False


_REGISTRY = {LOCAL: LocalFileConnector, POSTGRES: PostgresConnector, S3: S3Connector}


def build_connector(connector_type: str, config: dict) -> SourceConnector:
    cls = _REGISTRY.get(connector_type)
    if not cls:
        raise ValueError(f"Unknown connector type: {connector_type}")
    return cls(config)


def parse_config(raw: str | dict) -> dict:
    if isinstance(raw, dict):
        return raw
    return json.loads(raw or "{}")
