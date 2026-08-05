from fastapi import APIRouter, Depends, Query
from supabase import AsyncClient
from api.database import get_supabase
from api.schemas.trip import InitTripResponse
from api.services.trip_service import TripService
from api.security import verify_api_key

router = APIRouter(
    prefix="/api",
    tags=["Trips"],
    dependencies=[Depends(verify_api_key)]
)

@router.get("/init-trip", response_model=InitTripResponse)
async def init_trip(
    train_number: str = Query(..., description="The train number to fetch routes/trips for"),
    db: AsyncClient = Depends(get_supabase)
):
    """
    Initializes a trip for the requested train number.
    Returns scheduled or active trip sequence and route stations.
    """
    trip_service = TripService(db)
    return await trip_service.initialize_trip(train_number)
