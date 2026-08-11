from enum import Enum


class ApplicationStatus(str, Enum):
    APPLIED = "APPLIED"
    AI_REVIEWED = "AI_REVIEWED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    SHORTLISTED = "SHORTLISTED"
    CONTACTED = "CONTACTED"
    REPLIED = "REPLIED"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    HIRED = "HIRED"
    REJECTED = "REJECTED"


class ApplicationSort(str, Enum):
    NEWEST = "NEWEST"
    OLDEST = "OLDEST"
    FIT_SCORE_ASC = "FIT_SCORE_ASC"
    FIT_SCORE_DESC = "FIT_SCORE_DESC"
