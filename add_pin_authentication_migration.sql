-- Migration: Add PIN authentication fields to users table
-- This enables device-specific PIN authentication for mobile users

ALTER TABLE users
ADD COLUMN pin_hash VARCHAR(255),
ADD COLUMN pin_device_id VARCHAR(255),
ADD COLUMN pin_failed_attempts INTEGER DEFAULT 0,
ADD COLUMN pin_locked_until TIMESTAMP,
ADD COLUMN pin_created_at TIMESTAMP;

-- Create index for device_id lookups
CREATE INDEX idx_users_pin_device_id ON users(pin_device_id);

-- Add comment for documentation
COMMENT ON COLUMN users.pin_hash IS 'Hashed PIN for quick device authentication (bcrypt)';
COMMENT ON COLUMN users.pin_device_id IS 'Unique device identifier where PIN is configured';
COMMENT ON COLUMN users.pin_failed_attempts IS 'Counter for failed PIN attempts';
COMMENT ON COLUMN users.pin_locked_until IS 'Timestamp until PIN authentication is locked';
COMMENT ON COLUMN users.pin_created_at IS 'When the PIN was configured';


