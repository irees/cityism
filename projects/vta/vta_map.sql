-- Export census tracts as GeoJSON, including various properties. Use with ogr2ogr.
SELECT
  tract.geoid AS geoid,
  tract.aland AS aland,
  tract.countyfp as countyfp,
  ST_Simplify(tract.geom, 0.001) as geom,
  acs_b01001.b01001_001 as pop,
  acs_b01001.b01001_001 / tract.aland * 1e6 AS density,
  acs_b08301.b08301_010 / acs_b08301.b08301_001::float AS transit_pct,
  acs_b19013.b19013_001 as income
FROM 
  tract_2012 as tract
INNER JOIN
  acs_b08301 ON acs_b08301.geoid = tract.geoid
INNER JOIN
  acs_b01001 ON acs_b01001.geoid = tract.geoid
INNER JOIN
  acs_b19013 ON acs_b19013.geoid = tract.geoid
WHERE
  tract.statefp = '06' AND
  tract.countyfp in ('001', '013', '075', '081', '055', '041', '085', '087', '095', '097') AND
  acs_b08301.b08301_001 > 0;
