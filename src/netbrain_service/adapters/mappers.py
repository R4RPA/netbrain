from test_services.atf.common import (
    Message,
    Command,
    Event,
    get_cid,
    get_yesterday,
)

from test_services.atf import (
    commands,
    events,
)

from test_services import logger

from datetime import (
    datetime,
    timezone,
)


def documents_to_messages(documents: list[dict]) -> list[Message]:
    return_messages: list[Message] = []
    for document in documents:
        if document.get('meta_message_type') == 'Command':
            return_messages.append(convert_to_command(document))
        elif document.get('meta_message_type') == 'Event':
            return_messages.append(convert_to_event(document))
        else:
            logger.error(f'Invalid document field: meta_message_type must be Command or Event, not {document.get("meta_message_type")}')
    return return_messages


def convert_to_event(document: dict) -> Event:
    """
    The purpose of this function is to convert formatted documents from test_services.external_message_queue
    collection into Events that can be passed to the Messagebus.
    """
    message_type: str = document.get('message_type', '')
    event: Event = events.EmptyEvent(cid=get_cid(), create_time=datetime.now(timezone.utc))


def convert_to_command(document: dict) -> Command:
    """
    This function is used to convert formatted documents from test_services.external_message_queue
    collection into Commands that can be passed to the Messagebus.

    To add a new mapping, just follow the format established below, capturing the message
    type and assigning the correct command to the command variable.

    Calling code expects a Command to be returned, so we use EmptyCommand for the scenario
    that the command provided has not yet been mapped.
    """

    message_type: str = document.get('message_type', '')
    command: Command = commands.EmptyCommand(cid=get_cid(), create_time=datetime.now(timezone.utc))


command_types = {

}

event_types = {

}
