-- seed.sql: sample listings across Vancouver for trying out the app.
-- WARNING: deletes every row in listings before inserting.
-- Run after schema.sql:  psql listings -f seed.sql

TRUNCATE listings RESTART IDENTITY;

INSERT INTO listings (address, description, location, bedrooms, washrooms, sqft, price, property_type) VALUES
-- Downtown / central
('1050 Robson St',        'Downtown condo with city views and gym access',        ST_MakePoint(-123.1240, 49.2845), 1, 1.0,  620,  699000, 'condo'),
('1180 Mainland St',      'Yaletown loft with exposed brick and high ceilings',   ST_MakePoint(-123.1210, 49.2750), 1, 1.5,  780,  849000, 'loft'),
('1560 W Hastings St',    'Coal Harbour waterfront suite with mountain views',    ST_MakePoint(-123.1270, 49.2900), 2, 2.0, 1150, 1895000, 'condo'),
('1720 Davie St',         'West End apartment steps from English Bay',            ST_MakePoint(-123.1370, 49.2880), 1, 1.0,  580,  619000, 'condo'),
('210 Water St',          'Gastown heritage loft, open layout',                   ST_MakePoint(-123.1080, 49.2840), 1, 1.0,  690,  729000, 'loft'),
('480 E Pender St',       'Chinatown studio near transit, renovated kitchen',     ST_MakePoint(-123.1000, 49.2795), 0, 1.0,  420,  449000, 'condo'),
('720 Union St',          'Strathcona character house with garden',               ST_MakePoint(-123.0880, 49.2770), 3, 2.0, 1680, 1749000, 'house'),
-- West side
('2250 Main St',          'Mount Pleasant 2-bed near breweries and SkyTrain',     ST_MakePoint(-123.1010, 49.2630), 2, 1.0,  860,  829000, 'condo'),
('1290 W 10th Ave',       'Fairview condo close to hospitals and shops',          ST_MakePoint(-123.1300, 49.2640), 2, 2.0,  940,  989000, 'condo'),
('2240 W 4th Ave',        'Kitsilano townhouse near the beach',                   ST_MakePoint(-123.1590, 49.2680), 3, 2.5, 1450, 1799000, 'townhouse'),
('4410 W 8th Ave',        'Point Grey family home near UBC',                      ST_MakePoint(-123.2000, 49.2680), 4, 3.0, 2700, 4250000, 'house'),
('3650 Dunbar St',        'Dunbar bungalow with large backyard',                  ST_MakePoint(-123.1850, 49.2480), 3, 2.0, 1900, 2890000, 'house'),
('2150 W 41st Ave',       'Kerrisdale apartment near shops and schools',          ST_MakePoint(-123.1560, 49.2340), 2, 2.0, 1050, 1189000, 'condo'),
('1450 Matthews Ave',     'Shaughnessy estate home with garden and garage',       ST_MakePoint(-123.1400, 49.2480), 5, 4.5, 4200, 7950000, 'house'),
('5720 Cambie St',        'Oakridge condo, new building near transit',            ST_MakePoint(-123.1170, 49.2270), 2, 2.0,  880, 1099000, 'condo'),
('8320 Granville St',     'Marpole townhouse near the airport and river',         ST_MakePoint(-123.1300, 49.2100), 3, 2.5, 1320, 1299000, 'townhouse'),
('4680 Cambie St',        'South Cambie suite near Queen Elizabeth Park',         ST_MakePoint(-123.1200, 49.2450), 1, 1.0,  640,  679000, 'condo'),
-- East side
('4490 Main St',          'Riley Park duplex with renovated kitchen',             ST_MakePoint(-123.1010, 49.2450), 3, 2.0, 1500, 1649000, 'duplex'),
('4520 Fraser St',        'Kensington character home, bright and quiet',          ST_MakePoint(-123.0900, 49.2450), 4, 2.5, 2100, 1989000, 'house'),
('6250 Fraser St',        'Sunset family home with basement suite',               ST_MakePoint(-123.0900, 49.2200), 5, 3.0, 2600, 2149000, 'house'),
('6380 Kerr St',          'Killarney townhouse near parks and community centre',  ST_MakePoint(-123.0400, 49.2200), 3, 2.5, 1400, 1149000, 'townhouse'),
('3180 E 22nd Ave',       'Renfrew house near SkyTrain, large lot',               ST_MakePoint(-123.0400, 49.2550), 4, 2.0, 1950, 1899000, 'house'),
('2550 E Hastings St',    'Hastings-Sunrise condo near cafes and PNE',            ST_MakePoint(-123.0450, 49.2810), 2, 1.0,  820,  739000, 'condo'),
('1720 Commercial Dr',    'Grandview loft above shops, walkable neighbourhood',   ST_MakePoint(-123.0700, 49.2700), 1, 1.0,  700,  649000, 'loft'),
('6150 Victoria Dr',      'Victoria-Fraserview home with mountain views',         ST_MakePoint(-123.0650, 49.2200), 4, 3.0, 2300, 2089000, 'house');