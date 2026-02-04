---
title: "Validation_Firetool"
format: html_document
editor: visual
---

## Validation Fire Tool

```{r}
setwd("~/Desktop/NPS/Fireseverity/Validation")

source('validation.R')

df_dnbr = st_read("validation_metrics_dnbr.gpkg", quiet = T)
df_rbr = st_read("validation_metrics_rbr.gpkg", quiet = T)

calfire = st_read('Validation_Fire_Perimeters_2015_2024.shp', quiet = T) %>%
  rename(fire_name = FIRE_NAME) %>%
  st_make_valid() %>%
  st_transform(crs = st_crs(df_dnbr))
```

### 2. Are the two different indices truly different in our tool and is ours truly more sensitive?

*This is calculated with 30 days of data after the detection date and using the Calfire boundaries*

```{r}
#| fig-height: 8
#| fig-width: 6
compare_metrics(df_dnbr, df_rbr)
```

### 3. Do our boundaries and those from CalFire match?

```{r}
#| warning: false

calculate_overlap(df_dnbr, calfire)
```

### 4.How sensitive are results to chosen time window?

```{r}
#| warning: false
#| fig-height: 7
#| fig-width: 7
time_sensitivity(df_rbr)
```

### What up with the high numbers?

```{r}
diagnostics(df_rbr, calfire)
```
