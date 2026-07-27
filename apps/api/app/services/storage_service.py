"""
Abstraccion de almacenamiento de archivos originales (Cloud Storage en produccion).
En desarrollo local (ENVIRONMENT=local) o si no hay GCS_BUCKET configurado, guarda
en el filesystem local (./local_storage) para poder probar sin credenciales de GCP.
"""
import os
import uuid
from pathlib import Path

from app.core.config import settings

LOCAL_STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "local_storage"


def _use_local_storage() -> bool:
    return settings.environment == "local" or not settings.gcs_bucket


def save_file(filename: str, content: bytes) -> str:
    """Guarda el archivo y devuelve el 'path' (gcs_path o ruta local) para guardar en import_files."""
    unique_name = f"{uuid.uuid4().hex}_{filename}"

    if _use_local_storage():
        LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        dest = LOCAL_STORAGE_DIR / unique_name
        dest.write_bytes(content)
        return f"local://{dest}"

    from google.cloud import storage  # import diferido: solo se necesita en produccion

    client = storage.Client()
    bucket = client.bucket(settings.gcs_bucket)
    blob = bucket.blob(f"facturas/{unique_name}")
    blob.upload_from_string(content)
    return f"gs://{settings.gcs_bucket}/facturas/{unique_name}"


def read_file(gcs_path: str) -> bytes:
    if gcs_path.startswith("local://"):
        return Path(gcs_path.replace("local://", "")).read_bytes()

    from google.cloud import storage

    # gcs_path = "gs://bucket/ruta/al/archivo"
    _, _, bucket_name, *blob_parts = gcs_path.split("/")
    blob_path = "/".join(blob_parts)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    return blob.download_as_bytes()
