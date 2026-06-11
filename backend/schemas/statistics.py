from pydantic import BaseModel


class GroupStat(BaseModel):
    group: str
    count: int


class ClassStat(BaseModel):
    class_name: str
    count: int


class HourlyStat(BaseModel):
    time: str
    count: int


class StatisticsResponse(BaseModel):
    total_count: int
    most_common_class: str
    most_common_class_count: int
    most_common_class_confidence: float
    group_distribution: list[GroupStat]
    class_distribution: list[ClassStat]
    hourly_distribution: list[HourlyStat]
