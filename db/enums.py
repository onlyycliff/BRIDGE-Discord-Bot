import enum


class FormStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    closed = "closed"


class QuestionType(str, enum.Enum):
    single_choice = "single_choice"
    multi_choice = "multi_choice"
    text = "text"
