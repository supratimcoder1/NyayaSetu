from . import models
from datetime import datetime

def generate_timeline(case_events, current_stage):
    """
    Generates a dynamic timeline based on actual case events and the standard Civil Workflow.
    """
    # Standard Civil Workflow Stages
    workflow = [
        models.CaseStage.PRE_FILING,
        models.CaseStage.FILING,
        models.CaseStage.NOTICE_ISSUED,
        models.CaseStage.WRITTEN_STATEMENT,
        models.CaseStage.EVIDENCE_SUBMISSION,
        models.CaseStage.HEARING,
        models.CaseStage.ARGUMENTS,
        models.CaseStage.JUDGMENT,
        models.CaseStage.EXECUTION,
        models.CaseStage.CLOSED
    ]
    
    timeline = []
    
    # map stages to their index for comparison
    stage_order = {stage: i for i, stage in enumerate(workflow)}
    current_idx = stage_order.get(current_stage, 0)
    
    # Create timeline items from workflow
    for stage in workflow:
        status = "Upcoming"
        stage_idx = stage_order.get(stage, 0)
        
        if stage_idx < current_idx:
            status = "Completed"
        elif stage_idx == current_idx:
            status = "Current"
            
        # Check if we have an actual event for this stage
        # Logic: Find latest event that corresponds to this stage (if strictly mapped)
        # For now, we just list the workflow steps.
        # Enhancment: merge actual dates if available?
        # Let's simple return the standard flow marked with status.
        
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
        models.CaseStage.CLOSED: "Case file closed."
    }
    return descriptions.get(stage, "Procedural Step")

def get_next_stage(current_stage: str) -> str:
    """Returns the next stage in the Civil Workflow or None if last."""
    workflow = [
        models.CaseStage.PRE_FILING,
        models.CaseStage.FILING,
        models.CaseStage.NOTICE_ISSUED,
        models.CaseStage.WRITTEN_STATEMENT,
        models.CaseStage.EVIDENCE_SUBMISSION,
        models.CaseStage.HEARING,
        models.CaseStage.ARGUMENTS,
        models.CaseStage.JUDGMENT,
        models.CaseStage.EXECUTION,
        models.CaseStage.CLOSED
    ]
    
    try:
        idx = workflow.index(current_stage)
        if idx < len(workflow) - 1:
            return workflow[idx + 1].value
    except ValueError:
        pass
        
    return None

def evaluate_stage_transition(event_type: str, current_stage: str) -> str:
    """
    Determines if a new event triggers a stage change.
    """
    # Simple Logic Rule Engine
    if event_type == models.CaseEventType.FILING and current_stage == models.CaseStage.PRE_FILING:
        return models.CaseStage.FILING
    
    if event_type == models.CaseEventType.NOTICE and current_stage == models.CaseStage.FILING:
        return models.CaseStage.NOTICE_ISSUED
        
    if event_type == models.CaseEventType.EVIDENCE:
        if current_stage in [models.CaseStage.WRITTEN_STATEMENT, models.CaseStage.NOTICE_ISSUED]:
             return models.CaseStage.EVIDENCE_SUBMISSION
             
    if event_type == models.CaseEventType.HEARING:
        if current_stage == models.CaseStage.EVIDENCE_SUBMISSION:
            return models.CaseStage.HEARING
            
    if event_type == models.CaseEventType.ORDER:
        # If it's a final order
        return None # Manual intervention usually needed unless specific "Judgment" type
        
    return None

def recommend_next_step(current_stage: str, case_type: str) -> str:
    """
    Returns specific procedural advice based on the new Civil Workflow.
    """
    if current_stage == models.CaseStage.PRE_FILING:
        return "Legal Notice: Send a formal legal notice to the opposite party via Registered Post. Keep the postal receipt."
        
    elif current_stage == models.CaseStage.FILING:
        return "Service of Summons: Ensure the court summons is served to the defendant. You may need to pay 'Bhatta' (Process Fee)."
        
    elif current_stage == models.CaseStage.NOTICE_ISSUED:
        return "Wait for Appearance: Track if the defendant acknowledges receipt. If they refuse (Refusal), it is treated as served."
        
    elif current_stage == models.CaseStage.WRITTEN_STATEMENT:
        return "Replication: Review the defendant's reply. You may file a 'Replication' to deny their allegations."
        
    elif current_stage == models.CaseStage.EVIDENCE_SUBMISSION:
        return "Affidavit in Evidence: File your Chief Examination via Affidavit. Ensure original documents are annexed."
        
    elif current_stage == models.CaseStage.HEARING:
        return "Cross Examination: Prepare your witnesses for cross-examination by the opposing counsel."
        
    elif current_stage == models.CaseStage.ARGUMENTS:
        return "Written Submissions: Prepare a concise summary of facts, evidence, and relevant case laws to submit to the judge."
        
    elif current_stage == models.CaseStage.JUDGMENT:
        return "Certified Copy: Apply for the certified copy of the judgment immediately (`Nakal`)."
        
    elif current_stage == models.CaseStage.EXECUTION:
        return "Execution Petition: If the order is not obeyed, file an Execution Petition (EP) to enforce it."
        
    else:
        return "Consult your lawyer for the specific procedural requirement."
