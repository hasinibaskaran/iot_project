from supabase import AsyncClient

class RouteRepository:
    def __init__(self, db: AsyncClient):
        self.db = db

    async def get_stations_by_route(self, train_number: str, direction: str):
        response = await self.db.table("train_route_station") \
            .select("sequence_order, station_id, station_name, manager_phone") \
            .eq("train_number", train_number) \
            .eq("direction", direction) \
            .order("sequence_order", desc=False) \
            .execute()
        return response.data

    async def get_station_manager(self, station_id: str):
        response = await self.db.table("train_route_station") \
            .select("station_name, manager_phone") \
            .eq("station_id", station_id) \
            .execute()
        return response.data[0] if response.data else None
