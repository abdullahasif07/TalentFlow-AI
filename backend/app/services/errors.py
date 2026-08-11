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
