-- Calculate housing unit densities for the various columns in ACS B25034.
(SELECT 
  tract.gid AS gid,
	tract.geom AS geom,  
	tract.geoid, 
	tract.aland, 
	acs_b25034.b25034_002/tract.aland * 1e6 as density_2010_2012,
	acs_b25034.b25034_003/tract.aland * 1e6 as density_2000_2010,
	acs_b25034.b25034_004/tract.aland * 1e6 as density_1990_2000,
	acs_b25034.b25034_005/tract.aland * 1e6 as density_1980_1990,
	acs_b25034.b25034_006/tract.aland * 1e6 as density_1970_1980,
	acs_b25034.b25034_007/tract.aland * 1e6 as density_1960_1970,
	acs_b25034.b25034_008/tract.aland * 1e6 as density_1950_1960,
	acs_b25034.b25034_009/tract.aland * 1e6 as density_1940_1950,
	acs_b25034.b25034_010/tract.aland * 1e6 as density_0000_1939
FROM 
	tract_2012 as tract
INNER JOIN 
	acs_b25034 on acs_b25034.geoid = tract.geoid 
WHERE 
	tract.aland > 0
) as layer