from app.graphql.inputs.application import (
    AddApplicationNoteInput,
    ApplicationFiltersInput,
    ApplicationQueryInput,
    ApplicationsQueryInput,
    BulkUpdateApplicationStatusInput,
    SubmitApplicationInput,
    UpdateApplicationStatusInput,
)
from app.graphql.inputs.ai import (
    GenerateCandidateEvaluationInput,
    GenerateJobCriteriaInput,
    ProcessApplicationResumeInput,
    RecommendedCandidatesInput,
    ScreenJobApplicantsInput,
)
from app.graphql.inputs.common import OffsetPaginationInput
from app.graphql.inputs.job import CreateJobInput, JobQueryInput, JobsQueryInput

__all__ = [
    "AddApplicationNoteInput",
    "ApplicationFiltersInput",
    "ApplicationQueryInput",
    "ApplicationsQueryInput",
    "BulkUpdateApplicationStatusInput",
    "CreateJobInput",
    "GenerateCandidateEvaluationInput",
    "GenerateJobCriteriaInput",
    "JobQueryInput",
    "JobsQueryInput",
    "OffsetPaginationInput",
    "ProcessApplicationResumeInput",
    "RecommendedCandidatesInput",
    "ScreenJobApplicantsInput",
    "SubmitApplicationInput",
    "UpdateApplicationStatusInput",
]
