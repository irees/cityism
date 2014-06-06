python -m cityism.misc.housing_decades \
  --output=$1 \
  --lat=$2 \
  --lon=$3 \
  --sql=$HOME/src/cityism/misc/housing_decades.sql \
  --xml=$HOME/src/cityism/misc/housing_decades.xml \
  --keys=density_0000_1939 \
  --labels="   pre - 1939" \
  --keys=density_1940_1950 \
  --labels="1940 - 1950" \
  --keys=density_1950_1960 \
  --labels="1950 - 1960" \
  --keys=density_1960_1970 \
  --labels="1960 - 1970" \
  --keys=density_1970_1980 \
  --labels="1970 - 1980" \
  --keys=density_1980_1990 \
  --labels="1980 - 1990" \
  --keys=density_1990_2000 \
  --labels="1990 - 2000" \
  --keys=density_2000_2010 \
  --labels="2000 - 2010" \
  --cmin=25 \
  --cmax=800 \
  --radius=60000 \
  --nx=1024 \
  --ny=1024 
