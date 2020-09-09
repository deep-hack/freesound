from django.conf import settings
from django.core.cache import cache
from celery.decorators import task
from celery import Task
import logging

from clustering import ClusteringEngine
from clustering_settings import CLUSTERING_CACHE_TIME, CLUSTERING_PENDING_CACHE_TIME
from . import CLUSTERING_RESULT_STATUS_PENDING, CLUSTERING_RESULT_STATUS_FAILED

logger = logging.getLogger('clustering')


class ClusteringTask(Task):
    """ Task Class used  for defining the clustering engine only required in celery workers    
    """
    def __init__(self):
        if settings.IS_CELERY_WORKER:
            self.engine = ClusteringEngine()
            

@task(name="cluster_sounds", base=ClusteringTask)
def cluster_sounds(cache_key_hashed, sound_ids, features):
    """ Triggers the clustering of the sounds given as argument with the specified features.

    This is the task that is used for clustering the sounds of a search result asynchronously with Celery.
    The clustering result is stored in cache using the hashed cache key built with the query parameters.

    Args:
        cache_key_hashed (str): hashed key for storing/retrieving the results in cache.
        sound_ids (List[int]): list containing the ids of the sound to cluster.
        features (str): name of the features used for clustering the sounds (defined in the clustering settings file).
    """
    # store pending state in cache
    cache.set(cache_key_hashed, CLUSTERING_RESULT_STATUS_PENDING, CLUSTERING_PENDING_CACHE_TIME)

    try:
        # perform clustering
        result = cluster_sounds.engine.cluster_points(cache_key_hashed, features, sound_ids)

        # store result in cache
        cache.set(cache_key_hashed, result, CLUSTERING_CACHE_TIME)

    except Exception as e:  
        # delete pending state if exception raised during clustering
        cache.set(cache_key_hashed, CLUSTERING_RESULT_STATUS_FAILED, CLUSTERING_PENDING_CACHE_TIME)
        logger.error("Exception raised while clustering sounds", exc_info=True)
