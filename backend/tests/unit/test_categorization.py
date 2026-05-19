"""Unit tests for document categorization."""

from app.utils.categorization import categorize_document, is_rag_ingestible


def test_image_is_photo_not_ingestible():
    cat = categorize_document(filename="photo.jpg", mime_type="image/jpeg")
    assert cat.document_type == "photo"
    assert not is_rag_ingestible("image/jpeg")


def test_algebra_homework_from_filename():
    cat = categorize_document(
        filename="algebra_homework_5.pdf",
        mime_type="application/pdf",
    )
    assert cat.subject == "Алгебра"
    assert cat.document_type == "homework"


def test_video_catalog_only():
    cat = categorize_document(filename="lecture.mp4", mime_type="video/mp4")
    assert cat.document_type == "video"
    assert not is_rag_ingestible("video/mp4")
