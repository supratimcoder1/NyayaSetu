from . import models
from datetime import datetime

# Module-level constant — single source of truth for stage order (#18: no more duplicates)
WORKFLOW = [
    models.CaseStage.PRE_FILING,
    models.CaseStage.FILING,
    models.CaseStage.NOTICE_ISSUED,
    models.CaseStage.WRITTEN_STATEMENT,
    models.CaseStage.EVIDENCE_SUBMISSION,
    models.CaseStage.HEARING,
    models.CaseStage.ARGUMENTS,
    models.CaseStage.JUDGMENT,
    models.CaseStage.EXECUTION,
    models.CaseStage.CLOSED,
]

# Pre-computed lookup: string value → index
STAGE_INDEX = {stage.value: i for i, stage in enumerate(WORKFLOW)}


def _resolve_stage(stage_input):
    """Convert a string or enum to the CaseStage enum. Returns None if invalid."""
    if isinstance(stage_input, models.CaseStage):
        return stage_input
    # It's a string — try to match by value
    for s in models.CaseStage:
        if s.value == stage_input:
            return s
    return None


def generate_timeline(case_events, current_stage):
    """
    Generates a dynamic timeline based on actual case events and the standard Civil Workflow.
    Fixed: properly resolves string current_stage to enum before comparison.
    """
    resolved = _resolve_stage(current_stage)
    current_idx = STAGE_INDEX.get(resolved.value, 0) if resolved else 0

    timeline = []
    for stage in WORKFLOW:
        stage_idx = STAGE_INDEX[stage.value]

        if stage_idx < current_idx:
            status = "Completed"
        elif stage_idx == current_idx:
            status = "Current"
        else:
            status = "Upcoming"

        timeline.append({
            "stage": stage.value,
            "status": status,
            "description": get_stage_description(stage)
        })

    return timeline


def get_stage_description(stage):
    descriptions = {
        models.CaseStage.PRE_FILING: "Preparation of documents and legal notice.",
        models.CaseStage.FILING: "Case filed in court and number generated.",
        models.CaseStage.NOTICE_ISSUED: "Summons sent to the opposite party.",
        models.CaseStage.WRITTEN_STATEMENT: "Reply filed by the defendant.",
        models.CaseStage.EVIDENCE_SUBMISSION: "Submission of proofs and witness affidavits.",
        models.CaseStage.HEARING: "Examination of witnesses by court.",
        models.CaseStage.ARGUMENTS: "Final oral arguments by lawyers.",
        models.CaseStage.JUDGMENT: "Final order pronounced by the Judge.",
        models.CaseStage.EXECUTION: "Implementation of the court order.",
        models.CaseStage.CLOSED: "Case file closed.",
    }
    resolved = _resolve_stage(stage)
    return descriptions.get(resolved, "Procedural Step")


def get_next_stage(current_stage: str) -> str:
    """Returns the next stage value string, or None if last."""
    resolved = _resolve_stage(current_stage)
    if resolved is None:
        return None
    idx = STAGE_INDEX.get(resolved.value)
    if idx is not None and idx < len(WORKFLOW) - 1:
        return WORKFLOW[idx + 1].value
    return None


def evaluate_stage_transition(event_type: str, current_stage: str) -> str:
    """
    Determines if a new event triggers a stage change.
    Returns the new stage VALUE string, or None.
    """
    resolved = _resolve_stage(current_stage)
    if resolved is None:
        return None

    if event_type == models.CaseEventType.FILING.value and resolved == models.CaseStage.PRE_FILING:
        return models.CaseStage.FILING.value

    if event_type == models.CaseEventType.NOTICE.value and resolved == models.CaseStage.FILING:
        return models.CaseStage.NOTICE_ISSUED.value

    if event_type == models.CaseEventType.EVIDENCE.value:
        if resolved in (models.CaseStage.WRITTEN_STATEMENT, models.CaseStage.NOTICE_ISSUED):
            return models.CaseStage.EVIDENCE_SUBMISSION.value

    if event_type == models.CaseEventType.HEARING.value:
        if resolved == models.CaseStage.EVIDENCE_SUBMISSION:
            return models.CaseStage.HEARING.value

    if event_type == models.CaseEventType.ORDER.value:
        return None  # Manual intervention needed

    return None


def recommend_next_step(current_stage: str, case_type: str) -> str:
    """
    Returns specific procedural advice based on the Civil Workflow.
    """
    resolved = _resolve_stage(current_stage)

    advice = {
        models.CaseStage.PRE_FILING: "Legal Notice: Send a formal legal notice to the opposite party via Registered Post. Keep the postal receipt.",
        models.CaseStage.FILING: "Service of Summons: Ensure the court summons is served to the defendant. You may need to pay 'Bhatta' (Process Fee).",
        models.CaseStage.NOTICE_ISSUED: "Wait for Appearance: Track if the defendant acknowledges receipt. If they refuse (Refusal), it is treated as served.",
        models.CaseStage.WRITTEN_STATEMENT: "Replication: Review the defendant's reply. You may file a 'Replication' to deny their allegations.",
        models.CaseStage.EVIDENCE_SUBMISSION: "Affidavit in Evidence: File your Chief Examination via Affidavit. Ensure original documents are annexed.",
        models.CaseStage.HEARING: "Cross Examination: Prepare your witnesses for cross-examination by the opposing counsel.",
        models.CaseStage.ARGUMENTS: "Written Submissions: Prepare a concise summary of facts, evidence, and relevant case laws to submit to the judge.",
        models.CaseStage.JUDGMENT: "Certified Copy: Apply for the certified copy of the judgment immediately (`Nakal`).",
        models.CaseStage.EXECUTION: "Execution Petition: If the order is not obeyed, file an Execution Petition (EP) to enforce it.",
    }

    return advice.get(resolved, "Consult your lawyer for the specific procedural requirement.")
