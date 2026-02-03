setwd("~/Desktop/NPS/Fireseverity/Validation")

library(tidyverse)
library(scico)
library(sf)

df = st_read("validation_metrics.gpkg")

ggplot() + theme_bw() + facet_wrap(~metric) +
  geom_point(data = df, aes(x = fire_days, y = filtered_mean)) +
  geom_line(data = df, aes(x = fire_days, y = filtered_mean, group = fire_name))

# area overlap

df_filtered = df %>%
  select(fire_name, fire_days, metric, geom) %>%
  st_make_valid()

calfire = st_read('Validation_Fire_Perimeters_2015_2024.shp') %>%
  select(FIRE_NAME, geometry) %>%
  rename(fire_name = FIRE_NAME) %>%
  st_make_valid() %>%
  st_transform(crs = st_crs(df_filtered))

calculate_intersection = function(i) {
  row = df_filtered[i, ]
  cal_poly = calfire %>% filter(fire_name == row$fire_name)
  
  if (nrow(cal_poly) == 0) return(NULL)
  
  intersection = st_intersection(row, cal_poly)
  
  # Handle case where there's no intersection
  if (nrow(intersection) == 0 || all(st_is_empty(intersection))) {
    return(data.frame(
      fire_name = row$fire_name,
      fire_days = row$fire_days,
      metric = row$metric,
      percent_overlap = 0
    ))
  }
  
  # Sum all intersection areas (in case of multipart geometries)
  intersection_area = sum(st_area(intersection))
  calfire_area = sum(st_area(cal_poly))
  
  pct = min(100, as.numeric(intersection_area / calfire_area * 100))
  
  data.frame(
    fire_name = row$fire_name,
    fire_days = row$fire_days,
    metric = row$metric,
    percent_overlap = pct
  )
}

overlap_results = map_dfr(1:nrow(df_filtered), calculate_intersection)

ggplot() + theme_bw() +
  geom_boxplot(data = overlap_results, aes(x = factor(metric), y = percent_overlap, fill = metric))
###
df_variance = df %>%
  select(fire_name, fire_days, metric, calfire_var) %>%
  sf::st_drop_geometry() %>%
  pivot_wider(names_from = metric, values_from = calfire_var)

ggplot() + theme_bw() +
  geom_point(data = df_variance, aes(color = fire_days, x =  dnbr, y = rdnbr))

df_test = sf::st_drop  