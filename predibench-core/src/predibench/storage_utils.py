"""
All of the data is stored in a bucket shared by all of the instances of the webportal crawlers.

For local development, the data is stored in the data directory.

This module contains utility functions for interacting with Google Cloud Storage.
"""

import json
import os
import uuid
from functools import cache
from pathlib import Path

from google.api_core.exceptions import ClientError
from google.cloud import storage

from predibench.common import DATA_PATH
from predibench.logger_config import get_logger

logger = get_logger(__name__)

BUCKET_ENV_VAR = "BUCKET_PREDIBENCH"

try:
    bucket_json_key = os.getenv("BUCKET_JSON_KEY")
    if bucket_json_key:
        credentials_info = json.loads(bucket_json_key)
        STORAGE_CLIENT = storage.Client.from_service_account_info(credentials_info)
    else:
        STORAGE_CLIENT = storage.Client()
except Exception as e:
    logger.error(f"Error initializing storage client: {e}")
    STORAGE_CLIENT = None


@cache
def get_bucket() -> storage.Bucket | None:
    if STORAGE_CLIENT is None:
        return None

    if BUCKET_ENV_VAR not in os.environ:
        print(
            f"To enable bucket access please set the {BUCKET_ENV_VAR} environment variable, defaulting to data directory."
        )
        return None

    bucket_name = os.getenv(BUCKET_ENV_VAR)
    return STORAGE_CLIENT.bucket(bucket_name)


@cache
def has_bucket_write_access() -> bool:
    """
    Check if the bucket is set and working with write access.

    If not set, the data is stored in the data directory.

    If set but not working, raising an error.
    """

    bucket = get_bucket()
    if bucket is None:
        return False

    try:
        random_string = str(uuid.uuid4())
        blob = bucket.blob(f"ping/ping_{random_string}.txt")
        blob.upload_from_string("ping")
        file_content = blob.download_as_bytes().decode("utf-8")
        assert file_content == "ping"
        blob.delete()
        return True
    except ClientError as e:
        print(f"Error accessing bucket {bucket.name}: {e}")
        raise e
    except AssertionError as e:
        print(
            f"Error while uploading file: {e}, file content is {file_content}, not 'ping'"
        )
        raise e
    except Exception as e:
        print(f"Error accessing bucket {bucket.name}: {e}")
        return False


@cache
def has_bucket_read_access() -> bool:
    """
    Check if the bucket is set and working with read access only.

    If not set, the data is stored in the data directory.

    If set but not working, raising an error.
    """

    bucket = get_bucket()
    if bucket is None:
        return False

    try:
        # Just try to list some blobs to test read access
        list(bucket.list_blobs(max_results=1))
        return True
    except ClientError as e:
        print(f"Error accessing bucket {bucket.name}: {e}")
        raise e
    except Exception as e:
        print(f"Error accessing bucket {bucket.name}: {e}")
        return False


def _write_file_to_bucket_or_data_dir(file_path: Path, blob_name: str) -> bool:
    """
    Upload a local file to bucket if available, and also save locally for debugging.
    """
    # Always save locally for debugging
    local_dest = DATA_PATH / blob_name
    local_dest.parent.mkdir(parents=True, exist_ok=True)
    if file_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]:
        # For images, copy the binary file
        local_dest.write_bytes(file_path.read_bytes())
    else:
        # For text files
        local_dest.write_text(file_path.read_text())

    # Also upload to bucket if available
    if has_bucket_write_access():
        bucket = get_bucket()
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(file_path))
        print(f"✅ Uploaded {blob_name} to bucket and saved locally")

    return True


def _write_to_bucket_or_data_dir(content: str, blob_name: str) -> bool:
    """
    Write content to a file in bucket if available, and also save locally for debugging.
    """
    # Always save locally for debugging
    local_path = DATA_PATH / blob_name
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(content)

    # Also upload to bucket if available
    if has_bucket_write_access():
        bucket = get_bucket()
        blob = bucket.blob(blob_name)
        blob.upload_from_string(content)
        print(f"✅ Uploaded {blob_name} to bucket and saved locally")
    else:
        print(f"✅ Saved {blob_name} locally only (no bucket access)")

    return True


def write_to_storage(file_path: Path, content: str) -> bool:
    """
    Write content to a file in storage at the given path relative to DATA_PATH.

    Args:
        file_path: Path object that must be relative to DATA_PATH
        content: Content to write to the file

    Raises:
        ValueError: If the path is not relative to DATA_PATH
    """
    # Ensure the path is relative to DATA_PATH
    if not file_path.is_relative_to(DATA_PATH):
        raise ValueError(f"Path {file_path} is not relative to DATA_PATH {DATA_PATH}")

    relative_path = file_path.relative_to(DATA_PATH)
    return _write_to_bucket_or_data_dir(content, str(relative_path))


def _read_file_from_bucket_or_data_dir(blob_name: str) -> str:
    """
    Read a file from local data directory first, then from bucket if not found.
    """
    # Try local first
    local_path = DATA_PATH / blob_name
    if local_path.exists():
        return local_path.read_text()

    # If not found locally, try bucket
    if has_bucket_read_access():
        bucket = get_bucket()
        blob = bucket.blob(blob_name)
        return blob.download_as_text()
    else:
        raise FileNotFoundError(f"File not found locally or in bucket: {blob_name}")


def read_from_storage(file_path: Path) -> str:
    """
    Read a file from storage at the given path relative to DATA_PATH.

    Args:
        file_path: Path object that must be relative to DATA_PATH

    Returns:
        Content of the file as string

    Raises:
        ValueError: If the path is not relative to DATA_PATH
        FileNotFoundError: If the file is not found in storage
    """
    # Ensure the path is relative to DATA_PATH
    if not file_path.is_relative_to(DATA_PATH):
        raise ValueError(f"Path {file_path} is not relative to DATA_PATH {DATA_PATH}")

    relative_path = file_path.relative_to(DATA_PATH)
    return _read_file_from_bucket_or_data_dir(str(relative_path))


def file_exists_in_storage(file_path: Path, force_rewrite: bool = False) -> bool:
    """
    Check if a file exists in storage (GCP bucket or local data directory).

    Args:
        file_path: Path object that must be relative to DATA_PATH

    Returns:
        True if file exists, False otherwise

    Raises:
        ValueError: If the path is not relative to DATA_PATH
    """
    if force_rewrite:
        return False

    # Ensure the path is relative to DATA_PATH
    if not file_path.is_relative_to(DATA_PATH):
        raise ValueError(f"Path {file_path} is not relative to DATA_PATH {DATA_PATH}")

    relative_path = file_path.relative_to(DATA_PATH)
    blob_name = str(relative_path)

    # Check bucket if available
    if has_bucket_read_access():
        bucket = get_bucket()
        blob = bucket.blob(blob_name)
        return blob.exists()

    # Check local
    return file_path.exists()


def delete_from_storage(file_path: Path) -> bool:
    """
    Delete a file from storage (GCP bucket and local data directory).

    Args:
        file_path: Path object that must be relative to DATA_PATH

    Returns:
        True if file was deleted successfully, False otherwise

    Raises:
        ValueError: If the path is not relative to DATA_PATH
    """
    # Ensure the path is relative to DATA_PATH
    if not file_path.is_relative_to(DATA_PATH):
        raise ValueError(f"Path {file_path} is not relative to DATA_PATH {DATA_PATH}")

    relative_path = file_path.relative_to(DATA_PATH)
    blob_name = str(relative_path)
    
    deleted = False

    # Delete from bucket if available
    if has_bucket_write_access():
        bucket = get_bucket()
        blob = bucket.blob(blob_name)
        if blob.exists():
            blob.delete()
            deleted = True

    # Delete from local
    if file_path.exists():
        file_path.unlink()
        deleted = True

    return deleted


if __name__ == "__main__":
    print(has_bucket_write_access())
