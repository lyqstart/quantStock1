"""seed initial data catalog

Revision ID: 0002_seed_catalog
Revises: 0001_p3_core
Create Date: 2026-07-27
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0002_seed_catalog"
down_revision = "0001_p3_core"
branch_labels = None
depends_on = None

NS = uuid.UUID("f49c0ed2-6b6d-4a65-9e8d-03de74809391")

def uid(value: str) -> uuid.UUID:
    return uuid.uuid5(NS, value)


def upgrade() -> None:
    conn = op.get_bind()
    source = sa.table(
        "data_source",
        sa.column("source_id", UUID(as_uuid=True)), sa.column("source_code", sa.String),
        sa.column("source_name", sa.String), sa.column("source_type", sa.String),
        sa.column("provider", sa.String), sa.column("status", sa.String),
        sa.column("credential_ref", sa.String), sa.column("base_config", JSONB),
        sa.column("health_status", sa.String), schema="meta",
    )
    conn.execute(source.insert(), [
        {"source_id": uid("source:tushare"), "source_code": "tushare", "source_name": "Tushare", "source_type": "api", "provider": "Tushare", "status": "enabled", "credential_ref": "env:TUSHARE_TOKEN", "base_config": {}, "health_status": "unknown"},
        {"source_id": uid("source:akshare"), "source_code": "akshare", "source_name": "AKShare", "source_type": "api", "provider": "AKShare", "status": "enabled", "credential_ref": None, "base_config": {}, "health_status": "unknown"},
        {"source_id": uid("source:legacy_quantstock"), "source_code": "legacy_quantstock", "source_name": "旧quantStock", "source_type": "legacy_database", "provider": "legacy", "status": "enabled", "credential_ref": None, "base_config": {"binding_type": "migration_only"}, "health_status": "unknown"},
    ])

    item = sa.table(
        "data_item",
        sa.column("data_item_id", UUID(as_uuid=True)), sa.column("code", sa.String),
        sa.column("name", sa.String), sa.column("domain", sa.String), sa.column("grain", sa.String),
        sa.column("frequency", sa.String), sa.column("availability_rule", JSONB),
        sa.column("status", sa.String), sa.column("implementation_priority", sa.String),
        sa.column("quality_required", sa.Boolean), sa.column("strategy_exposed", sa.Boolean),
        sa.column("schema_version", sa.String), sa.column("critical", sa.Boolean), schema="meta",
    )
    items = [
        ("trade_calendar","交易日历","D01","交易所+日期","day","A",True),
        ("stock_basic","股票基础信息","D01","股票",None,"A",True),
        ("stock_daily","A股日线","D02","股票+交易日","day","A",True),
        ("stock_adj_factor","复权因子","D02","股票+交易日","day","A",True),
        ("stock_daily_basic","每日指标","D02","股票+交易日","day","A",True),
        ("stock_suspend","停复牌","D02","股票+日期+状态","event","A",False),
        ("stock_limit_price","涨跌停价格","D02","股票+交易日","day","A",False),
        ("stock_minute","A股历史分钟","D03","股票+频率+交易时间","minute","E",False),
        ("financial_income","利润表","D05","股票+报告期+版本","report","B",False),
        ("financial_indicator","财务指标","D05","股票+报告期+版本","report","B",False),
    ]
    conn.execute(item.insert(), [{
        "data_item_id": uid(f"item:{code}"), "code": code, "name": name, "domain": domain,
        "grain": grain, "frequency": freq, "availability_rule": {}, "status": "validated",
        "implementation_priority": priority, "quality_required": True, "strategy_exposed": True,
        "schema_version": "v1", "critical": critical,
    } for code,name,domain,grain,freq,priority,critical in items])

    binding = sa.table(
        "source_binding",
        sa.column("source_binding_id", UUID(as_uuid=True)), sa.column("data_item_id", UUID(as_uuid=True)),
        sa.column("source_id", UUID(as_uuid=True)), sa.column("binding_code", sa.String),
        sa.column("api_name", sa.String), sa.column("adapter_type", sa.String),
        sa.column("binding_type", sa.String), sa.column("priority", sa.Integer), sa.column("enabled", sa.Boolean),
        sa.column("status", sa.String), sa.column("permission_type", sa.String),
        sa.column("max_rows_per_request", sa.Integer), sa.column("field_mapping_version", sa.String),
        sa.column("request_policy_version", sa.String), sa.column("capability_status", sa.String),
        sa.column("update_time_rule", JSONB), sa.column("supports_pagination", sa.Boolean),
        sa.column("config", JSONB), schema="meta",
    )
    apis = {
        "trade_calendar": ("trade_cal", "points", None),
        "stock_basic": ("stock_basic", "points", 6000),
        "stock_daily": ("daily", "points", 6000),
        "stock_adj_factor": ("adj_factor", "points", None),
        "stock_daily_basic": ("daily_basic", "points", 6000),
        "stock_suspend": ("suspend_d", "points", None),
        "stock_limit_price": ("stk_limit", "points", 5800),
        "stock_minute": ("stk_mins", "entitlement", 8000),
        "financial_income": ("income", "points", None),
        "financial_indicator": ("fina_indicator", "points", 100),
    }
    conn.execute(binding.insert(), [{
        "source_binding_id": uid(f"binding:tushare:{code}"), "data_item_id": uid(f"item:{code}"),
        "source_id": uid("source:tushare"), "binding_code": f"tushare:{code}", "api_name": api,
        "adapter_type": "tushare", "binding_type": "online", "priority": 1, "enabled": True,
        "status": "enabled", "permission_type": permission, "max_rows_per_request": max_rows,
        "field_mapping_version": "v1", "request_policy_version": "v1", "capability_status": "unknown",
        "update_time_rule": {}, "supports_pagination": False, "config": {},
    } for code,(api,permission,max_rows) in apis.items()])


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM meta.source_binding WHERE binding_code LIKE 'tushare:%'"))
    conn.execute(sa.text("DELETE FROM meta.data_item WHERE code IN ('trade_calendar','stock_basic','stock_daily','stock_adj_factor','stock_daily_basic','stock_suspend','stock_limit_price','stock_minute','financial_income','financial_indicator')"))
    conn.execute(sa.text("DELETE FROM meta.data_source WHERE source_code IN ('tushare','akshare','legacy_quantstock')"))
