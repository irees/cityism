(SELECT 
  tract_2012.gid AS gid,
	tract_2012.geom AS geom,  
	tract_2012.geoid, 
	tract_2012.aland, 
	acs_b25034.b25034_003/tract_2012.aland * 1e6 as density_2000_2010,
	acs_b25034.b25034_004/tract_2012.aland * 1e6 as density_1990_2000,
	acs_b25034.b25034_005/tract_2012.aland * 1e6 as density_1980_1990,
	acs_b25034.b25034_006/tract_2012.aland * 1e6 as density_1970_1980,
	acs_b25034.b25034_007/tract_2012.aland * 1e6 as density_1960_1970,
	acs_b25034.b25034_008/tract_2012.aland * 1e6 as density_1950_1960,
	acs_b25034.b25034_009/tract_2012.aland * 1e6 as density_1940_1950,
	acs_b25034.b25034_010/tract_2012.aland * 1e6 as density_0000_1939
FROM 
	tract_2012 
INNER JOIN 
	acs_b25034 on acs_b25034.geoid = tract_2012.geoid 
WHERE 
	tract_2012.aland > 0
) as layer