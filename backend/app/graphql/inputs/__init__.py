from app.graphql.inputs.application import (
    AddApplicationNoteInput,
    ApplicationFiltersInput,
    ApplicationQueryInput,
    ApplicationsQueryInput,
    BulkUpdateApplicationStatusInput,
    SubmitApplicationInput,
    UpdateApplicationStatusInput,
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
    "JobQueryInput",
    "JobsQueryInput",
    "OffsetPaginationInput",
    "SubmitApplicationInput",
    "UpdateApplicationStatusInput",
]
