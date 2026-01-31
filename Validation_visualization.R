setwd("~/Desktop/NPS/Fireseverity/Validation")

library(tidyverse)
library(scico)
library(sf)

df = st_read("validation_metrics.gpkg")

ggplot() + theme_bw() +
  geom_point(data = df, aes(x = fire_days, y = boundary_mean_dnbr)) +
  geom_line(data = df, aes(x = fire_days, y = boundary_mean_dnbr, group = fire_name))

# area overlap

df_filtered = df %>%
  select(fire_name, fire_days, geom) %>%
  st_make_valid()

calfire = st_read('Validation_Fire_Perimeters_2015_2024.shp') %>%
  select(FIRE_NAME, geometry) %>%
  rename(fire_name = FIRE_NAME) %>%
  st_make_valid() %>%
  st_transform(crs = st_crs(df_filtered))

# Calculate overlap for each fire/fire_days combination
overlap_results = map_dfr(1:nrow(df_filtered), function(i) {
  row = df_filtered[i, ]
  cal_poly = calfire %>% filter(fire_name == row$fire_name)
  
  if (nrow(cal_poly) == 0) return(NULL)
  
  intersection = st_intersection(row, cal_poly)
  
  # Handle case where there's no intersection
  if (nrow(intersection) == 0 || all(st_is_empty(intersection))) {
    return(data.frame(
      fire_name = row$fire_name,
      fire_days = row$fire_days,
      percent_overlap = 0
    ))
  }
  
  # Sum all intersection areas (in case of multipart geometries)
  intersection_area = sum(st_area(intersection))
  calfire_area = sum(st_area(cal_poly))
  
  # Cap at 100% (intersection can't exceed calfire area)
  pct = min(100, as.numeric(intersection_area / calfire_area * 100))
  
  data.frame(
    fire_name = row$fire_name,
    fire_days = row$fire_days,
    percent_overlap = pct
  )
}) %>%
  crossing(metric = c("dnbr", "rdnbr"))

overlap_results 
  