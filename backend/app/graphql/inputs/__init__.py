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
from app.graphql.inputs.outreach import (
    ApproveOutreachInput,
    GenerateOutreachInput,
    SendOutreachInput,
    UpdateOutreachDraftInput,
)

__all__ = [
    "AddApplicationNoteInput",
    "ApplicationFiltersInput",
    "ApplicationQueryInput",
    "ApplicationsQueryInput",
    "ApproveOutreachInput",
    "BulkUpdateApplicationStatusInput",
    "CreateJobInput",
    "GenerateCandidateEvaluationInput",
    "GenerateJobCriteriaInput",
    "GenerateOutreachInput",
    "JobQueryInput",
    "JobsQueryInput",
    "OffsetPaginationInput",
    "ProcessApplicationResumeInput",
    "RecommendedCandidatesInput",
    "ScreenJobApplicantsInput",
    "SendOutreachInput",
    "SubmitApplicationInput",
    "UpdateApplicationStatusInput",
    "UpdateOutreachDraftInput",
]
