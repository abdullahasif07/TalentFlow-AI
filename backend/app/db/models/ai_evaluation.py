from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tortoise import fields

from app.db.models.base import TimestampedModel
from app.enums import EvaluationConfidence

if TYPE_CHECKING:
    from app.db.models.application import Application


class AIEvaluation(TimestampedModel):
    id = fields.IntField(primary_key=True)
    application: fields.OneToOneRelation["Application"] = fields.OneToOneField(
        "models.Application", related_name="ai_evaluation", on_delete=fields.CASCADE
    )
    overall_score = fields.DecimalField(max_digits=5, decimal_places=2)
    recommendation = fields.TextField()
    confidence = fields.CharEnumField(EvaluationConfidence, max_length=20)
    strengths: dict[str, Any] | list[Any] = fields.JSONField(default=list)
    gaps: dict[str, Any] | list[Any] = fields.JSONField(default=list)
    evidence: dict[str, Any] | list[Any] = fields.JSONField(default=list)
    analysis_json: dict[str, Any] | list[Any] = fields.JSONField(default=dict)

    class Meta:
        table = "ai_evaluations"
