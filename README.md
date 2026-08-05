# Smart Train Sanitation System Backend

CleanTrack is an automated, event-driven IoT backend designed to manage real-time sanitation alerts originating from passenger train coaches. 

This repository implements the API hosted on Vercel, utilizing a Supabase PostgreSQL database to check assignments and route alerts to either active On-Board Housekeeping Service (OBHS) staff members or the next station manager as a fallback.

---

## 🛠️ Tech Stack
* **Runtime:** Python 3.12+ (Managed via **uv**)
* **Framework:** FastAPI & Pydantic v2
* **Database:** Supabase (PostgreSQL) with async client sdk
* **SMS Integration:** Fast2SMS API
* **Deployment:** Vercel Serverless Functions

---

## 🚀 Quick Start with `uv`

This project uses [uv](https://github.com/astral-sh/uv), a fast Python package installer and resolver.

### 1. Installation & Environment Setup
Initialize the environment and synchronize all dependencies (which automatically reads `pyproject.toml` and locks to `uv.lock`):
```bash
# Sync/create virtual environment and install packages
uv sync
```

### 2. Configuration (`.env`)
Create a `.env` file in the root of the project with the following configuration details:
```env
SUPABASE_URL="https://your-supabase-url.supabase.co"
SUPABASE_KEY="your-supabase-service-role-key"
API_SECRET_KEY="your-header-x-api-key-value"
FAST2SMS_API_KEY="your-fast2sms-api-key-optional"
```
*Note: If `FAST2SMS_API_KEY` is not set, the backend runs in **mock sandbox mode**, simulating successful SMS deliveries in console logs.*

### 3. Run Development Server
Start the local FastAPI development server using the configured uv shortcut command:
```bash
uv run app
```
Open [http://localhost:3000](http://localhost:3000) to access the **Interactive Control Panel & Testing Bench**!

### 4. Run Automated Tests
Execute the self-contained mock tests:
```bash
uv run python -m unittest tests/test_api.py
```

---

## 💾 Database Setup

Apply the SQL DDL schema and test seed data located in [Design/schema.sql](Design/schema.sql) directly in your Supabase SQL Editor.

The schema establishes the following relations:
* **`train` / `trip`**: Tracks trains and their active or scheduled trips.
* **`train_route_station`**: Records station order sequence and station managers' contact phone numbers.
* **`gateway_device`**: Pairs onboard Raspberry Pi gateways with their respective train.
* **`obhs_staff`**: Defines service staff assignments for specific coaches and trips.
* **`alert_log`**: Audits triggered alerts, targets, contacted numbers, and SMS delivery statuses.

---

## 📡 API Specifications

All endpoints require the API Key authentication header:
`x-api-key: <API_SECRET_KEY>`

### 1. Initialize Trip
* **Endpoint:** `GET /api/init-trip`
* **Query Parameters:** `train_number`
* **Response:** Returns the active trip number, direction, and ordered list of sequence stations (omitting manager contacts for security compliance).

### 2. Alert Dispatch
* **Endpoint:** `POST /api/alert`
* **Payload:**
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
* **Response:** Dispatches the alert SMS. Returns success and confirmation of the routing target.

---

## 🛡️ Exception & Error Handling

The application implements global exception handling to capture validation failures, HTTP exceptions, and unexpected server errors, ensuring clean and uniform JSON responses:

* **HTTP Exceptions (e.g., `401 Unauthorized`, `404 Not Found`)**:
  ```json
  {
    "success": false,
    "detail": "Error details/message"
  }
  ```
* **Validation Errors (`422 Unprocessable Entity`)**:
  Raised when input parameters or JSON payloads fail validation:
  ```json
  {
    "success": false,
    "detail": [
      {
        "type": "missing",
        "loc": ["body", "trip_number"],
        "msg": "Field required",
        "input": {}
      }
    ],
    "message": "Validation error"
  }
  ```
* **Unexpected Errors (`500 Internal Server Error`)**:
  Generic server failures are intercepted to prevent sensitive stack trace disclosure. The details are logged to the console, and a sanitized response is sent to the client:
  ```json
  {
    "success": false,
    "detail": "Internal Server Error"
  }
  ```
