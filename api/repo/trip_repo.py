from supabase import AsyncClient

class TripRepository:
    def __init__(self, db: AsyncClient):
        self.db = db

    async def get_active_or_scheduled_trips(self, train_number: str):
        response = await self.db.table("trip") \
            .select("*") \
            .eq("train_number", train_number) \
            .in_("status", ["ACTIVE", "SCHEDULED"]) \
            .execute()
        return response.data

    async def get_trip_by_number(self, trip_number: str):
        response = await self.db.table("trip") \
            .select("*") \
            .eq("trip_number", trip_number) \
            .execute()
        return response.data[0] if response.data else None
