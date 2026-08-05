-- Enable UUID generation extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. TRAIN Table
CREATE TABLE train (
    train_number VARCHAR(50) PRIMARY KEY,
    train_name VARCHAR(100) NOT NULL
);

-- 2. TRIP Table
CREATE TABLE trip (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_number VARCHAR(100) UNIQUE NOT NULL,
    train_number VARCHAR(50) REFERENCES train(train_number) ON DELETE CASCADE,
    direction VARCHAR(10) CHECK (direction IN ('UP', 'DOWN')) NOT NULL,
    status VARCHAR(20) CHECK (status IN ('SCHEDULED', 'ACTIVE', 'COMPLETED')) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Indexes on TRIP for lookup speed
CREATE INDEX idx_trip_train_status ON trip(train_number, status);
CREATE INDEX idx_trip_trip_number ON trip(trip_number);

-- 3. TRAIN_ROUTE_STATION Table
CREATE TABLE train_route_station (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    train_number VARCHAR(50) REFERENCES train(train_number) ON DELETE CASCADE,
    direction VARCHAR(10) CHECK (direction IN ('UP', 'DOWN')) NOT NULL,
    sequence_order INTEGER NOT NULL,
    station_id VARCHAR(50) NOT NULL,
    station_name VARCHAR(100) NOT NULL,
    manager_phone VARCHAR(20) NOT NULL,
    UNIQUE(train_number, direction, sequence_order)
);

-- Indexes on TRAIN_ROUTE_STATION for fast route/manager lookups
CREATE INDEX idx_route_train_dir_seq ON train_route_station(train_number, direction, sequence_order);
CREATE INDEX idx_route_train_station ON train_route_station(train_number, station_id);

-- 4. GATEWAY_DEVICE Table
CREATE TABLE gateway_device (
    device_id VARCHAR(100) PRIMARY KEY,
    train_number VARCHAR(50) REFERENCES train(train_number) ON DELETE SET NULL,
    status VARCHAR(20) CHECK (status IN ('ONLINE', 'OFFLINE')) NOT NULL DEFAULT 'ONLINE'
);

-- 5. OBHS_STAFF Table
CREATE TABLE obhs_staff (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_number VARCHAR(100) REFERENCES trip(trip_number) ON DELETE CASCADE,
    coach_number VARCHAR(20) NOT NULL, -- e.g., 'A1', 'B1', or 'ALL'
    name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);

-- Indexes on OBHS_STAFF for rapid matching queries
CREATE INDEX idx_obhs_trip_coach ON obhs_staff(trip_number, coach_number) WHERE is_active = TRUE;

-- 6. ALERT_LOG Table
CREATE TABLE alert_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(100) REFERENCES gateway_device(device_id) ON DELETE SET NULL,
    train_number VARCHAR(50) NOT NULL,
    trip_number VARCHAR(100) NOT NULL,
    coach_number VARCHAR(20) NOT NULL,
    last_station_id VARCHAR(50) NOT NULL,
    next_station_id VARCHAR(50) NOT NULL,
    dispatched_to_type VARCHAR(20) CHECK (dispatched_to_type IN ('OBHS_STAFF', 'STATION_MANAGER')) NOT NULL,
    recipient_phone VARCHAR(20) NOT NULL,
    sms_status VARCHAR(20) CHECK (sms_status IN ('DELIVERED', 'FAILED')) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- =========================================================================
-- SEED DATA FOR TESTING
-- =========================================================================

-- Insert Train
INSERT INTO train (train_number, train_name) 
VALUES ('12601', 'Mangalore Express')
ON CONFLICT (train_number) DO NOTHING;

-- Insert Trip
INSERT INTO trip (trip_number, train_number, direction, status, start_time)
VALUES ('TRP-2026-8849', '12601', 'UP', 'ACTIVE', '2026-07-30 08:00:00+00')
ON CONFLICT (trip_number) DO NOTHING;

-- Insert Route Stations
INSERT INTO train_route_station (train_number, direction, sequence_order, station_id, station_name, manager_phone)
VALUES 
('12601', 'UP', 1, 'MAS', 'Chennai Central', '+918489422354'),
('12601', 'UP', 2, 'AJJ', 'Arakkonam Jn', '+918489422354'),
('12601', 'UP', 3, 'KPD', 'Katpadi Jn', '+918489422354'),
('12601', 'UP', 4, 'JTJ', 'Jolarpettai Jn', '+918489422354')
ON CONFLICT (train_number, direction, sequence_order) DO NOTHING;

-- Insert Gateway Device
INSERT INTO gateway_device (device_id, train_number, status)
VALUES ('RPI-GATEWAY-12601', '12601', 'ONLINE')
ON CONFLICT (device_id) DO NOTHING;

-- Insert OBHS Staff
INSERT INTO obhs_staff (trip_number, coach_number, name, phone_number, is_active)
VALUES 
('TRP-2026-8849', 'A1', 'John Doe (A1 Staff)', '+918489422354', true),

('TRP-2026-8849', 'A2', 'Jane Smith (All Coach)', '+918489422354', true)
ON CONFLICT (id) DO NOTHING;
