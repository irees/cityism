SELECT
  tract_2012.geoid AS geoid,
  tract_2012.aland AS aland,
  tract_2012.countyfp as countyfp,
  -- ST_Simplify(tract_2012.geom, 0.001) as geom,
  acs_b01001.b01001_001 as pop,
  acs_b01001.b01001_001 / tract_2012.aland * 1e6 AS density,
  acs_b08301.b08301_010 / acs_b08301.b08301_001::float AS transit_pct,
  acs_b19013.b19013_001 as income
FROM 
  tract_2012
INNER JOIN
  acs_b08301 ON acs_b08301.geoid = tract_2012.geoid
INNER JOIN
  acs_b01001 ON acs_b01001.geoid = tract_2012.geoid
INNER JOIN
  acs_b19013 ON acs_b19013.geoid = tract_2012.geoid
WHERE
  tract_2012.statefp = '06' AND
  tract_2012.countyfp in ('001', '013', '075', '081', '055', '041', '085', '087', '095', '097') AND
  acs_b08301.b08301_001 > 0;
