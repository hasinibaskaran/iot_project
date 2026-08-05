from supabase import AsyncClient

class DeviceRepository:
    def __init__(self, db: AsyncClient):
        self.db = db

    async def get_device_by_train(self, train_number: str):
        response = await self.db.table("gateway_device") \
            .select("device_id") \
            .eq("train_number", train_number) \
            .execute()
        return response.data[0]["device_id"] if response.data else None
