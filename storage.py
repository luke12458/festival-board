"""One poll partition and one vote partition per poll; one row per browser."""
import json
import os
import sqlite3
from pathlib import Path
from uuid import uuid4

root = Path(__file__).resolve().parent / "instance"


class LocalStore:
    def __init__(self):
        root.mkdir(exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS items (p TEXT,k TEXT,data TEXT,PRIMARY KEY(p,k))")
            db.execute("CREATE TABLE IF NOT EXISTS pictures (name TEXT PRIMARY KEY,data BLOB)")

    def connect(self):
        return sqlite3.connect(root / "board.db")

    def rows(self, partition):
        with self.connect() as db:
            return [json.loads(r[0]) for r in db.execute("SELECT data FROM items WHERE p=?", (partition,))]

    def put(self, partition, key, data):
        row = dict(data, PartitionKey=partition, RowKey=key)
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO items VALUES(?,?,?)", (partition,key,json.dumps(row)))

    def exists(self, key):
        with self.connect() as db:
            return bool(db.execute("SELECT 1 FROM items WHERE p='polls' AND k=?", (key,)).fetchone())

    def picture(self, name, data=None):
        with self.connect() as db:
            if data is not None:
                db.execute("INSERT INTO pictures VALUES(?,?)", (name,data))
                return
            row = db.execute("SELECT data FROM pictures WHERE name=?", (name,)).fetchone()
            return row[0] if row else None


class AzureStore:
    def __init__(self, account):
        from azure.data.tables import TableClient
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import ContainerClient
        self.auth = DefaultAzureCredential()
        self.table = TableClient(f"https://{account}.table.core.windows.net", "FestivalBoard", credential=self.auth)
        self.images = ContainerClient(f"https://{account}.blob.core.windows.net", "pictures", credential=self.auth)

    def rows(self, partition):
        return list(self.table.query_entities("PartitionKey eq @p", parameters={"p": partition}))

    def exists(self, key):
        from azure.core.exceptions import ResourceNotFoundError
        try:
            self.table.get_entity("polls", key)
            return True
        except ResourceNotFoundError:
            return False

    def put(self, partition, key, data):
        self.table.upsert_entity(dict(data, PartitionKey=partition, RowKey=key))

    def picture(self, name, data=None):
        from azure.core.exceptions import ResourceNotFoundError
        from azure.storage.blob import ContentSettings
        blob = self.images.get_blob_client(name)
        if data is not None:
            blob.upload_blob(data, content_settings=ContentSettings(content_type="image/jpeg"))
            return
        try:
            return blob.download_blob().readall()
        except ResourceNotFoundError:
            return None


def open_store():
    account = os.getenv("STORAGE_ACCOUNT")
    if account:
        return AzureStore(account)
    if os.getenv("WEBSITE_SITE_NAME"):
        raise RuntimeError("App Service requires STORAGE_ACCOUNT")
    return LocalStore()
