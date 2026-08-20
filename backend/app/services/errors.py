class ApplicationSubmissionError(Exception):
    """Base exception for safe, client-facing application submission errors."""


class JobNotFoundError(ApplicationSubmissionError):
    pass


class JobClosedError(ApplicationSubmissionError):
    pass


class DuplicateApplicationError(ApplicationSubmissionError):
    pass


class InvalidCandidateInformationError(ApplicationSubmissionError):
    pass


class InvalidApplicationInformationError(ApplicationSubmissionError):
    pass


class MissingResumeError(ApplicationSubmissionError):
    pass


class InvalidResumeTypeError(ApplicationSubmissionError):
    pass


class ResumeTooLargeError(ApplicationSubmissionError):
    pass


class ResumeExtractionError(Exception):
    """Base exception for safe, client-facing resume extraction errors."""


class ResumeRecordNotFoundError(ResumeExtractionError):
    pass


class ResumeFileNotFoundError(ResumeExtractionError):
    pass


class InvalidResumePDFError(ResumeExtractionError):
    pass


class ResumeTextNotFoundError(ResumeExtractionError):
    pass


class ResumeParsingError(Exception):
    """Base exception for safe, client-facing structured resume parsing errors."""


class EmptyResumeTextError(ResumeParsingError):
    pass


class InvalidResumeParsingOutputError(ResumeParsingError):
    pass


class ResumeParsingProviderError(ResumeParsingError):
    pass


class JobCriteriaError(Exception):
    """Base exception for safe, client-facing job criteria errors."""


class JobCriteriaJobNotFoundError(JobCriteriaError):
    pass


class InvalidJobInformationError(JobCriteriaError):
    pass


class InvalidJobCriteriaOutputError(JobCriteriaError):
    pass


class JobCriteriaProviderError(JobCriteriaError):
    pass


class CandidateEvaluationError(Exception):
    """Base exception for safe, client-facing candidate evaluation errors."""


class EvaluationApplicationNotFoundError(CandidateEvaluationError):
    pass


class MissingStructuredResumeDataError(CandidateEvaluationError):
    pass


class MissingJobEvaluationCriteriaError(CandidateEvaluationError):
    pass


class InvalidCandidateEvaluationInputError(CandidateEvaluationError):
    pass


class InvalidCandidateEvaluationOutputError(CandidateEvaluationError):
    pass


class CandidateEvaluationProviderError(CandidateEvaluationError):
    pass


class OutreachGenerationError(Exception):
    """Base exception for safe, client-facing outreach generation errors."""


class OutreachApplicationNotFoundError(OutreachGenerationError):
    pass


class OutreachCandidateNotFoundError(OutreachGenerationError):
    pass


class OutreachJobNotFoundError(OutreachGenerationError):
    pass


class OutreachCompanyNotFoundError(OutreachGenerationError):
    pass


class MissingOutreachResumeDataError(OutreachGenerationError):
    pass


class InvalidOutreachContextError(OutreachGenerationError):
    pass


class InvalidOutreachInstructionError(OutreachGenerationError):
    pass


class InvalidOutreachOutputError(OutreachGenerationError):
    pass


class OutreachGenerationProviderError(OutreachGenerationError):
    pass


class OutreachWorkflowError(Exception):
    """Base exception for safe, client-facing outreach workflow errors."""


class OutreachNotFoundError(OutreachWorkflowError):
    pass


class InvalidOutreachSubjectError(OutreachWorkflowError):
    pass


class InvalidOutreachBodyError(OutreachWorkflowError):
    pass


class InvalidOutreachStatusTransitionError(OutreachWorkflowError):
    pass


class OutreachDeliveryError(OutreachWorkflowError):
    pass


class AIProcessingRequestError(Exception):
    """Base exception for safe AI task-enqueue failures."""


class ProcessingResourceNotFoundError(AIProcessingRequestError):
    pass


class ProcessingPrerequisiteError(AIProcessingRequestError):
    pass


class ProcessingQueueError(AIProcessingRequestError):
    pass


class ApplicationPipelineError(Exception):
    """Base exception for safe, client-facing pipeline errors."""


class ApplicationNotFoundError(ApplicationPipelineError):
    pass


class InvalidStatusTransitionError(ApplicationPipelineError):
    pass


class InvalidPipelineActorError(ApplicationPipelineError):
    pass


class RecruiterNotFoundError(ApplicationPipelineError):
    pass


class RecruiterCompanyMismatchError(ApplicationPipelineError):
    pass


class ApplicationNoteError(Exception):
    """Base exception for safe, client-facing application note errors."""


class InvalidApplicationNoteError(ApplicationNoteError):
    pass
