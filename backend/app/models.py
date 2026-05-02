"""
SQLAlchemy ORM models for the AI Agent Generation & Maintenance System.

Maps the entities defined in the functional spec to SQLite tables:
    Users, Agents, AgentVersions, Workflows, Tasks, Endpoints,
    AIModels, Prompts, Executions, ExecutionSteps, CostRecords, Budgets.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, JSON, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


# ---------------------------------------------------------------------------
# Users & RBAC (basic stub — full RBAC is Phase 3 governance)
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(160), unique=True, nullable=False)
    full_name = Column(String(160))
    role = Column(String(40), nullable=False, default="designer")
    # roles: designer | admin | engineer | ops | governance
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Environment Settings (DEV / QA / PROD configuration)
# ---------------------------------------------------------------------------

class EnvironmentSetting(Base):
    __tablename__ = "environment_settings"
    __table_args__ = (
        UniqueConstraint("environment", "key", name="uq_environment_settings_env_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    environment = Column(String(40), nullable=False, index=True)  # dev | qa | prod
    key = Column(String(120), nullable=False, index=True)
    value = Column(Text, nullable=False)
    is_secret = Column(Boolean, default=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Agent Definition Management (§4.1)
# ---------------------------------------------------------------------------

class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False, index=True)
    description = Column(Text)
    objective = Column(Text)
    business_domain = Column(String(120))
    owner_id = Column(Integer, ForeignKey("users.id"))
    environment = Column(String(40), default="dev")
    # environment: dev | test | uat | prod
    status = Column(String(40), default="draft")
    # status: draft | test | review | published | archived

    system_prompt = Column(Text)
    business_instructions = Column(Text)
    constraints = Column(Text)
    response_format = Column(String(40), default="json")
    fallback_behavior = Column(Text)

    # JSON Schema describing required input parameters
    input_schema = Column(JSON, default=dict)
    # JSON Schema describing structured output (incl. confidence, evidence, etc.)
    output_schema = Column(JSON, default=dict)

    default_model_id = Column(Integer, ForeignKey("ai_models.id"))
    current_version = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", foreign_keys=[owner_id])
    default_model = relationship("AIModel", foreign_keys=[default_model_id])
    versions = relationship("AgentVersion", back_populates="agent", cascade="all, delete-orphan")
    workflows = relationship("Workflow", back_populates="agent", cascade="all, delete-orphan")


class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    version = Column(Integer, nullable=False)
    # Full snapshot of the agent + workflow at the time of versioning
    snapshot = Column(JSON, nullable=False)
    changelog = Column(Text)
    status = Column(String(40), default="draft")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_by = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime)

    agent = relationship("Agent", back_populates="versions")


# ---------------------------------------------------------------------------
# Workflow & Task Management (§4.2)
# ---------------------------------------------------------------------------

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    name = Column(String(160), nullable=False)
    description = Column(Text)
    version = Column(Integer, default=1)
    status = Column(String(40), default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    agent = relationship("Agent", back_populates="workflows")
    tasks = relationship("Task", back_populates="workflow", cascade="all, delete-orphan",
                         order_by="Task.order_index")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    name = Column(String(160), nullable=False)
    task_type = Column(String(40), nullable=False)
    # task_type: classify | retrieve | call_endpoint | transform |
    #            call_model | validate | generate | escalate | approval | loop | branch
    order_index = Column(Integer, default=0)
    config = Column(JSON, default=dict)
    # depends_on: list of task ids (or names) within the same workflow
    depends_on = Column(JSON, default=list)
    # condition: optional expression (e.g., `intent == "billing"`) gating execution.
    # Empty/null → always run. Evaluated by execution_engine against the workflow context.
    condition = Column(Text)
    preconditions = Column(Text)
    postconditions = Column(Text)
    timeout_seconds = Column(Integer, default=30)
    retry_count = Column(Integer, default=0)
    error_handling = Column(String(40), default="fail")
    # error_handling: fail | retry | fallback | escalate | continue

    # Optional links — a task can target an endpoint, model, or prompt
    endpoint_id = Column(Integer, ForeignKey("endpoints.id"))
    model_id = Column(Integer, ForeignKey("ai_models.id"))
    prompt_id = Column(Integer, ForeignKey("prompts.id"))

    workflow = relationship("Workflow", back_populates="tasks")
    endpoint = relationship("Endpoint", foreign_keys=[endpoint_id])
    model = relationship("AIModel", foreign_keys=[model_id])
    prompt = relationship("Prompt", foreign_keys=[prompt_id])


# ---------------------------------------------------------------------------
# Endpoint Registry (§4.3)
# ---------------------------------------------------------------------------

class Endpoint(Base):
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False, index=True)
    description = Column(Text)

    base_url = Column(String(400), nullable=False)
    path = Column(String(400), default="")
    method = Column(String(10), default="GET")
    # method: GET | POST | PUT | PATCH | DELETE | SOAP

    auth_type = Column(String(40), default="none")
    # auth_type: none | api_key | bearer | oauth | basic | mtls | internal
    # Secrets are stored as references (KMS keys / env var names),
    # never as plaintext credentials.
    auth_config = Column(JSON, default=dict)

    headers = Column(JSON, default=dict)
    query_params_template = Column(JSON, default=dict)
    body_template = Column(Text, default="")
    timeout_seconds = Column(Integer, default=30)
    environment = Column(String(40), default="dev")

    response_schema = Column(JSON, default=dict)
    # response_mapping: { variable_name: { type, json_path, default, ... } }
    response_mapping = Column(JSON, default=dict)
    validation_rules = Column(JSON, default=list)

    estimated_cost_per_call = Column(Float, default=0.0)
    sensitive_fields = Column(JSON, default=list)  # masked in logs

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Multi-Model Support (§4.4)
# ---------------------------------------------------------------------------

class AIModel(Base):
    __tablename__ = "ai_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False, index=True)
    provider = Column(String(80), nullable=False)
    # provider: openai | anthropic | google | local | private | custom
    model_identifier = Column(String(160), nullable=False)
    model_type = Column(String(40), default="cloud")
    # model_type: local | private | cloud | specialized

    context_window = Column(Integer, default=8192)
    max_tokens = Column(Integer, default=2048)
    temperature_default = Column(Float, default=0.7)
    top_p_default = Column(Float, default=1.0)
    supports_tools = Column(Boolean, default=False)
    supports_streaming = Column(Boolean, default=True)

    cost_per_1k_input_tokens = Column(Float, default=0.0)
    cost_per_1k_output_tokens = Column(Float, default=0.0)

    handles_sensitive_data = Column(Boolean, default=False)
    routing_priority = Column(Integer, default=100)
    # lower number = higher priority for fallback routing

    status = Column(String(40), default="active")
    # status: active | deprecated | experimental
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Prompt, Context, Knowledge (§4.5)
# ---------------------------------------------------------------------------

class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False, index=True)
    description = Column(Text)
    template = Column(Text, nullable=False)
    # variables: list of {name, type, required, default, description}
    variables = Column(JSON, default=list)
    category = Column(String(40), default="task")
    # category: system | task | validation | final
    version = Column(Integer, default=1)
    status = Column(String(40), default="draft")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Execution & Observability (§7)
# ---------------------------------------------------------------------------

class Execution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    correlation_id = Column(String(64), unique=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    agent_version = Column(Integer, default=1)
    workflow_id = Column(Integer, ForeignKey("workflows.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)

    status = Column(String(40), default="running")
    # status: running | success | failed | escalated | timeout
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    total_latency_ms = Column(Integer, default=0)

    total_cost = Column(Float, default=0.0)
    estimated_cost = Column(Float, default=0.0)
    total_tokens_input = Column(Integer, default=0)
    total_tokens_output = Column(Integer, default=0)

    schema_compliant = Column(Boolean, default=True)
    escalated = Column(Boolean, default=False)
    error_message = Column(Text)

    agent = relationship("Agent")
    workflow = relationship("Workflow")
    user = relationship("User")
    steps = relationship("ExecutionStep", back_populates="execution",
                         cascade="all, delete-orphan", order_by="ExecutionStep.id")


class ExecutionStep(Base):
    __tablename__ = "execution_steps"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    step_name = Column(String(160), nullable=False)
    step_type = Column(String(40), nullable=False)
    status = Column(String(40), default="pending")
    # status: pending | running | success | failed | skipped | retried

    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)

    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    latency_ms = Column(Integer, default=0)

    cost = Column(Float, default=0.0)
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    retries = Column(Integer, default=0)
    error_message = Column(Text)

    execution = relationship("Execution", back_populates="steps")


# ---------------------------------------------------------------------------
# Cost Validation (§7.3)
# ---------------------------------------------------------------------------

class CostRecord(Base):
    __tablename__ = "cost_records"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    model_id = Column(Integer, ForeignKey("ai_models.id"))
    endpoint_id = Column(Integer, ForeignKey("endpoints.id"))
    record_type = Column(String(40), nullable=False)
    # record_type: model | endpoint | orchestration

    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    department = Column(String(80))
    environment = Column(String(40), default="dev")
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False)
    scope = Column(String(40), nullable=False)
    # scope: global | agent | department | user | environment
    scope_id = Column(String(80))   # agent_id / department name / user_id ...
    period = Column(String(20), default="monthly")
    # period: daily | weekly | monthly
    limit_amount = Column(Float, nullable=False)
    warning_threshold = Column(Float, default=0.8)
    hard_limit = Column(Boolean, default=False)
    current_consumption = Column(Float, default=0.0)
    period_start = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
