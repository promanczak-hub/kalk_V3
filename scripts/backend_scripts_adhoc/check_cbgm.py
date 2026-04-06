import logging
import traceback
from core.matrix_cache_job import process_single_kalkulacja_matrix_task

logging.basicConfig(level=logging.ERROR)

try:
    process_single_kalkulacja_matrix_task('8390ff7f-4a9e-4ce0-aaf1-8284649ac733')
except Exception as e:
    print(traceback.format_exc())
