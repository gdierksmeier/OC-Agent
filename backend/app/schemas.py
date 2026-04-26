"""Pydantic schemas for request validation and API responses."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------- Users ----------

class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    role: str = "designer"


class UserCreate(UserBase):
    pass


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: datetime


# ---------- Environment Settings ----------

class EnvironmentSettingBase(BaseModel):
    environment: str = "dev"
    key: str
    value: str
    is_secret: bool = False
    description: Optional[str] = None
    is_active: bool = True


class EnvironmentSettingCreate(EnvironmentSettingBase):
    pass


class EnvironmentSettingUpdate(BaseModel):
    environment: Optional[str] = None
    key: Optional[str] = None
    value: Optional[str] = None
    is_secret: Optional[bool] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class EnvironmentSettingOut(EnvironmentSettingBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


# ---------- AI Models ----------

class AIModelBase(BaseModel):
    name: str
    provider: str
    model_identifier: str
    model_type: str = "cloud"
    context_window: int = 8192
    max_tokens: int = 2048
    temperature_default: float = 0.7
    top_p_default: float = 1.0
    supports_tools: bool = False
    supports_streaming: bool = True
    cost_per_1k_input_tokens: float = 0.0
    cost_per_1k_output_tokens: float = 0.0
    handles_sensitive_data: bool = False
    routing_priority: int = 100
    status: str = "active"


class AIModelCreate(AIModelBase):
    pass


class AIModelUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    model_identifier: Optional[str] = None
    model_type: Optional[str] = None
    context_window: Optional[int] = None
    max_tokens: Optional[int] = None
    temperature_default: Optional[float] = None
    top_p_default: Optional[float] = None
    supports_tools: Optional[bool] = None
    supports_streaming: Optional[bool] = None
    cost_per_1k_input_tokens: Optional[float] = None
    cost_per_1k_output_tokens: Optional[float] = None
    handles_sensitive_data: Optional[bool] = None
    routing_priority: Optional[int] = None
    status: Optional[str] = None


class AIModelOut(AIModelBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# ---------- Endpoints ----------

class EndpointBase(BaseModel):
    name: str
    description: Optional[str] = None
    base_url: str
    path: str = ""
    method: str = "GET"
    auth_type: str = "none"
    auth_config: dict = Field(default_factory=dict)
    headers: dict = Field(default_factory=dict)
    query_params_template: dict = Field(default_factory=dict)
    body_template: str = ""
    timeout_seconds: int = 30
    environment: str = "dev"
    response_schema: dict = Field(default_factory=dict)
    response_mapping: dict = Field(default_factory=dict)
    validation_rules: list = Field(default_factory=list)
    estimated_cost_per_call: float = 0.0
    sensitive_fields: list = Field(default_factory=list)
    is_active: bool = True


class EndpointCreate(EndpointBase):
    pass


class EndpointUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_url: Optional[str] = None
    path: Optional[str] = None
    method: Optional[str] = None
    auth_type: Optional[str] = None
    auth_config: Optional[dict] = None
    headers: Optional[dict] = None
    query_params_template: Optional[dict] = None
    body_template: Optional[str] = None
    timeout_seconds: Optional[int] = None
    environment: Optional[str] = None
    response_schema: Optional[dict] = None
    response_mapping: Optional[dict] = None
    validation_rules: Optional[list] = None
    estimated_cost_per_call: Optional[float] = None
    sensitive_fields: Optional[list] = None
    is_active: Optional[bool] = None


class EndpointOut(EndpointBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class EndpointTestRequest(BaseModel):
    """`environment` selects which environment_settings rows load (OUC host, token, etc.)."""
    environment: str = "dev"
    input_data: dict = Field(default_factory=dict)
    # When true, perform a real HTTP request (httpx). When false, simulated response.
    real_http: bool = False
    # Optional overrides for this test only (do not require saving the endpoint first).
    override_base_url: str | None = None
    override_path: str | None = None
    override_method: str | None = None
    # If set, used instead of the endpoint's query_params_template (values still get {{ input }} resolution).
    override_query_params: dict | None = None


# ---------- Prompts ----------

class PromptBase(BaseModel):
    name: str
    description: Optional[str] = None
    template: str
    variables: list = Field(default_factory=list)
    category: str = "task"
    status: str = "draft"


class PromptCreate(PromptBase):
    pass


class PromptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template: Optional[str] = None
    variables: Optional[list] = None
    category: Optional[str] = None
    status: Optional[str] = None


class PromptOut(PromptBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    version: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime


# ---------- Tasks ----------

class TaskBase(BaseModel):
    name: str
    task_type: str
    order_index: int = 0
    config: dict = Field(default_factory=dict)
    depends_on: list = Field(default_factory=list)
    preconditions: Optional[str] = None
    postconditions: Optional[str] = None
    timeout_seconds: int = 30
    retry_count: int = 0
    error_handling: str = "fail"
    endpoint_id: Optional[int] = None
    model_id: Optional[int] = None
    prompt_id: Optional[int] = None


class TaskCreate(TaskBase):
    pass


class TaskOut(TaskBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    workflow_id: int


# ---------- Workflows ----------

class WorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "draft"


class WorkflowCreate(WorkflowBase):
    agent_id: int
    tasks: list[TaskCreate] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tasks: Optional[list[TaskCreate]] = None


class WorkflowOut(WorkflowBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    agent_id: int
    version: int
    tasks: list[TaskOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ---------- Agents ----------

class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    objective: Optional[str] = None
    business_domain: Optional[str] = None
    environment: str = "dev"
    status: str = "draft"
    system_prompt: Optional[str] = None
    business_instructions: Optional[str] = None
    constraints: Optional[str] = None
    response_format: str = "json"
    fallback_behavior: Optional[str] = None
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    default_model_id: Optional[int] = None
    owner_id: Optional[int] = None


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    objective: Optional[str] = None
    business_domain: Optional[str] = None
    environment: Optional[str] = None
    status: Optional[str] = None
    system_prompt: Optional[str] = None
    business_instructions: Optional[str] = None
    constraints: Optional[str] = None
    response_format: Optional[str] = None
    fallback_behavior: Optional[str] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    default_model_id: Optional[int] = None
    owner_id: Optional[int] = None


class AgentOut(AgentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    current_version: int
    created_at: datetime
    updated_at: datetime


class AgentDetailOut(AgentOut):
    workflows: list[WorkflowOut] = Field(default_factory=list)


class AgentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    agent_id: int
    version: int
    snapshot: dict
    changelog: Optional[str] = None
    status: str
    created_by: Optional[int] = None
    created_at: datetime
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None


# ---------- Executions ----------

class ExecutionStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    step_name: str
    step_type: str
    status: str
    input_data: dict | None = None
    output_data: dict | None = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    latency_ms: int
    cost: float
    tokens_input: int
    tokens_output: int
    retries: int
    error_message: Optional[str] = None


class ExecutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    correlation_id: str
    agent_id: int
    agent_version: int
    workflow_id: Optional[int] = None
    user_id: Optional[int] = None
    input_data: dict | None = None
    output_data: dict | None = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_latency_ms: int
    total_cost: float
    estimated_cost: float
    total_tokens_input: int
    total_tokens_output: int
    schema_compliant: bool
    escalated: bool
    error_message: Optional[str] = None


class ExecutionDetailOut(ExecutionOut):
    steps: list[ExecutionStepOut] = Field(default_factory=list)


class ExecuteAgentRequest(BaseModel):
    input_data: dict = Field(default_factory=dict)
    user_id: Optional[int] = None


# ---------- Budgets / Cost ----------

class BudgetBase(BaseModel):
    name: str
    scope: str
    scope_id: Optional[str] = None
    period: str = "monthly"
    limit_amount: float
    warning_threshold: float = 0.8
    hard_limit: bool = False
    is_active: bool = True


class BudgetCreate(BudgetBase):
    pass


class BudgetOut(BudgetBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    current_consumption: float
    period_start: datetime
    created_at: datetime


class CostRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    execution_id: Optional[int] = None
    agent_id: Optional[int] = None
    model_id: Optional[int] = None
    endpoint_id: Optional[int] = None
    record_type: str
    tokens_input: int
    tokens_output: int
    cost: float
    department: Optional[str] = None
    environment: str
    recorded_at: datetime


# ---------- Dashboard / KPIs ----------

class DashboardKPIs(BaseModel):
    total_executions: int
    success_rate: float
    average_latency_ms: float
    endpoint_failure_rate: float
    model_failure_rate: float
    human_escalation_rate: float
    schema_compliance_rate: float
    total_cost: float
    total_tokens: int
    cost_per_successful_run: float
    active_agents: int
    active_endpoints: int
    active_models: int


class CostSummary(BaseModel):
    total_cost: float
    by_model: list[dict[str, Any]]
    by_agent: list[dict[str, Any]]
    by_environment: list[dict[str, Any]]
    daily_trend: list[dict[str, Any]]
