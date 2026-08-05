from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Train(BaseModel):
    train_number: str
    train_name: str

class Trip(BaseModel):
    id: Optional[str] = None
    trip_number: str
    train_number: str
    direction: str
    status: str
    start_time: datetime

class TrainRouteStation(BaseModel):
    id: Optional[str] = None
    train_number: str
    direction: str
    sequence_order: int
    station_id: str
    station_name: str
    manager_phone: str

class GatewayDevice(BaseModel):
    device_id: str
    train_number: str
    status: str

class ObhsStaff(BaseModel):
    id: Optional[str] = None
    trip_number: str
    coach_number: str
    name: str
    phone_number: str
    is_active: bool

class AlertLog(BaseModel):
    id: Optional[str] = None
    device_id: Optional[str] = None
    train_number: str
    trip_number: str
    coach_number: str
    last_station_id: str
    next_station_id: str
    dispatched_to_type: str
    recipient_phone: str
    sms_status: str
    created_at: Optional[datetime] = None
