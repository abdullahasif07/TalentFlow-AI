from app.graphql.inputs.application import (
    ApplicationFiltersInput,
    ApplicationQueryInput,
    ApplicationsQueryInput,
    SubmitApplicationInput,
    UpdateApplicationStatusInput,
)
from app.graphql.inputs.common import OffsetPaginationInput
from app.graphql.inputs.job import CreateJobInput, JobQueryInput, JobsQueryInput

__all__ = [
    "ApplicationFiltersInput",
    "ApplicationQueryInput",
    "ApplicationsQueryInput",
    "CreateJobInput",
    "JobQueryInput",
    "JobsQueryInput",
    "OffsetPaginationInput",
    "SubmitApplicationInput",
    "UpdateApplicationStatusInput",
]
