# Software Requirements Specification (SRS)
## Smart Train Sanitation System (Backend & IoT Gateway)

### 1. System Overview
The Smart Train Sanitation System is an automated, event-driven IoT solution designed to manage real-time sanitation alerts originating from passenger train coaches. 

A central **Raspberry Pi Gateway** onboard the train tracks station progress and dispatches coach sanitation requests to a serverless **FastAPI API hosted on Vercel**. The backend evaluates personnel assignments stored in a **Supabase PostgreSQL database**, automatically routing the alert via SMS to either:
1. Assigned **On-Board Housekeeping Service (OBHS)** staff members.
2. The **Station Manager** at the upcoming station as a fallback mechanism.

---

### 2. Functional Requirements

#### 2.1 Authentication & Security (BR-01)
* **REQ-SEC-1:** All backend API endpoints must enforce mandatory API key verification using a custom HTTP header (`x-api-key`).
* **REQ-SEC-2:** Unauthenticated requests missing or presenting an invalid key must be rejected immediately with an `HTTP 401 Unauthorized` status code.
* **REQ-SEC-3:** Database connections from Vercel to Supabase must utilize the `service_role` key to prevent direct public access to sensitive data.
* **REQ-SEC-4:** Sensitive details (such as phone numbers of station managers and staff) must be excluded from public API responses.

#### 2.2 Trip Initialization & Dynamic Caching (BR-02)
* **REQ-INIT-1:** The backend must expose an initialization endpoint (`GET /api/init-trip`) taking a `train_number` query parameter.
* **REQ-INIT-2:** The system must locate the active or upcoming trip for the requested train set (`status IN ('ACTIVE', 'SCHEDULED')`).
* **REQ-INIT-3:** The system must query the sequence of route stations corresponding to the trip's direction (`UP` or `DOWN`), sorted in ascending order of `sequence_order`.
* **REQ-INIT-4:** The response must return the `trip_number`, `direction`, and ordered array of stations (`sequence_order`, `station_id`, `station_name`) to be cached in the Raspberry Pi's memory.

#### 2.3 Alert Routing & SMS Dispatch (BR-03)
* **REQ-ALT-1:** The backend must expose an alert endpoint (`POST /api/alert`) accepting train metadata, coach identifier, last station passed, upcoming station, and timestamp.
* **REQ-ALT-2 (Primary Routing):** The system must query active `obhs_staff` assigned to the specific `trip_number` and matching `coach_number` (or `coach_number = 'ALL'`).
* **REQ-ALT-3 (Fallback Routing):** If no active OBHS personnel are found for the coach, the system must fetch the `manager_phone` associated with the `next_station_id` from `train_route_stations`.
* **REQ-ALT-4:** The backend must format and dispatch an asynchronous SMS via the Fast2SMS API (`https://www.fast2sms.com/dev/bulkV2`).
* **REQ-ALT-5:** All alert events, assigned targets, phone numbers used, and SMS delivery statuses (`DELIVERED` or `FAILED`) must be logged into the `alert_logs` table for auditing.

---

### 3. Database Requirements & Schema

The database must be built on PostgreSQL (Supabase) with the  relational structures specified in ER.mmd file:


### 4. Interface Requirements & API Specifications

#### 4.1 Interface Specification: Init Trip API
* **Path:** `GET /api/init-trip`
* **Headers:** `x-api-key: <API_SECRET_KEY>`
* **Parameters:** `train_number` (string)
* **Response Schema (200 OK):**

```json
{
  "success": true,
  "train_number": "12601",
  "trip_number": "TRP-2026-8849",
  "direction": "UP",
  "stations": [
    {
      "sequence_order": 1,
      "station_id": "MAS",
      "station_name": "Chennai Central"
    },
    {
      "sequence_order": 2,
      "station_id": "KPD",
      "station_name": "Katpadi Jn"
    }
  ]
}
```
### 4.2 Interface Specification: Alert Dispatch API
* **Path:** POST /api/alert
* **Headers:** x-api-key: <API_SECRET_KEY>

**Request Schema Body:**

```json
{
  "train_number": "12601",
  "trip_number": "TRP-2026-8849",
  "coach_number": "A1",
  "last_station_id": "AJJ",
  "next_station_id": "KPD",
  "time": "2026-07-30 18:30:00"
}
```
**Response Schema (200 OK):**

```json
{
  "success": true,
  "dispatched_to": "Station Manager (Katpadi Jn)",
  "sms_response": {
    "return": true,
    "request_id": "v2_req_992184",
    "message": ["SMS sent successfully."]
  }
}
```

### 5. Non-Functional Requirements
#### 5.1 Performance & Latency (NFR-01)
* **P-01:** API execution latency on Vercel must be under 500 milliseconds (excluding external Fast2SMS network time).
* **P-02:** DB queries must utilize indexes on train_number, trip_number, and direction to keep lookup times under 20 milliseconds.

#### 5.2 Reliability & Availability (NFR-02)
* **R-01:** The serverless architecture must achieve 99.9% uptime.
* **R-02:** Failure of the primary OBHS lookup must gracefully fall back to the station manager query without throwing application errors.

#### 5.3 Maintainability & Technology Stack (NFR-03)
* **M-01:** Framework: Python 3.10+ using FastAPI and Pydantic v2.
* **M-02:** Deployment Environment: Vercel Serverless Functions (api/index.py configured via vercel.json).
* **M-03:** Database Client: Supabase Client SDK using asynchronous I/O (httpx) for external HTTP API calls.