import os
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

# Set up test environment variables before importing app
os.environ["API_SECRET_KEY"] = "secret-test-key-2026"
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_KEY"] = "mock-key"
# We leave FAST2SMS_API_KEY unset to trigger mock mode in test runs

from api.main import app
from api.database import get_supabase

client = TestClient(app)

class MockSupabaseClient:
    """
    A lightweight, chainable mock for Supabase's AsyncClient.
    Enables simulation of selective table queries.
    """
    def __init__(self, mock_data=None):
        self.mock_data = mock_data or {}
        self.current_table = None

    def table(self, table_name):
        self.current_table = table_name
        return self

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def or_(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def insert(self, *args, **kwargs):
        return self

    async def execute(self):
        result = MagicMock()
        result.data = self.mock_data.get(self.current_table, [])
        return result


class TestSmartSanitationAPI(unittest.TestCase):

    def test_authentication_missing_key(self):
        """REQ-SEC-2: Reject requests missing the custom x-api-key header with 401"""
        response = client.get("/api/init-trip?train_number=12601")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid or missing API Key", response.json()["detail"])

    def test_authentication_invalid_key(self):
        """REQ-SEC-2: Reject requests presenting an invalid x-api-key header with 401"""
        response = client.get(
            "/api/init-trip?train_number=12601",
            headers={"x-api-key": "wrong-secret-key"}
        )
        self.assertEqual(response.status_code, 401)

    def test_init_trip_success(self):
        """REQ-INIT-1 to REQ-INIT-4: Successfully load trip sequence and exclude manager phone"""
        # Set up mock database queries
        mock_data = {
            "trip": [
                {
                    "trip_number": "TRP-2026-8849",
                    "train_number": "12601",
                    "direction": "UP",
                    "status": "ACTIVE",
                    "start_time": "2026-07-30T08:00:00+00:00"
                }
            ],
            "train_route_station": [
                {
                    "sequence_order": 1,
                    "station_id": "MAS",
                    "station_name": "Chennai Central",
                    "manager_phone": "+919999900001" # sensitive
                },
                {
                    "sequence_order": 2,
                    "station_id": "AJJ",
                    "station_name": "Arakkonam Jn",
                    "manager_phone": "+919999900002" # sensitive
                }
            ]
        }
        
        mock_client = MockSupabaseClient(mock_data)
        async def override_get_db():
            return mock_client
        
        app.dependency_overrides[get_supabase] = override_get_db
        
        try:
            response = client.get(
                "/api/init-trip?train_number=12601",
                headers={"x-api-key": "secret-test-key-2026"}
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["train_number"], "12601")
            self.assertEqual(data["trip_number"], "TRP-2026-8849")
            self.assertEqual(data["direction"], "UP")
            
            # REQ-SEC-4: Sensitive details (phone numbers) must be excluded from public API responses
            self.assertEqual(len(data["stations"]), 2)
            self.assertEqual(data["stations"][0]["station_id"], "MAS")
            self.assertEqual(data["stations"][0]["station_name"], "Chennai Central")
            self.assertNotIn("manager_phone", data["stations"][0])
            self.assertNotIn("phone_number", data["stations"][0])
        finally:
            app.dependency_overrides.clear()

    @patch("api.services.sms_service.SmsService.send_sms")
    def test_alert_dispatch_primary_routing(self, mock_send_sms):
        """REQ-ALT-2: Primary Routing matches active OBHS staff members"""
        mock_data = {
            "trip": [{"direction": "UP", "train_number": "12601"}],
            "train": [{"train_name": "Mangalore Express"}],
            "obhs_staff": [
                {"name": "John Doe", "phone_number": "+918888888888"},
                {"name": "Jane Smith", "phone_number": "+917777777777"}
            ],
            "gateway_device": [{"device_id": "RPI-GATEWAY-12601"}]
        }
        
        mock_client = MockSupabaseClient(mock_data)
        async def override_get_db():
            return mock_client
        
        app.dependency_overrides[get_supabase] = override_get_db
        
        payload = {
            "train_number": "12601",
            "trip_number": "TRP-2026-8849",
            "coach_number": "A1",
            "last_station_id": "AJJ",
            "next_station_id": "KPD",
            "time": "2026-07-30 18:30:00"
        }
        
        mock_send_sms.return_value = {
            "return": True,
            "request_id": "mock_req_12345",
            "message": ["SMS mock sent successfully."]
        }
        
        try:
            response = client.post(
                "/api/alert",
                json=payload,
                headers={"x-api-key": "secret-test-key-2026"}
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
            self.assertIn("John Doe", data["dispatched_to"])
            self.assertIn("Jane Smith", data["dispatched_to"])
            self.assertTrue(data["sms_response"]["return"])
            
            # Verify the Option A message format is sent with the train name
            mock_send_sms.assert_called_once_with(
                "Urgent: Sanitation requested on Train 12601 (Mangalore Express), Coach A1. Please attend immediately. [Alert Time: 2026-07-30 18:30:00]",
                "+918888888888,+917777777777"
            )
        finally:
            app.dependency_overrides.clear()

    @patch("api.services.sms_service.SmsService.send_sms")
    def test_alert_dispatch_fallback_routing(self, mock_send_sms):
        """REQ-ALT-3: Fallback Routing triggers Station Manager lookup when no OBHS staff are active"""
        mock_data = {
            "trip": [{"direction": "UP", "train_number": "12601"}],
            "train": [{"train_name": "Mangalore Express"}],
            "obhs_staff": [], # No staff
            "train_route_station": [{"station_name": "Katpadi Jn", "manager_phone": "+919999900003"}],
            "gateway_device": [{"device_id": "RPI-GATEWAY-12601"}]
        }
        
        mock_client = MockSupabaseClient(mock_data)
        async def override_get_db():
            return mock_client
        
        app.dependency_overrides[get_supabase] = override_get_db
        
        payload = {
            "train_number": "12601",
            "trip_number": "TRP-2026-8849",
            "coach_number": "B1",
            "last_station_id": "AJJ",
            "next_station_id": "KPD",
            "time": "2026-07-30 18:30:00"
        }
        
        mock_send_sms.return_value = {
            "return": True,
            "request_id": "mock_req_12345",
            "message": ["SMS mock sent successfully."]
        }
        
        try:
            response = client.post(
                "/api/alert",
                json=payload,
                headers={"x-api-key": "secret-test-key-2026"}
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["dispatched_to"], "Station Manager (Katpadi Jn)")
            self.assertTrue(data["sms_response"]["return"])
            
            # Verify the Option Y message format is sent with the train name
            mock_send_sms.assert_called_once_with(
                "Sanitation Alert: Train 12601 (Mangalore Express) Coach B1 requires sanitation. OBHS team offline. Please arrange station cleanup at Katpadi Jn.",
                "+919999900003"
            )
        finally:
            app.dependency_overrides.clear()

    def test_validation_error(self):
        """Verify that Pydantic validation errors return structured 422 error response"""
        payload = {
            "train_number": "12601"
        }
        response = client.post(
            "/api/alert",
            json=payload,
            headers={"x-api-key": "secret-test-key-2026"}
        )
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["message"], "Validation error")
        self.assertTrue(isinstance(data["detail"], list))
        self.assertTrue(len(data["detail"]) > 0)

    def test_generic_exception_handler(self):
        """Verify that unexpected exceptions return a structured 500 error response"""
        mock_client = MockSupabaseClient({})
        mock_client.execute = AsyncMock(side_effect=RuntimeError("Database connection failed"))
        
        async def override_get_db():
            return mock_client
        
        app.dependency_overrides[get_supabase] = override_get_db
        try:
            # Use a test client that doesn't raise exceptions to test our custom error handler
            err_client = TestClient(app, raise_server_exceptions=False)
            response = err_client.get(
                "/api/init-trip?train_number=12601",
                headers={"x-api-key": "secret-test-key-2026"}
            )
            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertFalse(data["success"])
            self.assertEqual(data["detail"], "Internal Server Error")
        finally:
            app.dependency_overrides.clear()

if __name__ == "__main__":
    unittest.main()
