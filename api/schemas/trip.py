from pydantic import BaseModel
from typing import List

class StationInfo(BaseModel):
    sequence_order: int
    station_id: str
    station_name: str

class InitTripResponse(BaseModel):
    success: bool
    train_number: str
    trip_number: str
    direction: str
    stations: List[StationInfo]
