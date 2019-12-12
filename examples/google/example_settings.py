import os

if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
    GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')

TASKHAWK_QUEUE = 'dev-myapp'

TASKHAWK_CONSUMER_BACKEND = 'taskhawk.backends.gcp.GooglePubSubConsumerBackend'
TASKHAWK_PUBLISHER_BACKEND = 'taskhawk.backends.gcp.GooglePubSubPublisherBackend'
