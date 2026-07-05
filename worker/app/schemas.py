"""Unified finding schema. LLM must return JSON matching FindingList."""
from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class Category(str, Enum):
    bug = "bug"
    security = "security"
    performance = "performance"
    concurrency = "concurrency"
    maintainability = "maintainability"
    architecture = "architecture"
    style = "style"


class Finding(BaseModel):
    title: str
    description: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    category: Category
    explanation: str
    suggested_fix: str
    code_example: str = ""
    file: str
    line: int


class FindingList(BaseModel):
    findings: list[Finding]
