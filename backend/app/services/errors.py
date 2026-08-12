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
