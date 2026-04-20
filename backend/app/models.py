from pydantic import BaseModel


class Race(BaseModel):
    session_key: int
    meeting_name: str
    country_name: str
    circuit_short_name: str
    date_start: str
    year: int


class DriverResult(BaseModel):
    position: int
    driver_number: int
    full_name: str
    team_name: str | None = None
    points: float | None = None


class CommentaryResponse(BaseModel):
    session_key: int
    race_title: str
    podium: list[DriverResult]
    full_results: list[DriverResult]
    commentary: str
