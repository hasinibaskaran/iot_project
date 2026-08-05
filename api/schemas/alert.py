from pydantic import BaseModel, Field
from typing import List

class AlertRequest(BaseModel):
    train_number: str = Field(..., description="e.g., '12601'")
    trip_number: str = Field(..., description="e.g., 'TRP-2026-8849'")
    coach_number: str = Field(..., description="e.g., 'A1'")
    last_station_id: str = Field(..., description="e.g., 'AJJ'")
    next_station_id: str = Field(..., description="e.g., 'KPD'")
    time: str = Field(..., description="Timestamp in format 'YYYY-MM-DD HH:MM:SS'")

class SmsResponseDetail(BaseModel):
    return_val: bool = Field(..., alias="return")
    request_id: str
    message: List[str]

    class Config:
        populate_by_name = True

class AlertResponse(BaseModel):
    success: bool
    dispatched_to: str
    sms_response: SmsResponseDetail
