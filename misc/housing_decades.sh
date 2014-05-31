# sacramento 38.578518 -121.495741
# seattle 47.605879 -122.335799
# atlanta 33.750773 -84.389898
# denver 39.739296 -104.983686
# bayarea 37.795598 -122.394180
# houston 29.758294 -95.363741
# nyc 40.713666 -74.006757
# dallas 32.780569 -96.799511
# phoenix 33.448240 -112.067296
# boston 42.360498 -71.057385
# la 34.048808 -118.251873
# sandiego 32.715710 -117.162873
# chicago 41.875625 -87.627675
# dc 38.900134 -77.036585
# philadelphia 39.940065 -75.166295
python housing_decades.py \
  --cmin=25 \
  --cmax=800 \
  --radius=100000 \
  --output=$1 \
  --lat=$2 \
  --lon=$3 \
  --sql=housing_decades.sql \
  --xml=housing_decades.xml \
  --keys=density_0000_1939 \
  --keys=density_1940_1950 \
  --keys=density_1950_1960 \
  --keys=density_1960_1970 \
  --keys=density_1970_1980 \
  --keys=density_1980_1990 \
  --keys=density_1990_2000 \
  --keys=density_2000_2010 