"""
dify_client.py - Goi 2 API cua Dify de tao document trong Knowledge Base.

    POST /v1/datasets/{dataset_id}/document/create-by-file   (file nhi phan: pdf, docx, ...)
    POST /v1/datasets/{dataset_id}/document/create-by-text    (text thuan)

Tham khao: https://docs.dify.ai (Knowledge Base API)
"""
import os
import json
import mimetypes
import requests


class DifyError(Exception):
    pass


class DifyClient:
    def __init__(self, base_url: str, api_key: str, dataset_id: str,
                 indexing_technique: str = "high_quality", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.dataset_id = dataset_id
        self.indexing_technique = indexing_technique
        self.timeout = timeout

    @property
    def _auth_header(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _process_rule(self) -> dict:
        # mode 'automatic' = de Dify tu dong tach chunk
        return {
            "indexing_technique": self.indexing_technique,
            "process_rule": {"mode": "automatic"},
        }

    def create_by_file(self, file_path: str, display_name: str | None = None) -> dict:
        """Day mot file nhi phan len Dify. Tra ve dict {document_id, batch}.

        display_name: ten hien thi tren Dify (dung khi file thuc te la ban OCR tam,
        nhung muon giu ten goc cua khach).
        """
        url = f"{self.base_url}/v1/datasets/{self.dataset_id}/document/create-by-file"
        file_name = display_name or os.path.basename(file_path)
        mime = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

        with open(file_path, "rb") as f:
            files = {"file": (file_name, f, mime)}
            # Dify yeu cau truong 'data' la chuoi JSON kem theo file
            data = {"data": json.dumps(self._process_rule(), ensure_ascii=False)}
            resp = requests.post(
                url, headers=self._auth_header, files=files, data=data,
                timeout=self.timeout,
            )
        return self._parse(resp)

    def create_by_text(self, name: str, text: str) -> dict:
        """Tao document tu text thuan. Tra ve dict {document_id, batch}."""
        url = f"{self.base_url}/v1/datasets/{self.dataset_id}/document/create-by-text"
        payload = {"name": name, "text": text, **self._process_rule()}
        headers = {**self._auth_header, "Content-Type": "application/json"}
        resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        return self._parse(resp)

    @staticmethod
    def _parse(resp: requests.Response) -> dict:
        if resp.status_code not in (200, 201):
            raise DifyError(f"HTTP {resp.status_code}: {resp.text[:500]}")
        try:
            body = resp.json()
        except ValueError:
            raise DifyError(f"Phan hoi khong phai JSON: {resp.text[:500]}")

        doc = body.get("document") or {}
        document_id = doc.get("id")
        batch = body.get("batch", "")
        if not document_id:
            raise DifyError(f"Khong tim thay document.id trong phan hoi: {body}")
        return {"document_id": document_id, "batch": batch}
