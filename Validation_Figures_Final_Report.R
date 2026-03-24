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

(p2 = ggplot() + theme_bw() +
    ggtitle('Agreement with Calfire Boundaries per park') +
    geom_boxplot(data = results1, aes(x = UNIT_ID, y = percent_overlap, fill = UNIT_ID), fill = 'grey80') +
    geom_boxplot(data = results2, aes(x = UNIT_ID, y = percent_overlap, fill = UNIT_ID)) +
    geom_jitter(data = results2, aes(x = UNIT_ID, y = percent_overlap, shape = as.factor(fire_days)), size = 1, width = .25, color = 'black') +
    scale_x_discrete(labels = c('All Parks', 'Channel Islands', 'Joshua Tree', 'Seqouia', 'Mojave', 'Santa Monica'), name = "") +
    scale_y_continuous(limits = c(0, 100), expand = c(0,0), 'Overlap with Calfire boundaries in %') +
    scale_fill_scico_d(palette = 'lajolla', guide = 'none', begin = .3 ) +
    theme(axis.text.x = element_text(angle = 45, hjust = 1),
          text = element_text(size = 14),
          legend.position = 'None'))