from io import BytesIO


def test_upload_document(auth_client):
    files = {"file": ("report.pdf", BytesIO(b"%PDF-1.4 test"), "application/pdf")}
    response = auth_client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["document"]["filename"] == "report.pdf"
    assert data["document"]["status"] == "uploaded"


def test_list_documents(auth_client):
    response = auth_client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_ingest_document(auth_client, sample_document_id):
    response = auth_client.post(
        f"/api/v1/documents/{sample_document_id}/ingest",
        params={"sync": "true"},
    )
    assert response.status_code in (200, 202)
    data = response.json()
    assert data["status"] == "indexed"
    assert data["chunks_created"] >= 1
