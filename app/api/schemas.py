from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReportRequest(Strict):
    incident_id: str
    format: Literal["json", "csv", "html"]


class ScanRequest(Strict):
    root: str


class SettingsRequest(Strict):
    expected_version: int = Field(ge=1)
    patch: dict


class ReportSelection(Strict):
    formats: list[Literal["html", "json", "csv"]] = Field(min_length=1, max_length=3)
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def valid_range(self):
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("Dates must include a timezone")
        if self.start >= self.end:
            raise ValueError("End must be after start")
        if len(set(self.formats)) != len(self.formats):
            raise ValueError("Choose each format once")
        return self
