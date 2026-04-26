"""Seed sample data so the platform is usable out of the box."""
from sqlalchemy.orm import Session

from . import models


def _seed_environment_settings_if_empty(db: Session) -> None:
    if db.query(models.EnvironmentSetting).count() > 0:
        return
    environment_settings = [
        # DEV
        models.EnvironmentSetting(environment="dev", key="OUC_API_PROTOCOL", value="http", description="Protocol for OUC API"),
        models.EnvironmentSetting(environment="dev", key="OUC_API_HOST", value="localhost", description="OUC API host"),
        models.EnvironmentSetting(environment="dev", key="OUC_API_PORT", value="8081", description="OUC API port"),
        models.EnvironmentSetting(environment="dev", key="OUC_API_PATH", value="/aiservice/1.0.1", description="Base path for OUC API"),
        models.EnvironmentSetting(environment="dev", key="OUC_API_BEARER_TOKEN", value="dev-token-placeholder", is_secret=True, description="Bearer token for OUC API"),
        # QA
        models.EnvironmentSetting(environment="qa", key="OUC_API_PROTOCOL", value="https", description="Protocol for OUC API"),
        models.EnvironmentSetting(environment="qa", key="OUC_API_HOST", value="qa-ouc.example.internal", description="OUC API host"),
        models.EnvironmentSetting(environment="qa", key="OUC_API_PORT", value="443", description="OUC API port"),
        models.EnvironmentSetting(environment="qa", key="OUC_API_PATH", value="/aiservice/1.0.1", description="Base path for OUC API"),
        models.EnvironmentSetting(environment="qa", key="OUC_API_BEARER_TOKEN", value="qa-token-placeholder", is_secret=True, description="Bearer token for OUC API"),
        # PROD
        models.EnvironmentSetting(environment="prod", key="OUC_API_PROTOCOL", value="https", description="Protocol for OUC API"),
        models.EnvironmentSetting(environment="prod", key="OUC_API_HOST", value="prod-ouc.example.internal", description="OUC API host"),
        models.EnvironmentSetting(environment="prod", key="OUC_API_PORT", value="443", description="OUC API port"),
        models.EnvironmentSetting(environment="prod", key="OUC_API_PATH", value="/aiservice/1.0.1", description="Base path for OUC API"),
        models.EnvironmentSetting(environment="prod", key="OUC_API_BEARER_TOKEN", value="prod-token-placeholder", is_secret=True, description="Bearer token for OUC API"),
    ]
    db.add_all(environment_settings)
    db.flush()


def seed_if_empty(db: Session) -> None:
    if db.query(models.User).count() > 0:
        _seed_environment_settings_if_empty(db)
        db.commit()
        return  # already seeded

    # ---- Users ----
    users = [
        models.User(username="alice", email="alice@example.com", full_name="Alice Designer", role="designer"),
        models.User(username="bob", email="bob@example.com", full_name="Bob Admin", role="admin"),
        models.User(username="carol", email="carol@example.com", full_name="Carol Engineer", role="engineer"),
    ]
    db.add_all(users)
    db.flush()

    # ---- Environment Settings ----
    _seed_environment_settings_if_empty(db)

    # ---- AI Models ----
    ai_models = [
        models.AIModel(
            name="GPT-4o (cloud)", provider="openai", model_identifier="gpt-4o",
            model_type="cloud", context_window=128000, max_tokens=4096,
            cost_per_1k_input_tokens=0.005, cost_per_1k_output_tokens=0.015,
            supports_tools=True, routing_priority=20,
        ),
        models.AIModel(
            name="Claude Sonnet (cloud)", provider="anthropic", model_identifier="claude-sonnet-4-6",
            model_type="cloud", context_window=200000, max_tokens=8192,
            cost_per_1k_input_tokens=0.003, cost_per_1k_output_tokens=0.015,
            supports_tools=True, routing_priority=10,
        ),
        models.AIModel(
            name="Llama 3 70B (local)", provider="local", model_identifier="llama-3-70b",
            model_type="local", context_window=8192, max_tokens=4096,
            cost_per_1k_input_tokens=0.0, cost_per_1k_output_tokens=0.0,
            supports_tools=False, handles_sensitive_data=True, routing_priority=5,
        ),
    ]
    db.add_all(ai_models)
    db.flush()

    # ---- Endpoints (parameterized from IndraAI/EWAOUCEAM hard-coded domain) ----
    endpoints = [
        models.Endpoint(
            name="OUC Profile Details",
            description="Returns account profile/tariff context from OUC /profileDetails.",
            base_url="http://OUC_API_HOST:OUC_API_PORT",
            path="/aiservice/1.0.1/profileDetails",
            method="GET",
            auth_type="bearer",
            auth_config={"secret_ref": "env:OUC_API_TOKEN"},
            headers={"Accept": "application/json"},
            query_params_template={"account": "{{ input.account_id }}"},
            response_mapping={
                "profile_details": {"json_path": "data"},
            },
            estimated_cost_per_call=0.002,
            sensitive_fields=["account_id"],
            environment="dev",
        ),
        models.Endpoint(
            name="OUC Consumption Details",
            description="Returns consumption history from OUC /consumptionDetails.",
            base_url="http://OUC_API_HOST:OUC_API_PORT",
            path="/aiservice/1.0.1/consumptionDetails",
            method="GET",
            auth_type="bearer",
            auth_config={"secret_ref": "env:OUC_API_TOKEN"},
            query_params_template={"accountNo": "{{ input.account_id }}"},
            response_mapping={"consumption_details": {"json_path": "data"}},
            estimated_cost_per_call=0.001,
            environment="dev",
        ),
        models.Endpoint(
            name="OUC Bill Details",
            description="Returns latest billing details from OUC /billDetails.",
            base_url="http://OUC_API_HOST:OUC_API_PORT",
            path="/aiservice/1.0.1/billDetails",
            method="GET",
            auth_type="bearer",
            auth_config={"secret_ref": "env:OUC_API_TOKEN"},
            query_params_template={
                "accountNo": "{{ input.account_id }}",
                "nBills": "12",
                "date": "{{ input.reference_date }}",
            },
            response_mapping={"bill_details": {"json_path": "data"}},
            estimated_cost_per_call=0.0015,
            environment="dev",
        ),
        models.Endpoint(
            name="OUC Hierarchy Details",
            description="Returns hierarchy/share data from OUC /hierarchyDetails.",
            base_url="http://OUC_API_HOST:OUC_API_PORT",
            path="/aiservice/1.0.1/hierarchyDetails",
            method="GET",
            auth_type="bearer",
            auth_config={"secret_ref": "env:OUC_API_TOKEN"},
            query_params_template={"accountNo": "{{ input.account_id }}"},
            response_mapping={"hierarchy_details": {"json_path": "data"}},
            estimated_cost_per_call=0.001,
            environment="dev",
        ),
        models.Endpoint(
            name="OUC Historical RCCS",
            description="Returns previous complaints from OUC /historicalRccs.",
            base_url="http://OUC_API_HOST:OUC_API_PORT",
            path="/aiservice/1.0.1/historicalRccs",
            method="GET",
            auth_type="bearer",
            auth_config={"secret_ref": "env:OUC_API_TOKEN"},
            query_params_template={"accountNo": "{{ input.account_id }}"},
            response_mapping={"historical_complaints": {"json_path": "data"}},
            estimated_cost_per_call=0.001,
            environment="dev",
        ),
    ]
    db.add_all(endpoints)
    db.flush()

    # ---- Prompts (from IndraAI/EWAOUCEAM/src/prompts/config.yml) ----
    prompts = [
        models.Prompt(
            name="EWA Preanalysis Prompt",
            description="Extract service, typology and period from complaint context.",
            template=(
                "You are an expert assistant specialized in utility complaint analysis. "
                "Extract service (electricity|water|municipality|mix|unspecified), "
                "typology, and period from complaint text and context dates. "
                "If service cannot be inferred confidently, return 'unspecified'. "
                "Return only valid JSON."
            ),
            variables=[],
            category="system",
            status="published",
            created_by=users[0].id,
        ),
        models.Prompt(
            name="EWA Reasoning Prompt",
            description="Synthesizes checks into root cause and recommended actions.",
            template=(
                "Analyze complaint context and findings from profile, consumption, "
                "hierarchy, billing, and historical complaints checks.\n"
                "Prioritize duplicate/recurrent cases, hierarchy-share logic, "
                "consumption spikes, tariff impacts, and data-quality anomalies.\n"
                "Return JSON with: root_cause_summary, technical_explanation, "
                "recommended_actions[], complexity_score."
            ),
            variables=[
                {"name": "profile_details", "type": "object", "required": False},
                {"name": "consumption_details", "type": "array", "required": False},
                {"name": "hierarchy_details", "type": "array", "required": False},
                {"name": "bill_details", "type": "array", "required": False},
                {"name": "historical_complaints", "type": "object", "required": False},
            ],
            category="final",
            status="published",
            created_by=users[0].id,
        ),
    ]
    db.add_all(prompts)
    db.flush()

    # ---- Agent + Workflow ----
    agent = models.Agent(
        name="EWA Complaint Analysis Agent",
        description="Analyze EWA utility complaints using OUC API checks and reasoning.",
        objective="Determine probable root cause and generate technical explanation and next actions.",
        business_domain="utility_complaints",
        owner_id=users[0].id,
        environment="dev",
        status="test",
        system_prompt=prompts[0].template,
        business_instructions="Focus on service-specific diagnostics and deterministic API findings.",
        constraints="Do not invent account facts; use only retrieved OUC context and explicit complaint text.",
        response_format="json",
        fallback_behavior="Escalate to backoffice when confidence is low or findings are contradictory.",
        input_schema={
            "type": "object",
            "required": ["account_id", "complaint_reference", "customer_comments", "reference_date"],
            "properties": {
                "account_id": {"type": "string"},
                "complaint_reference": {"type": "string"},
                "customer_comments": {"type": "string"},
                "reference_date": {"type": "string", "description": "YYYY-MM-DD"},
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "root_cause_summary": {"type": "string"},
                "technical_explanation": {"type": "string"},
                "recommended_actions": {"type": "array"},
                "complexity_score": {"type": "number"},
            },
            "required": ["root_cause_summary", "technical_explanation", "recommended_actions"],
        },
        default_model_id=ai_models[2].id,
    )
    db.add(agent)
    db.flush()

    workflow = models.Workflow(
        agent_id=agent.id,
        name="EWA Complaint Analysis Flow v1",
        description="Preanalysis → profile/tariff → consumption → hierarchy → billing → historical → reasoning.",
        status="published",
    )
    db.add(workflow)
    db.flush()

    tasks = [
        models.Task(
            workflow_id=workflow.id, name="PreAnalysis", task_type="classify",
            order_index=1,
            config={
                "categories": [
                    "high_bill", "not_received_bill", "reading_error", "supply_issue",
                    "technical_issue", "payment_issue", "contract_issue", "other",
                ]
            },
            timeout_seconds=10, retry_count=1, error_handling="continue",
        ),
        models.Task(
            workflow_id=workflow.id, name="AccountTariffCheck", task_type="call_endpoint",
            order_index=2, endpoint_id=endpoints[0].id,
            timeout_seconds=15, retry_count=2, error_handling="fallback",
        ),
        models.Task(
            workflow_id=workflow.id, name="ConsumptionCheck", task_type="call_endpoint",
            order_index=3, endpoint_id=endpoints[1].id, depends_on=[],
            timeout_seconds=15, retry_count=1, error_handling="continue",
        ),
        models.Task(
            workflow_id=workflow.id, name="HierarchyCheck", task_type="call_endpoint",
            order_index=4,
            endpoint_id=endpoints[3].id,
            timeout_seconds=15, retry_count=1, error_handling="continue",
        ),
        models.Task(
            workflow_id=workflow.id, name="BillingsChecks", task_type="call_endpoint",
            order_index=5,
            endpoint_id=endpoints[2].id,
            timeout_seconds=15, retry_count=1, error_handling="continue",
        ),
        models.Task(
            workflow_id=workflow.id, name="PreviousComplaints", task_type="call_endpoint",
            order_index=6,
            endpoint_id=endpoints[4].id,
            timeout_seconds=15, retry_count=1, error_handling="continue",
        ),
        models.Task(
            workflow_id=workflow.id, name="Reasoning", task_type="generate",
            order_index=7,
            model_id=ai_models[2].id, prompt_id=prompts[1].id,
            timeout_seconds=30, retry_count=1, error_handling="fail",
        ),
        models.Task(
            workflow_id=workflow.id, name="Validate output schema", task_type="validate",
            order_index=8,
            config={"required_keys": ["text"]},
            timeout_seconds=5, error_handling="escalate",
        ),
    ]
    db.add_all(tasks)

    # Sample budget
    db.add(
        models.Budget(
            name="Default Monthly Budget",
            scope="global",
            scope_id=None,
            period="monthly",
            limit_amount=500.0,
            warning_threshold=0.8,
            hard_limit=False,
        )
    )

    db.commit()
