setwd("~/Desktop/NPS/Fireseverity/Validation")

library(tidyverse)
library(scico)
library(sf)

source('validation.R')

df_dnbr = st_read("validation_metrics_dnbr.gpkg", quiet = T)
df_rbr = st_read("validation_metrics_rbr.gpkg", quiet = T)

calfire = st_read('Validation_Fire_Perimeters_2015_2024.shp', quiet = T) %>%
  rename(fire_name = FIRE_NAME) %>%
  st_make_valid() %>%
  st_transform(crs = st_crs(df_dnbr))

df_filtered_dnbr = df_dnbr %>%
  select(fire_name, metric, geom) %>%
  st_make_valid()

overlap_results_dnbr = map_dfr(1:nrow(df_filtered_dnbr), ~calculate_intersection(.x, df_filtered_dnbr))

results1 = overlap_results_dnbr %>%
  filter(fire_days == 21 & date_mode == 'alarm') %>%
  mutate(UNIT_ID = 'All Parks')

results2 = overlap_results_dnbr %>%
  filter(fire_days == 21 & date_mode == 'alarm') %>%
  left_join(select(calfire, c("fire_name", "UNIT_ID"))) %>%
  filter(!is.na(UNIT_ID)) %>%
  mutate(date_mode = if_else(date_mode == 'alarm', 'Days after Alarm Date', 'Date after Containment')) %>%
  mutate(date_mode = factor(date_mode, levels = c('Days after Alarm Date', 'Date after Containment')))

(p2 = ggplot() + theme_bw() +
    ggtitle('Agreement with Calfire Boundaries') +
    geom_boxplot(data = results1, aes(x = UNIT_ID, y = percent_overlap, fill = UNIT_ID), fill = 'grey80') +
    geom_boxplot(data = results2, aes(x = UNIT_ID, y = percent_overlap, fill = UNIT_ID)) +
    geom_jitter(data = results2, aes(x = UNIT_ID, y = percent_overlap, shape = as.factor(fire_days)), size = 2, width = .25, color = 'black') +
    scale_x_discrete(labels = c('All Parks', 'Channel Islands', 'Joshua Tree', 'Mojave', 'Santa Monica'), name = "") +
    scale_y_continuous(limits = c(0, 100), expand = c(0,0), 'Overlap with Calfire boundaries in %') +
    scale_fill_scico_d(palette = 'lajolla', guide = 'none', begin = .3 ) +
    theme(axis.text.x = element_text(angle = 45, hjust = 1),
          text = element_text(size = 18),
          legend.position = 'None'))

ggsave('overlap_boundaries_report.png')


###

correlation = read_csv("dnbr_r2_results.csv") %>%
  filter(!is.na(r_squared)) %>%
  left_join(select(calfire, c("fire_name", "UNIT_ID", 'YEAR_'))) %>%
  mutate(date_mode = if_else(date_mode == 'alarm', 'Days after Alarm Date', 'Date after Containment')) %>%
  mutate(date_mode = factor(date_mode, levels = c('Days after Alarm Date', 'Date after Containment')),
         fire_name = paste0(fire_name, ' (', UNIT_ID, ", ", YEAR_,')'))

ggplot() + theme_bw() +
  facet_wrap(~date_mode, ncol = 2) +
  geom_point(data = correlation, aes(x = date_after_fire, y = r_squared, color = fire_name, shape = fire_name),
             size = 2) +
  geom_line(data = correlation, aes(x = date_after_fire, y = r_squared, color = fire_name), 
            linewidth = .5, linetype = 'dotted') +
  geom_smooth(data = correlation, aes(x = date_after_fire, y = r_squared), 
              method = 'loess', color = 'black', alpha = 0.1, linewidth = .75) +
  scico::scale_color_scico_d(palette = 'batlow', begin = .3, end = .8, name = 'Fire Name') +
  scale_shape_discrete(name = 'Fire Name', solid = T) +
  scale_x_continuous('Days after fire', expand = c(0,0)) +
  scale_y_continuous('R-squared of Tool vs. BAER dNBR', expand = c(0,0), limits = c(-0.01,1))
