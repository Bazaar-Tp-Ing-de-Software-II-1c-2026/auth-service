-- Migration to add shipping address fields to users table
-- Run this migration on your database

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS shipping_address VARCHAR(200),
ADD COLUMN IF NOT EXISTS shipping_city VARCHAR(100),
ADD COLUMN IF NOT EXISTS shipping_state VARCHAR(100),
ADD COLUMN IF NOT EXISTS shipping_postal_code VARCHAR(20),
ADD COLUMN IF NOT EXISTS shipping_country VARCHAR(100),
ADD COLUMN IF NOT EXISTS shipping_phone VARCHAR(20);

-- Add indexes for commonly queried fields (optional, for performance)
CREATE INDEX IF NOT EXISTS idx_users_shipping_country ON users(shipping_country);
CREATE INDEX IF NOT EXISTS idx_users_shipping_city ON users(shipping_city);


