import os
from google.cloud import storage

def download_blob_to_file(bucket_name: str, source_blob_name: str, destination_file_name: str):
    """Downloads a blob from the bucket to a local file."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)

        # Download the blob to the specified local file path
        blob.download_to_filename(destination_file_name)

        print(f"Blob {source_blob_name} downloaded to {destination_file_name}.")
        return True
    except Exception as e:
        print(f"Error downloading {source_blob_name}: {e}")
        return False