YEAR_START = 2015
YEAR_END = 2024
PARKS = ['JTP', 'MNP', 'KNP', 'CNP', 'SMP']
POST_FIRE_PERIOD = [5, 10, 15, 21, 30, 45, 60, 90]
POST_FIRE_REFERENCE_POINT =  ['alarm', 'cont']
METRICS = ['dnbr', 'rbr']

URL_API = "https://fire-recovery-backend-dev-113009620257.us-central1.run.app/fire-recovery/process/analyze_fire_severity"

PATH_CALFIRE = 'California_Fire_Perimeters_(all).shp'
PATH_FIRES_VALIDATION = f'Validation_Fire_Perimeters_{YEAR_START}_{YEAR_END}.shp'
PATH_JOBS_LOG = 'validation_sent_requests_log.csv'



