import json
import time
import requests
import runpod
from runpod.serverless.utils.rp_validator import validate
from runpod.serverless.modules.rp_logger import RunPodLogger
from requests.adapters import HTTPAdapter, Retry
from schemas.api import API_SCHEMA
from schemas.chat import CHAT_SCHEMA
from schemas.generate import GENERATE_SCHEMA

BASE_URL = 'http://127.0.0.1:5000/api/v1'
TIMEOUT = 600

VALIDATION_SCHEMAS = {
    'chat': CHAT_SCHEMA,
    'generate': GENERATE_SCHEMA,
}

session = requests.Session()
retries = Retry(total=10, backoff_factor=0.1, status_forcelist=[502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))
logger = RunPodLogger()


# ---------------------------------------------------------------------------- #
# Application Functions                                                        #
# ---------------------------------------------------------------------------- #
def wait_for_service(url):
    while True:
        try:
            requests.get(url)
            return
        except requests.exceptions.RequestException:
            print('Service not ready yet. Retrying...')
        except Exception as err:
            print(f'Error: {err}')

        time.sleep(0.2)


def send_get_request(endpoint):
    return session.get(
        url=f'{BASE_URL}/{endpoint}',
        timeout=TIMEOUT
    )


def send_post_request(endpoint, payload):
    return session.post(
        url=f'{BASE_URL}/{endpoint}',
        json=payload,
        timeout=TIMEOUT
    )


# ---------------------------------------------------------------------------- #
# RunPod Handler                                                               #
# ---------------------------------------------------------------------------- #
def validate_api(event):
    if 'api' not in event:
        return {
            'errors': '"api" is a required field in the payload'
        }

    if type(event['api']) is not dict:
        return {
            'errors': '"api" must be a dictionary containing "method" and "endpoint"'
        }

    event['api']['endpoint'] = event['api']['endpoint'].lstrip('/')

    return validate(event['api'], API_SCHEMA)


def validate_input(event):
    endpoint = event['api']['endpoint']
    validated_input = {}

    if endpoint == 'generate':
        validated_input = validate(event['input'], GENERATE_SCHEMA)
    elif endpoint == 'chat':
        validated_input = validate(event['input'], CHAT_SCHEMA)

    return endpoint, event['api']['method'], validated_input


def handler(event):
    validated_api = validate_api(event)

    if 'errors' in validated_api:
        return {
            'error': validated_api['errors']
        }

    endpoint, method, validated_input = validate_input(event)

    if 'errors' in validated_input:
        return {
            'error': validated_input['errors']
        }

    payload = validated_input['validated_input']

    try:
        logger.log(f'Sending {method} request to: {endpoint}')

        if method == 'GET':
            response = send_post_request(endpoint, payload)
        elif method == 'POST':
            response = send_post_request(endpoint, payload)
    except Exception as e:
        return {
            'error': str(e)
        }

    return response.json()


if __name__ == '__main__':
    wait_for_service(url='http://127.0.0.1:5000/api/v1/model')
    logger.log('Oobabooga API is ready', 'INFO')
    logger.log('Starting RunPod Serverless...', 'INFO')
    runpod.serverless.start(
        {
            'handler': handler
        }
    )