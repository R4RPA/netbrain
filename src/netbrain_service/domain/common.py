from dataclasses import dataclass

from random import choices

from typing import NewType
from typing import Literal
from typing import Union

from datetime import datetime
from datetime import timezone
from datetime import timedelta

from src.netbrain_service.config import settings

RAND_ROOT = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789'

# short for Correlation ID, standard length of 12 alphanumeric chars
# a cid should be created at the start of a transaction or process
# and be passed through each phase for log correlation and event
# sourcing abilities, real-time and historical, in the future.
Cid = NewType('Cid', str)


# provides a randomly generated correlation id
def get_cid() -> Cid:
    selections: list[str] = choices(RAND_ROOT, k=settings.CORRELATION_ID_LENGTH)
    cid = Cid(''.join(selections))
    return cid


#
# Message base classes
class Message:
    """
    Abstract parent level class intended to be extended. Only
    refer to Message when extending to a more specialized base
    class, such as Command or Event.

    You should not be instantiating a Message.

    Locking behavior is provided and is declared here so that all
    children inherit the behavior. To declare idempotent behavior
    for a Message, provide one or more fields as strings that
    require uniqueness constraints across the inherited Message
    child class namespace [ex. Message.Command.TestCommand
    namespace in below example].

    For example
        Message.Command.TestCommand may have the fields
        cid, name, domain, description, create_time
        and field_locks could be ["name", "domain"]

        In this case, every Message.Command.TestCommand that comes
        in will try to run and the MessageBus will confirm that
        no other Message.Command.TestCommand with the same data in
        fields "name" and "domain" is currently running, by checking
        a idempotent cllection. If it is, the Message is discarded
        with a logging message recording the event, if it is not
        currently running, the Message is processed and the
        "signature" of the Message type and data from the fields is
        added to a idempotent collection so that the next
        Message.Command.TestCommand that matches will be discarded
        as per above description.

    """
    cid: Cid
    create_time: datetime
    target_stage: Literal[
        "DEV",
        "TEST",
        "PROD",] = "PROD"


class Document(Message):
    """
    Message that is a Data Representation, typically of a
    resource or result.

    Informational in nature, not of something
    that has occurred, as that has its Event, but something that
    is. Typically used as a method of transferring State.
    """
    cid: Cid
    create_time: datetime
    target_stage: Literal[
        "DEV",
        "TEST",
        "PROD",] = "PROD"


class Command(Message):
    """
    Message that makes a request of the system, analagous to
    an instruction being given.

    Commands are only ever passed to one function. This is
    because if you are asking for a change to be made in the
    system, we do not want multiple functions trying to make
    that same change.

    Command is an abstract class, not intended to be directly
    instantiated. You should extend it to a specific class,
    such as ExampleCommand(Command)
    """

    field_locks: list[str] = list()


class Event(Message):
    """
    Message that documents the occurrence or result of an
    action somewhere in the system

    Events can be passed to many functions. This is because
    an event is inherently informative and non-actionable.
    If an action (besides reporting/logging/etc.) needs to
    be taken in response to an Event, then an EventConsumer
    of that Event should consume it and then return one or
    more Commands that make further requests of the system.

    Event is an abstract class, not intended to be directly
    instantiated. You should extend it to a specific class,
    such as ExampleEvent(Event)
    """
    pass


# End Message base classes
#
def get_yesterday() -> datetime:
    # return a datetime object representing yesterday
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    return yesterday
