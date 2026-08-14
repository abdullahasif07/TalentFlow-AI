import strawberry


@strawberry.input
class GenerateJobCriteriaInput:
    job_id: strawberry.ID


@strawberry.input
class ProcessApplicationResumeInput:
    application_id: strawberry.ID


@strawberry.input
class GenerateCandidateEvaluationInput:
    application_id: strawberry.ID


@strawberry.input
class ScreenJobApplicantsInput:
    job_id: strawberry.ID


@strawberry.input
class RecommendedCandidatesInput:
    job_id: strawberry.ID
    limit: int = 5
