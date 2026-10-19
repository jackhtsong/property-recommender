-- Extensions
CREATE EXTENSION IF NOT EXISTS postgis;

-- Tables
CREATE TABLE listings (
  id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  address      TEXT NOT NULL,
  description  TEXT,
  location     GEOGRAPHY(Point, 4326) NOT NULL,
  bedrooms     SMALLINT CHECK (bedrooms >= 0),
  washrooms    NUMERIC(3,1) CHECK (washrooms >= 0),
  sqft         INTEGER CHECK (sqft > 0),
  price          NUMERIC(12,2) NOT NULL CHECK (price > 0),
  property_type  TEXT NOT NULL CHECK (property_type IN ('condo','townhouse','house','duplex','loft'))
);

-- Indexes
CREATE INDEX listings_location_idx ON listings USING GIST (location);