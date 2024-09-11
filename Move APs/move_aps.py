#!/usr/bin/env python3
"""
Ruckus Cloud AP Migration Script

This script automates the process of moving APs from one venue to another in Ruckus Cloud.
"""

import requests
from time import sleep
from typing import Dict, Any

# Configuration
CONFIG = {
    'DOMAIN': 'https://ruckus.cloud',
    'USERNAME': 'YOUR_RUCKUS_CLOUD_USERNAME',
    'PASSWORD': 'YOUR_RUCKUS_CLOUD_PASSWORD',
    'TENANT_ID': 'YOUR_RUCKUS_CLOUD_TENANT_ID',
    'SOURCE_VENUE_ID': 'SOURCE_VENUE_ID',
    'TARGET_VENUE_ID': 'TARGET_VENUE_ID'
}

class RuckusCloudAPI:
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.session = requests.Session()

    def login(self) -> bool:
        """Authenticate with Ruckus Cloud."""
        print(f'Logging in to: {self.config["DOMAIN"]}')
        response = self.session.post(
            f'{self.config["DOMAIN"]}/token',
            json={
                'username': self.config['USERNAME'],
                'password': self.config['PASSWORD'],
                'region': 'US'
            }
        )
        if response.status_code != 200:
            print('Error logging-in:', response)
            return False
        print('Logged-in successfully')
        return True

    def wait_for_async_response(self, response: requests.Response, sleep_time: int = 2) -> Dict[str, Any]:
        """
        Wait for asynchronous API requests to complete.

        :param response: Initial API response
        :param sleep_time: Duration to wait between polling the status
        :return: The entity as returned by the original response
        """
        if response.status_code != 202:
            return response.json()

        request_id = response.json()['requestId']
        print(f'\nWaiting for request to complete: {request_id}')

        while True:
            r = self.session.get(f'{self.config["DOMAIN"]}/api/tenant/{self.config["TENANT_ID"]}/request/{request_id}')
            if r.status_code != 200 or not r.text:
                print(f'Request status undefined [{r.status_code}]: "{r.text}"')
            else:
                request_details = r.json()
                print(f'\nRequest: {request_details["status"]}, {request_details}')
                if request_details['status'] in ['SUCCESS', 'FAIL']:
                    break
            sleep(sleep_time)

        if request_details['status'] != 'SUCCESS':
            raise Exception(request_details['status'])

        return response.json()['response']

    def move_aps(self):
        """Move all APs from source venue to target venue."""
        if not self.login():
            return

        # Get AP groups from source venue
        r = self.session.get(f'{self.config["DOMAIN"]}/api/tenant/{self.config["TENANT_ID"]}/wifi/venue/{self.config["SOURCE_VENUE_ID"]}/ap-group')
        ap_groups = r.json()

        for group in ap_groups:
            if 'aps' in group:
                for ap in group['aps']:
                    self._move_single_ap(ap)

    def _move_single_ap(self, ap: Dict[str, Any]):
        """Move a single AP to the target venue."""
        ap_id = ap['serialNumber']
        ap['venueId'] = self.config['TARGET_VENUE_ID']
        ap['apGroupId'] = None

        r = self.session.put(f'{self.config["DOMAIN"]}/api/tenant/{self.config["TENANT_ID"]}/wifi/ap/{ap_id}', json=ap)
        self.wait_for_async_response(r)
        print(f"Moved AP {ap_id} to target venue")

def main():
    api = RuckusCloudAPI(CONFIG)
    api.move_aps()

if __name__ == "__main__":
    main()
