import asyncio
import io

import fitz
import pytest
from bson import ObjectId
from docx import Document as WordDocument
from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.user import User
from app.routers import lawyer_documents


class FakeGridFS:
    def __init__(self):
        self.files: dict[str, bytes] = {}

    def put(self, content: bytes, **_kwargs):
        identifier = str(ObjectId())
        self.files[identifier] = content
        return ObjectId(identifier)

    def get(self, identifier: ObjectId):
        return io.BytesIO(self.files[str(identifier)])

    def delete(self, identifier: ObjectId):
        self.files.pop(str(identifier), None)


@pytest.fixture
def database(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    storage = FakeGridFS()
    monkeypatch.setattr(lawyer_documents, "mongo_available", True)
    monkeypatch.setattr(lawyer_documents, "fs", storage)
    try:
        yield session_factory(), storage
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def make_user(db, role: str, email: str) -> User:
    # These tests exercise case-document authorization directly; password
    # verification belongs to the authentication suite.
    user = User(email=email, password_hash="fixture-only-not-used", role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_upload(filename: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(file=io.BytesIO(content), filename=filename, headers=Headers({"content-type": content_type}))


def pdf_bytes(text: str = "Case document text") -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), text)
    return pdf.tobytes()


def workspace(db, lawyer: User) -> str:
    response = lawyer_documents.get_or_create_workspace(current_user=lawyer, db=db)
    return response["id"]


def test_lawyer_upload_list_and_delete_persisted_document(database):
    db, storage = database
    lawyer = make_user(db, "lawyer", "lawyer-docs@example.com")
    case_id = workspace(db, lawyer)
    uploaded = asyncio.run(lawyer_documents.upload_documents(
        case_id, [make_upload("evidence.pdf", pdf_bytes(), "application/pdf")], lawyer, db
    ))
    assert uploaded[0]["status"] == "parsed"
    assert uploaded[0]["pages"] == 1
    assert uploaded[0]["extracted_text_available"] is True
    assert len(storage.files) == 1

    listed = lawyer_documents.list_documents(case_id, lawyer, db)
    assert listed[0]["id"] == uploaded[0]["id"]
    lawyer_documents.delete_document(case_id, uploaded[0]["id"], lawyer, db)
    assert storage.files == {}
    assert lawyer_documents.list_documents(case_id, lawyer, db) == []


def test_upload_rejects_invalid_type_and_oversized_file(database):
    db, _ = database
    lawyer = make_user(db, "lawyer", "limits@example.com")
    case_id = workspace(db, lawyer)
    with pytest.raises(HTTPException) as invalid:
        asyncio.run(lawyer_documents.upload_documents(case_id, [make_upload("malware.exe", b"x", "application/octet-stream")], lawyer, db))
    assert invalid.value.status_code == 415
    with pytest.raises(HTTPException) as oversized:
        asyncio.run(lawyer_documents.upload_documents(case_id, [make_upload("large.pdf", b"%PDF-" + b"x" * (20 * 1024 * 1024), "application/pdf")], lawyer, db))
    assert oversized.value.status_code == 413


def test_docx_text_is_extracted(database):
    db, _ = database
    lawyer = make_user(db, "lawyer", "docx@example.com")
    case_id = workspace(db, lawyer)
    word = WordDocument()
    word.add_paragraph("Witness statement from the case file")
    content = io.BytesIO()
    word.save(content)
    uploaded = asyncio.run(lawyer_documents.upload_documents(
        case_id,
        [make_upload("statement.docx", content.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")],
        lawyer,
        db,
    ))
    assert uploaded[0]["status"] == "parsed"
    assert uploaded[0]["pages"] is None


def test_case_documents_are_owner_scoped_and_route_requires_lawyer_role(database):
    db, _ = database
    lawyer_one = make_user(db, "lawyer", "owner@example.com")
    lawyer_two = make_user(db, "lawyer", "other@example.com")
    case_id = workspace(db, lawyer_one)
    with pytest.raises(HTTPException) as denied:
        lawyer_documents.list_documents(case_id, lawyer_two, db)
    assert denied.value.status_code == 404

    route = next(route for route in lawyer_documents.router.routes if route.path == "/lawyer/cases/{case_id}/documents" and "GET" in route.methods)
    assert any(dependency.call.__name__ == "role_checker" for dependency in route.dependant.dependencies)


def test_analysis_endpoint_requires_parsed_documents_and_is_honest_about_scope(database):
    db, _ = database
    lawyer = make_user(db, "lawyer", "analysis@example.com")
    case_id = workspace(db, lawyer)
    with pytest.raises(HTTPException) as response:
        lawyer_documents.begin_analysis(case_id, lawyer, db)
    assert response.value.status_code == 409
