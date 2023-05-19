import json
from dataclasses import dataclass
from dataclasses import asdict
from xmlrpc.client import Boolean

from test_services import logger

from test_services.config import settings

from test_services.atf.common import Alert
from test_services.atf.common import Command

from requests import post

from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning, SSLError


@dataclass
class StackstormInstance:
    base_url: str
    alert_webhook: str
    api_key: str
    send_comment_webhook: str
    send_comment_api_key: str


class Stackstorm:
    """
    Adapter class to handle communication with Stackstorm.
    No arguments are required to instantiate this class, as it
    pulls required data from settings.


    Example:

    mock_alert: test_Services.atf.alerts.FailedTest
    Stackstorm().send_alert(mock_alert)
    """

    def __init__(self):
        self.dev_instance = StackstormInstance(
            base_url=settings.STACKSTORM_BASE_URL_DEV,
            alert_webhook=settings.STACKSTORM_ALERT_WEBHOOK,
            api_key=settings.STACKSTORM_API_KEY_DEV,
            send_comment_webhook=settings.STACKSTORM_SEND_COMMENT,
            send_comment_api_key=settings.STACKSTORM_SEND_COMMENT_API_KEY_DEV,
        )
        self.prod_instance = StackstormInstance(
            base_url=settings.STACKSTORM_BASE_URL_PROD,
            alert_webhook=settings.STACKSTORM_ALERT_WEBHOOK,
            api_key=settings.STACKSTORM_API_KEY_PROD,
            send_comment_webhook=settings.STACKSTORM_SEND_COMMENT,
            send_comment_api_key=settings.STACKSTORM_SEND_COMMENT_API_KEY_DEV,
        )

    def send_alert(self, alert: Alert) -> bool:
        # build url based on target_environ
        target = self.prod_instance if alert.production_alert else self.dev_instance
        url = f"{target.base_url}{target.alert_webhook}?st2-api-key={target.api_key}"

        # alert -> dict
        payload = asdict(alert)

        # disable insecure request warning
        disable_warnings(InsecureRequestWarning)
        disable_warnings(SSLError)

        # send to Stackstorm
        try:
            response = post(url, data=payload, verify=False)
        except:
            logger.error(f"{alert.cid} unable to send alert, encountered exception.", exc_info=True)
        else:
            # handle and log response
            if response.ok:
                # notice that we remove the api key by slicing args off
                logger.info(f"{alert.cid} alert was sent successfully to {url[:url.find('?')]}")
                return True
            else:
                logger.error(
                    f"{alert.cid} during sending of {alert}, received error from {url[:url.find('?')]} {response.status_code} {response.text}")

        # if we get here, sending the alert was not successful
        return False

    def send_comment(self, command: Command) -> bool:
        # build url based on target_environ
        target = self.dev_instance
        # url = f"{target.base_url}{target.send_comment_webhook}?st2-api-key={target.send_comment_api_key}"
        url = "http://localhost:8000/api/v1/test/payload"

        comment = {
            "Domain": command.domain,
            "TestId": command.test_id,
            "TestName": command.test_name,
            "TestStatus": command.test_status,
            "StatusDescription": command.status_description,
            "TestStartTime": command.start_time,
            "TestEndTime": command.end_time
        }

        # status = True if command.test_status.lower() == "passed" else False

        # command -> dict
        payload = {
            "support_ticket": f"{command.support_ticket}",
            "comment": json.dumps(comment, indent=4),
            # "testname": command.test_name,
            # "passed": status,
        }

        # disable insecure request warning
        disable_warnings(InsecureRequestWarning)
        disable_warnings(SSLError)

        # send to Stackstorm
        try:
            logger.info(f"{command.cid} payload being sent to stackstorm: {payload}")
            response = post(url, data=payload, verify=False)
        except:
            logger.error(f"{command.cid} unable to send comment, encountered exception.", exc_info=True)
        else:
            # handle and log response
            if response.ok:
                # notice that we remove the api key by slicing args off
                logger.info(
                    f"{command.cid} alert was sent successfully to {url[:url.find('?')]} with payload: {payload}")
                return True
            else:
                logger.error(
                    f"{command.cid} during sending of {command}, received error from {url[:url.find('?')]} {response.status_code} {response.text}")

        # if we get here, sending the alert was not successful
        return False

    def notify_of_test_results(self, cid: str, support_ticket: str, comment: str, testname: str, passed: bool,
                               prod=True) -> bool:
        # build url based on target_environ
        target = self.dev_instance if not prod else self.prod_instance
        url = f"{target.base_url}{target.send_comment_webhook}?st2-api-key={target.send_comment_api_key}"

        # build payload and convert to json-encoded string
        payload = {
            "support_ticket": support_ticket,
            "comment": comment,
            "testname": testname,
            "passed": passed,
        }
        payload_string = json.dumps(payload)

        # disable insecure request warning
        disable_warnings(InsecureRequestWarning)
        disable_warnings(SSLError)

        # send to Stackstorm
        try:
            response = post(url, data=payload_string, verify=False)
        except Exception as e:
            logger.error(f"{cid} unable to send comment, encountered Exception {str(e)}")
        else:
            # handle and log response
            if response.ok:
                # notice that we remove the api key by slicing args off
                logger.info(f"{cid} test results sent successfully to {url[:url.find('?')]} with payload: {payload}")
                return True
            else:
                logger.error(
                    f"{cid} during sending of test result to Stackstorm, received error from {url[:url.find('?')]} {response.status_code} {response.text}")

        # if we get here, sending the alert was not successful
        return False

    def send_test_update(self, command: Command) -> bool:
        # build url based on target_environ
        target = self.dev_instance
        url = f"{target.base_url}{target.send_comment_webhook}?st2-api-key={target.send_comment_api_key}"

        comment = {
            "Domain": command.domain,
            "TestId": command.test_id,
            "TestName": command.test_name,
            "TestStatus": command.test_status,
            "StatusDescription": command.status_description,
            "TestStartTime:": command.start_time,
            "TestEndTime": command.end_time
        }

        status = True if command.test_status.lower() == "passed" else False

        # command -> dict
        payload = {
            "support_ticket": command.support_ticket,
            "comment": json.dumps(comment, indent=4),
            "testname": command.test_name,
            "passed": status,
        }

        payload_string = json.dumps(payload)

        # disable insecure request warning
        disable_warnings(InsecureRequestWarning)
        disable_warnings(SSLError)

        # send to Stackstorm
        try:
            response = post(url, data=payload_string, verify=False)
        except:
            logger.error(f"{command.cid} unable to send comment, encountered exception.", exc_info=True)
        else:
            # handle and log response
            if response.ok:
                # notice that we remove the api key by slicing args off
                logger.info(
                    f"{command.cid} alert was sent successfully to {url[:url.find('?')]} with payload: {payload}")
                return True
            else:
                logger.error(
                    f"{command.cid} during sending of {command}, received error from {url[:url.find('?')]} {response.status_code} {response.text}")

        # if we get here, sending the alert was not successful
        return False
