hi this is a project that will recommend you a property :D

run in root folder: 'psql listings -f db/schema.sql' and then 'psql listings -f db/seed.sql'
use ur own gemini api!

stack:
- postgres: database
- postgis: spatial queries
- python (fastapi): runs queries, calls gemini + google
- gemini: parse search text into filters, write explanations
- google: geocoding (backend), maps display (frontend)
- js: ui