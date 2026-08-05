from supabase import AsyncClient
from api.repo.trip_repo import TripRepository
from api.repo.route_repo import RouteRepository
from api.schemas.trip import InitTripResponse, StationInfo
from fastapi import HTTPException, status

class TripService:
    def __init__(self, db: AsyncClient):
        self.trip_repo = TripRepository(db)
        self.route_repo = RouteRepository(db)

    async def initialize_trip(self, train_number: str) -> InitTripResponse:
        trips = await self.trip_repo.get_active_or_scheduled_trips(train_number)
        if not trips:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active or scheduled trips found for train {train_number}"
            )

        # Sort trips: active first, then closest start time
        active_trips = [t for t in trips if t["status"] == "ACTIVE"]
        if active_trips:
            selected_trip = sorted(active_trips, key=lambda x: x["start_time"])[0]
        else:
            scheduled_trips = [t for t in trips if t["status"] == "SCHEDULED"]
            selected_trip = sorted(scheduled_trips, key=lambda x: x["start_time"])[0]

        stations = await self.route_repo.get_stations_by_route(train_number, selected_trip["direction"])
        if not stations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No route stations found for train {train_number} in direction {selected_trip['direction']}"
            )

        return InitTripResponse(
            success=True,
            train_number=train_number,
            trip_number=selected_trip["trip_number"],
            direction=selected_trip["direction"],
            stations=[
                StationInfo(
                    sequence_order=s["sequence_order"],
                    station_id=s["station_id"],
                    station_name=s["station_name"]
                ) for s in stations
            ]
        )
