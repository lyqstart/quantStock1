"""operations control and audit trail

Revision ID: 0008_ops_control
Revises: 0007_sample_runtime
Create Date: 2026-07-27
"""
from alembic import op

revision = "0008_ops_control"
down_revision = "0007_sample_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
        CREATE TABLE audit.audit_event (
            audit_event_id UUID PRIMARY KEY,
            object_type VARCHAR(64) NOT NULL,
            object_id VARCHAR(160) NOT NULL,
            action VARCHAR(64) NOT NULL,
            before_status VARCHAR(32),
            after_status VARCHAR(32),
            reason TEXT,
            actor_type VARCHAR(32) NOT NULL,
            actor_id VARCHAR(128) NOT NULL,
            trace_id UUID,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            occurred_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    ''')
    op.execute(
        "CREATE INDEX ix_audit_event_object_time ON audit.audit_event "
        "(object_type, object_id, occurred_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_audit_event_action_time ON audit.audit_event "
        "(action, occurred_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit.audit_event")
