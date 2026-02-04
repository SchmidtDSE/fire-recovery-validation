setwd("~/Desktop/NPS/Fireseverity/Validation")

library(tidyverse)
library(scico)
library(sf)


calculate_intersection = function(i, df) {
  row = df[i, ]
  cal_poly = select(calfire, fire_name) %>% filter(fire_name == row$fire_name)
  
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
  
  pct = min(100, as.numeric(intersection_area / calfire_area * 100))
  
  data.frame(
    fire_name = row$fire_name,
    fire_days = row$fire_days,
    metric = row$metric,
    percent_overlap = pct
  )
}


calculate_overlap = function(df_dnbr, calfire) {
  
  df_filtered_dnbr = df_dnbr %>%
    select(fire_name, fire_days, metric, geom) %>%
    st_make_valid()
  
  overlap_results_dnbr = map_dfr(1:nrow(df_filtered_dnbr), ~calculate_intersection(.x, df_filtered_dnbr))
  
  results1 = overlap_results_dnbr %>%
    mutate(UNIT_ID = 'All Parks')
  
  results2 = overlap_results_dnbr %>%
    left_join(select(calfire, c("fire_name", "UNIT_ID")))
  
  
  p = ggplot() + theme_bw() +
    ggtitle('Agreement with Calfire Boundaries per park') +
    geom_boxplot(data = results1, aes(x = UNIT_ID, y = percent_overlap, fill = UNIT_ID), fill = 'grey80') +
    geom_boxplot(data = results2, aes(x = UNIT_ID, y = percent_overlap, fill = UNIT_ID)) +
    geom_jitter(data = results2, aes(x = UNIT_ID, y = percent_overlap, shape = as.factor(fire_days)), size = 1, width = .25, color = 'black') +
    scale_x_discrete(labels = c('All Parks', 'Channel Islands', 'Joshua Tree', 'Seqouia', 'Mojave', 'Santa Monica'), name = "") +
    scale_y_continuous(limits = c(0, 100), expand = c(0,0), 'Overlap with Calfire boundaries in %') +
    scale_fill_scico_d(palette = 'lajolla', guide = 'none', begin = .3 ) +
    theme(axis.text.x = element_text(angle = 45, hjust = 1),
          text = element_text(size = 14),
          legend.position = 'None')
  
  return(p)
  
}

compare_metrics = function(df_dnbr, df_rbr) {
  

results_dnbr = st_drop_geometry(df_dnbr) %>%
  filter(fire_days == 30) %>%
  select(fire_name, fire_days, metric, calfire_mean, calfire_var)

results_dnbr_parks = results_dnbr %>%
  left_join(select(calfire, c("fire_name", "UNIT_ID")))

results_rbr = st_drop_geometry(df_rbr) %>%
  filter(fire_days == 30) %>%
  select(fire_name, fire_days, metric, calfire_mean, calfire_var)

results_rbr_parks = results_rbr %>%
  left_join(select(calfire, c("fire_name", "UNIT_ID")))

results_parks = bind_rows(results_dnbr_parks, results_rbr_parks) %>%
  rename('Mean burn severity' = calfire_mean, 'Variance of burn severity' = calfire_var) %>%
  pivot_longer(cols = c(`Mean burn severity`, `Variance of burn severity`), names_to = 'name', values_to = 'value')

results = bind_rows(results_dnbr, results_rbr) %>%
  rename('Mean burn severity' = calfire_mean, 'Variance of burn severity' = calfire_var) %>%
  pivot_longer(cols = c(`Mean burn severity`, `Variance of burn severity`), names_to = 'name', values_to = 'value') %>%
  mutate(UNIT_ID = 'All Parks')

label_data = results %>%
  group_by(name) %>%
  summarise(y_pos = max(value, na.rm = TRUE)*0.9, .groups = 'drop') %>%
  crossing(metric = c('dnbr', 'rbr')) %>% 
  mutate(UNIT_ID = "All Parks",
         label_text = ifelse(metric == 'dnbr', 'dNBR', 'RBR'))

(p = ggplot() + theme_bw() +
    ggtitle('Comparison of dNBR and RBR') +
    facet_wrap(~name, ncol = 2, scales = 'free') +
    geom_boxplot(data = results, aes(x = UNIT_ID, y = value, fill = UNIT_ID, color = metric), fill = 'grey80') +
    geom_boxplot(data = results_parks, aes(x = UNIT_ID, y = value, fill = UNIT_ID, color = metric)) +
    geom_text(data = label_data, aes(x = UNIT_ID, y = y_pos, label = label_text, color = metric),
              position = position_dodge(width = 0.75), vjust = 0, fontface = "bold", size = 4) +
    scale_x_discrete(labels = c('All Parks', 'Channel Islands', 'Joshua Tree', 'Seqouia', 'Mojave', 'Santa Monica'), name = "") +
    scale_y_continuous('Burn severity', expand = c(0,0.01)) +
    scale_fill_scico_d(palette = 'lajolla', guide = 'none', begin = .3 ) +
    scale_color_manual(values = c('dnbr' = 'grey0', 'rbr' = 'grey1'), name = 'Metric') +
    theme(axis.text.x = element_text(angle = 45, hjust = 1),
        text = element_text(size = 14),
        legend.position = 'None'))

return(p)
}

time_sensitivity = function(df_dnbr) {

results_metric = st_drop_geometry(df_dnbr) %>%
  select(fire_name, fire_days, metric, calfire_mean, calfire_var) %>%
  group_by(fire_name) %>%
  mutate(calfire_mean_z = scale(calfire_mean),
         calfire_var_z = scale(calfire_var)) %>%
  rename('Mean burn severity (z-transformed)' = calfire_mean_z, 'Variance of burn severity (z-transformed)' = calfire_var_z) %>%
  pivot_longer(cols = c(`Mean burn severity (z-transformed)`, `Variance of burn severity (z-transformed)`), names_to = 'name', values_to = 'value') %>%
  left_join(select(calfire, c("fire_name", "UNIT_ID")))
  


  p = ggplot() + theme_bw() +
    facet_wrap(~name, ncol = 1, scales = 'free') +
    geom_jitter(data = results_metric, aes(x = fire_days, y = value, color = UNIT_ID, shape = UNIT_ID), width = .5) +
    geom_smooth(data = results_metric, aes(x = fire_days, y = value), method = 'loess', color = 'black') +
    scale_color_scico_d(palette = 'lajolla', guide = 'none', begin = .3, name = 'Park Unit') +
    scale_shape_discrete(name = 'Park Unit') +
    scale_x_continuous('Fire duration (days)', breaks = c(5, 10, 15, 21, 30, 45, 60, 90)) +
    scale_y_continuous('Burn severity (z-transformed)', expand = c(0,.1)) +
    theme(panel.grid.minor = element_blank(),
          text = element_text(size = 14))
  
  return(p)
  
}

diagnostics = function(df_metric, calfire) {
  
  df_diagnostics = st_drop_geometry(df_metric) %>%
    select(fire_name, fire_days, calfire_pct_removed, filtered_pct_removed) %>%
    pivot_longer(cols = c(calfire_pct_removed, filtered_pct_removed), names_to = 'metric', values_to = 'pct_removed') %>%
    left_join(select(calfire, c("fire_name", "UNIT_ID")))
  
  p = ggplot() + theme_bw() +
    geom_histogram(data = df_diagnostics, aes(x = pct_removed, fill = metric), bins = 50, color = 'black') +
    scale_fill_scico_d(palette = 'lajolla', guide = 'none', begin = .3, name = 'Park Unit')
  
  return(p)
}




        