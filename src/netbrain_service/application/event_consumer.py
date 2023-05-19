import logging
from src.netbrain_service.application import command_consumers

logger = logging.getLogger(__name__)


def process_event(payload):
    logger.info("process_event > Start")
    event_consumer = EventConsumer()
    event_consumer.register_event_received(payload)
    event_consumer.generate_login_token()
    event_consumer.translate_incoming_payload_to_benchmark_payload()
    event_consumer.check_and_add_benchmark()
    event_consumer.get_benchmark_status()
    event_consumer.get_device_info()
    event_consumer.process_device_content()
    event_consumer.delete_benchmark()
    event_consumer.logout_api()
    logger.info("process_event > end")


class EventConsumer:
    def __init__(self):
        self.username, self.password = get_creds()
        logger.info("EventConsumer > Initiated")

    def generate_login_token(self):
        return command_consumers.generate_login_token(self.username, self.password)

    @staticmethod
    def logout_api():
        return command_consumers.logout_api()

    @staticmethod
    def register_event_received(payload):
        return command_consumers.create_event_entry(payload)

    @staticmethod
    def translate_incoming_payload_to_benchmark_payload():
        return command_consumers.translate_incoming_payload_to_benchmark_payload()

    @staticmethod
    def check_and_add_benchmark():
        return command_consumers.check_and_add_benchmark()

    @staticmethod
    def get_benchmark_status():
        return command_consumers.get_benchmark_status()

    @staticmethod
    def get_device_info():
        return command_consumers.get_device_info()

    @staticmethod
    def process_device_content():
        return command_consumers.process_device_content()

    @staticmethod
    def delete_benchmark():
        return command_consumers.delete_benchmark()


def get_creds():
    username = "amd_rawataj"
    password = "Netb@238"
    return username, password


