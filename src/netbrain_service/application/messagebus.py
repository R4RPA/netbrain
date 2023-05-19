from test_services import logger

from test_services.atf import wsgw

from test_services.atf.common import (
    Message,
    Event,
    Command,
)

from typing import (
    Callable,
    Type,
)

from test_services.config import settings

import asyncio

import threading

import queue


class MessageBus:
    """
    Internal Communications Bus of the service.

    Messages will be sent to supplied consumers.
    Consumers are functions that accept an Event or Command and act on it.
    Consumers will return a list of further generated Messages during consumption,
    which will be passed on to the MessageBus for processing.
    """

    def __init__(
            self,
            command_consumers: dict[Type[Command], Callable],
            event_consumers: dict[Type[Event], list[Callable]],
            consumer_count: int = settings.MESSAGEBUS_THREAD_COUNT,
    ):
        self.command_consumers = command_consumers
        self.event_consumers = event_consumers
        self.startup(consumer_count=consumer_count)
        self.lock_store = list()

    def startup(self, consumer_count: int):
        """
        This space is used to initialize needed external connections.
        Intended to be run during object initiation, and any time that
        API connection configuration data needs to be reset.
        """
        # ATF WSGW Connection (Lazy, REST-HTTP API)
        self.wsgw = wsgw.Wsgw(
            wsgw.WsgwConfig(
                api_url=settings.WSGW_API,
                api_un=settings.SYS_UN,
                api_pw=settings.SYS_PW,
                domain=settings.WSGW_DOMAIN,
                debug=settings.DEBUG,
            )
        )
        self.message_q = queue.Queue()
        # start consumers/workers
        # each consumer spawns its own thread
        for i in range(consumer_count):
            threading.Thread(target=self.consumer, daemon=True).start()

        logger.info(f'Message Bus initialized with {consumer_count} asynchronous consumers.')

    def add_to_queue(self, messages: list[Message]) -> list[Message]:
        """
        Pass a list of messages to have them added to the Message Queue.

        Returns a list of Messages that could not be added.
        An Empty List represents that all Messages were successfully
        added to the Message Queue.

        Note that there is no backoff logic implemented in this method.
        Any backoff or retry logic will need to be implemented in the
        calling code.
        """
        messages_not_added: list[Message] = []

        for message in messages:
            try:
                self.message_q.put(message)
            except queue.Full as e:
                # if the queue is going to be capped at some point then this
                # exception will need to be handled in the calling code and
                # likely paired with retry logic determined by business needs
                logger.critical(
                    f'Attempt to add Messages {str(messages)} encountered queue.Full exception. This is not expected behavior, design is for uncapped queue. Check code comments. Please review any recent changes to message_bus.message_q configuration when looking for the culprit of this error.')
                messages_not_added.append(message)

        return messages_not_added

    async def __engine(self):
        """
        This is the core execution loop. Grab a message, consume message to
        execute matching code, report done, repeat.
        """
        while True:
            message = self.message_q.get()
            await self.__consume(message)
            self.message_q.task_done()

    def consumer(self):
        """
        Each consumer uses asyncio to run the core execution loop, abstracted
        to __engine.
        """
        asyncio.run(self.__engine())

    async def __consume(self, message: Message):
        """
        This function will check the type of the Message and delegate
        work to the correct method.
        """

        # process (consume) the Message
        try:
            if isinstance(message, Command):
                await self.__consume_command(message)
            elif isinstance(message, Event):
                await self.__consume_event(message)
            else:
                raise ValueError('message must be an Event or Command.')
        except Exception as e:
            logger.debug(f"{message.cid} Exception encountered while processing {str(message)}", exc_info=True)

    async def __consume_command(self, command: Command):
        """
        Pass Command to matching command_consumer function to perform
        any processing work. This is where the seam between calling the
        command_consumer and executing its internal code occurs, allowing
        extensibility by adding components to command_consumers file.
        """
        logger.info(f'{command.cid} consuming command {command}')
        consumer = '(not captured)'

        # deal with idempotency constraints
        #
        # REFACTOR_ALERT://
        # ASYNC contention not being dealt with here due to currently perceived
        # low expectation of triggering. Between the time of lock attainment
        # scanning, and actual lock attainment or insertion into lock_store, another
        # Consumer could also believe it can acquire the lock, and both Consumers would
        # end up thinking that they acquired the lock, and the Message would be double
        # processed
        if command.field_locks:
            attained_locks = set()
            for lock in command.field_locks:
                lock_sig = f"{command.__class__}.{lock}={command.__getattribute__(lock)}"
                if lock_sig in self.lock_store:
                    # already being processed, discard after logging
                    logger.debug(f"{command.cid} lock conflict trying to acquire lock on {lock_sig} for {command}")
                else:
                    # OK to process, adding lock signature to lock_store
                    attained_locks.add(lock_sig)
                    logger.debug(f"{command.cid} adding {lock_sig} to attained_locks for {command}")
            if not len(attained_locks) == len(command.field_locks):
                logger.debug(
                    f"{command.cid} not all locks could be attained, discarding Message {command} attained_locks={attained_locks}")
                return
            else:
                for lock_sig in attained_locks:
                    self.lock_store.append(lock_sig)
                    logger.debug(f"{command.cid} adding lock_sig {lock_sig} to lock_store")

        try:
            consumer = self.command_consumers[type(command)]
            messages = await consumer(command, self.wsgw)
        except Exception as e:
            logger.error(f'{command.cid} Exception occurred while {str(consumer)} was consuming {command}',
                         exc_info=True)
        else:
            self.add_to_queue(messages)
        finally:
            # check for membership in idempotent set (IF in THEN remove)
            if command.field_locks:
                for lock in command.field_locks:
                    lock_sig = f"{command.__class__}.{lock}={command.__getattribute__(lock)}"
                    self.lock_store.remove(lock_sig)
                    logger.debug(f"{command.cid} removed lock signature from lock_store: {lock_sig}")

    async def __consume_event(self, event: Event):
        """
        Pass Event to matching event_consumer function to perform
        any processing work. This is where the seam between calling the
        event_consumer and executing its internal code occurs, allowing
        extensibility by adding components to event_consumers file.
        """
        logger.info(f'{event.cid} processing {event}')
        for consumer in self.event_consumers[type(event)]:
            logger.debug(f'{event.cid} {consumer.__name__} is consuming {event}')
            try:
                messages = await consumer(event)
            except Exception as e:
                logger.error(f'{event.cid} Exception occurred while {consumer} was consuming {event}', exc_info=True)
            else:
                self.add_to_queue(messages)