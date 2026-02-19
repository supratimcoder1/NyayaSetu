from . import models

def generate_timeline(case_type: str):
    """
    Returns a deterministic timeline based on the case type.
    """
    if case_type == models.CaseType.CRIMINAL:
        return [
            {"step": 1, "stage": "FIR/Complaint", "description": "Filing of First Information Report or Complaint."},
            {"step": 2, "stage": "Investigation", "description": "Police investigation and evidence collection."},
            {"step": 3, "stage": "Charge Sheet", "description": "Filing of charges by the police."},
            {"step": 4, "stage": "Cognizance", "description": "Court takes notice of the offense."},
            {"step": 5, "stage": "Framing of Charges", "description": "Court decides what charges to proceed with."},
            {"step": 6, "stage": "Prosecution Evidence", "description": "Prosecution presents witnesses and evidence."},
            {"step": 7, "stage": "Statement of Accused", "description": "Accused is given a chance to explain evidence."},
            {"step": 8, "stage": "Defense Evidence", "description": "Defense presents their side."},
            {"step": 9, "stage": "Arguments", "description": "Final arguments by both sides."},
            {"step": 10, "stage": "Judgment", "description": "Acquittal or Conviction."},
        ]
    elif case_type == models.CaseType.CIVIL:
        return [
            {"step": 1, "stage": "Plaint", "description": "Filing of the civil suit by Plaintiff."},
            {"step": 2, "stage": "Summons", "description": "Court issues notice to the Defendant."},
            {"step": 3, "stage": "Written Statement", "description": "Defendant files their reply."},
            {"step": 4, "stage": "Framing of Issues", "description": "Court identifies points of dispute."},
            {"step": 5, "stage": "Evidence", "description": "Examination of witnesses and documents."},
            {"step": 6, "stage": "Final Arguments", "description": "Advocates argue on law and facts."},
            {"step": 7, "stage": "Judgment/Decree", "description": "Court passes the final order."},
            {"step": 8, "stage": "Execution", "description": "Enforcement of the decree if needed."},
        ]
    elif case_type == models.CaseType.FAMILY:
        return [
            {"step": 1, "stage": "Petition", "description": "Filing of petition (Divorce/Custody)."},
            {"step": 2, "stage": "Notice", "description": "Notice served to the respondent."},
            {"step": 3, "stage": "Mediation", "description": "Mandatory counseling/mediation session."},
            {"step": 4, "stage": "Evidence", "description": "If mediation fails, evidence is recorded."},
            {"step": 5, "stage": "Arguments", "description": "Final hearing."},
            {"step": 6, "stage": "Judgment", "description": "Final order granting/denying relief."},
        ]
    else:
        # Default/Corporate
        return [
            {"step": 1, "stage": "Filing", "description": "Case initiation."},
            {"step": 2, "stage": "Response", "description": "Counter-party reply."},
            {"step": 3, "stage": "Admission/Denial", "description": "Verifying documents."},
            {"step": 4, "stage": "Hearing", "description": "Court proceedings."},
            {"step": 5, "stage": "Order", "description": "Final decision."},
        ]

def recommend_next_step(current_stage: str, case_type: str) -> str:
    """
    Returns a rule-based next step recommendation.
    """
    # Simple mapping for demo purposes
    if current_stage == models.CaseStage.FILING:
        return "Ensure all copies of the petition are served to the opposite party and keep proof of service."
    elif current_stage == models.CaseStage.HEARING:
        return "Prepare a list of dates and events. Ensure your witnesses are ready if evidence is scheduled."
    elif current_stage == models.CaseStage.ARGUMENTS:
        return "Summarize key case laws and evidence. Prepare written submissions if required by the court."
    elif current_stage == models.CaseStage.JUDGMENT:
        return "Apply for a certified copy of the judgment immediately after pronouncement."
    elif current_stage == models.CaseStage.APPEAL:
        return "Review the limitation period for filing an appeal to the higher court (usually 30-90 days)."
    else:
        return "Consult your lawyer for the specific procedural requirement at this stage."
