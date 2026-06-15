"""Pydantic schemas for ABUZ8 CRM API"""
from pydantic import BaseModel
from typing import Optional, List


class ProjectOut(BaseModel):
    id: int
    name: str
    category: Optional[str]
    status: Optional[str]
    completion_pct: Optional[int]
    evidence_score: Optional[int]
    revenue_potential: Optional[float]
    revenue_realized: Optional[float]
    market_value_verified: Optional[float]
    replacement_cost_value: Optional[float]
    strategic_upside_value: Optional[float]
    valuation_confidence: Optional[int]
    valuation_method: Optional[str]
    priority_score: Optional[int]
    urf_urgency: Optional[int]
    urf_reality: Optional[int]
    urf_feasibility: Optional[int]
    urf_score: Optional[float]
    today_score: Optional[float]
    next_action: Optional[str]
    next_action_eta_hours: Optional[float]
    blocker: Optional[str]
    assigned_agent: Optional[str]
    created_at: Optional[str]
    last_active_at: Optional[str]
    updated_at: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


class FileOut(BaseModel):
    id: int
    path: str
    filename: Optional[str]
    extension: Optional[str]
    size_bytes: Optional[int]
    sha256: Optional[str]
    created_at: Optional[str]
    modified_at: Optional[str]
    last_scanned_at: Optional[str]
    project_id: Optional[int]
    category: Optional[str]
    status: Optional[str]
    ai_tool_guess: Optional[str]
    summary: Optional[str]
    reusable: Optional[int]
    revenue_linked: Optional[int]
    secret_detected: Optional[int]
    unreadable_reason: Optional[str]

    class Config:
        from_attributes = True


class ModelOut(BaseModel):
    id: int
    name: Optional[str]
    model_type: Optional[str]
    architecture: Optional[str]
    path: str
    size_bytes: Optional[int]
    modified_at: Optional[str]
    source: Optional[str]
    status: Optional[str]
    vram_required_gb: Optional[float]
    commercial_license_status: Optional[str]
    duplicate_group: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


class ProgramOut(BaseModel):
    id: int
    name: Optional[str]
    version: Optional[str]
    path: Optional[str]
    category: Optional[str]
    status: Optional[str]
    last_used: Optional[str]
    role_in_stack: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


class AgentOut(BaseModel):
    id: int
    name: Optional[str]
    framework: Optional[str]
    status: Optional[str]
    process_id: Optional[int]
    port: Optional[int]
    endpoint: Optional[str]
    model_used: Optional[str]
    gpu_id: Optional[str]
    last_heartbeat: Optional[str]
    current_task: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


class SystemMetricsOut(BaseModel):
    id: int
    timestamp: Optional[str]
    cpu_pct: Optional[float]
    ram_used_gb: Optional[float]
    ram_total_gb: Optional[float]
    gpu0_name: Optional[str]
    gpu0_vram_used_gb: Optional[float]
    gpu0_vram_total_gb: Optional[float]
    gpu0_util_pct: Optional[float]
    gpu1_name: Optional[str]
    gpu1_vram_used_gb: Optional[float]
    gpu1_vram_total_gb: Optional[float]
    gpu1_util_pct: Optional[float]
    disk_json: Optional[str]
    gpu_processes_json: Optional[str]
    running_services_json: Optional[str]
    open_ports_json: Optional[str]

    class Config:
        from_attributes = True


class ActionOut(BaseModel):
    id: int
    project_id: Optional[int]
    action: Optional[str]
    reason: Optional[str]
    eta_hours: Optional[float]
    money_unlocked: Optional[float]
    status: Optional[str]
    due_date: Optional[str]
    created_at: Optional[str]
    completed_at: Optional[str]
    assigned_agent: Optional[str]

    class Config:
        from_attributes = True


class ComfyJobOut(BaseModel):
    id: int
    name: Optional[str]
    workflow_path: Optional[str]
    prompt_path: Optional[str]
    model_used: Optional[str]
    status: Optional[str]
    output_path: Optional[str]
    target_video_count: Optional[int]
    completed_video_count: Optional[int]
    failed_count: Optional[int]
    next_render_action: Optional[str]
    last_run_at: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


class SummaryOut(BaseModel):
    project_count: int
    file_count: int
    model_count: int
    program_count: int
    agent_count: int
    active_agent_count: int
    latest_scan: Optional[str]
    latest_monitor: Optional[str]
    top_project: Optional[ProjectOut]
    top_action: Optional[ActionOut]
