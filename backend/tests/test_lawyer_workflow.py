import pytest
from fastapi import HTTPException

from app.models.case_document import CaseDocument
from app.models.lawyer_case import LawyerCase
from app.models.lawyer_workflow import CaseAnalysis, CaseTimelineEvent
from app.routers import lawyer_documents, lawyer_workflow
from test_lawyer_documents import database, make_user


def analyzed_case(database):
    db, _ = database
    lawyer = make_user(db, "lawyer", "workflow@example.com")
    case = LawyerCase(lawyer_id=lawyer.id, title="Workflow fixture")
    db.add(case); db.commit(); db.refresh(case)
    content = "Complainant: Asha Kumar\nAccused: Ravi Singh\nIncident Location: Market Road\nOn 08/09/2026 at 7:30 PM, incident occurred. BNS Section 303. Amount Rs. 5000."
    db.add(CaseDocument(case_id=case.id, uploaded_by=lawyer.id, original_filename="fir.pdf", file_type="pdf", content_type="application/pdf", size_bytes=len(content), status="parsed", progress=100, extracted_text=content, extracted_entities="[]", ocr_used=False))
    db.commit()
    return db, lawyer, case.id


def test_analysis_persists_only_source_grounded_data_and_timeline(database):
    db, lawyer, case_id = analyzed_case(database)
    result = lawyer_workflow.analyze(case_id, lawyer, db)
    assert result["status"] == "completed"
    assert result["analysis"]["parties"][0]["source"]["document_id"]
    assert result["analysis"]["bns_sections"][0]["section_number"] == "303"
    events = lawyer_workflow.get_timeline(case_id, current_user=lawyer, db=db)
    assert len(events) == 1
    assert events[0]["date"] == "2026-09-08"
    assert events[0]["source_document_name"] == "fir.pdf"
    assert lawyer_documents.document_metrics(case_id, lawyer, db)["documents"] == 1


def test_legacy_analysis_alias_uses_parsed_document_text(database):
    db, lawyer, case_id = analyzed_case(database)
    result = lawyer_documents.begin_analysis(case_id, lawyer, db)
    assert result["status"] == "completed"
    assert result["analysis"]["parties"][0]["name"] == "Asha Kumar"


def test_corrections_timeline_and_summary_are_persisted(database):
    db, lawyer, case_id = analyzed_case(database)
    lawyer_workflow.analyze(case_id, lawyer, db)
    current = lawyer_workflow.get_analysis(case_id, lawyer, db)["analysis"]
    current["offence_type"] = "Lawyer-reviewed theft allegation"
    updated = lawyer_workflow.update_analysis(case_id, lawyer_workflow.AnalysisPatch(payload=current), lawyer, db)
    assert updated["analysis"]["offence_type"].startswith("Lawyer-reviewed")
    event = lawyer_workflow.get_timeline(case_id, current_user=lawyer, db=db)[0]
    patched = lawyer_workflow.update_timeline(case_id, event["id"], lawyer_workflow.EventPatch(title="Reviewed event", event_type="FIR"), lawyer, db)
    assert patched["is_edited"] is True and patched["event_type"] == "FIR"
    lawyer_workflow.update_summary(case_id, lawyer_workflow.SummaryPatch(executive_summary="Reviewed summary", current_stage="Review"), lawyer, db)
    assert lawyer_workflow.get_summary(case_id, lawyer, db)["executive_summary"] == "Reviewed summary"


def test_analysis_failure_is_honest_and_retryable(database, monkeypatch):
    db, lawyer, case_id = analyzed_case(database)
    def broken(_documents): raise RuntimeError("model unavailable")
    monkeypatch.setattr(lawyer_workflow, "extract_case_information", broken)
    with pytest.raises(HTTPException) as error:
        lawyer_workflow.analyze(case_id, lawyer, db)
    assert error.value.status_code == 503
    record = db.query(CaseAnalysis).filter(CaseAnalysis.case_id == case_id).one()
    assert record.status == "failed" and record.error_message


def test_export_is_real_pdf_and_case_access_is_owner_scoped(database):
    db, lawyer, case_id = analyzed_case(database)
    lawyer_workflow.analyze(case_id, lawyer, db)
    response = lawyer_workflow.export_case(case_id, lawyer_workflow.ExportOptions(), lawyer, db)
    assert response.media_type == "application/pdf"
    assert "case-package-" in response.headers["content-disposition"]
    other = make_user(db, "lawyer", "workflow-other@example.com")
    with pytest.raises(HTTPException) as denied:
        lawyer_workflow.get_summary(case_id, other, db)
    assert denied.value.status_code == 404


def test_timeline_date_filters_and_pdf_escape_user_text(database):
    db, lawyer, case_id = analyzed_case(database)
    lawyer_workflow.analyze(case_id, lawyer, db)
    db.add_all([
        CaseTimelineEvent(case_id=case_id, event_date="2026-01-03", title="Earlier", description="A < B", event_type="FIR", related_bns_sections="[]", confidence="needs_review", is_edited="true"),
        CaseTimelineEvent(case_id=case_id, event_date="2026-10-03", title="Later", description="C & D", event_type="FIR", related_bns_sections="[]", confidence="needs_review", is_edited="true"),
    ])
    db.commit()
    events = lawyer_workflow.get_timeline(case_id, date_from="2026-10-01", date_to="2026-10-31", current_user=lawyer, db=db)
    assert [event["title"] for event in events] == ["Later"]
    lawyer_workflow.update_summary(case_id, lawyer_workflow.SummaryPatch(executive_summary="A < B & C", current_stage=None), lawyer, db)
    assert lawyer_workflow.export_case(case_id, lawyer_workflow.ExportOptions(), lawyer, db).media_type == "application/pdf"


def test_delete_after_analysis_invalidates_dependencies_without_broken_foreign_keys(database):
    db, lawyer, case_id = analyzed_case(database)
    lawyer_workflow.analyze(case_id, lawyer, db)
    document = db.query(CaseDocument).filter(CaseDocument.case_id == case_id).one()
    assert db.query(CaseTimelineEvent).filter(CaseTimelineEvent.source_document_id == document.id).count() > 0
    lawyer_documents.delete_document(case_id, document.id, lawyer, db)
    assert db.query(CaseDocument).filter(CaseDocument.id == document.id).first() is None
    assert db.query(CaseTimelineEvent).filter(CaseTimelineEvent.source_document_id == document.id).count() == 0
    analysis = db.query(CaseAnalysis).filter(CaseAnalysis.case_id == case_id).one()
    assert analysis.status == "needs_review"
    assert document.original_filename in analysis.error_message
