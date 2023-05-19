from random import choices
from time import sleep

from typing import NewType

from test_services.adapters.odm import ExternalMessageQueue
from test_services.adapters.odm import PollingEntry
# from test_services.adapters.odm import PollingManagerEntity

from test_services.atf.common import get_cid

from pymongo.errors import DuplicateKeyError

from dataclasses import dataclass

from datetime import datetime
from datetime import timezone

# short for Polling Manager ID, PMID allows us to make a
# Polling Manager an Entity with state maintained in the
# external database. This is a step toward scalability.
Pmid = NewType('Pmid', str)


@dataclass(frozen=True)
class PollingAssignment:
    """
    Represents a PollingEntry Document assigned to the PollingManager.

    Implemented as an immutable object due to the fact that the
    _id is not a local entity id but rather the id of the
    PollingEntry to which this Assignment refers. We take advantage
    of this for comparison purposes and treat this Object as a DTO.
    This is important, as it means there is an expectation of this
    class that its objects can be compared directly to each other for
    equality checks.

    If the PollingEntry changes then a new PollingAssignment must be
    created.
    """
    entry_id: str
    domain: str
    campaign: str
    test: str
    interval: int


def pe_to_pa(polling_entry: PollingEntry) -> PollingAssignment:
    """
    This function accepts a PollingEntry (dictionary) and returns
    an appropriate PollingAssignment.

    PollingEntry contains some fields that are superfluous to a
    PollingAssignment, and also _id becomes entry_id, so rather
    than do any unpacking + modification, we just map directly.

    NOTE: Consider this function strongly coupled to both PollingEntry
    and PollingAssignment; a change to either of those classes will
    likely require a change here as well.
    """

    return PollingAssignment(
        entry_id=polling_entry._id,
        domain=polling_entry.domain,
        campaign=polling_entry.campaign,
        test=polling_entry.test,
        interval=polling_entry.interval,
    )


class PollingManager:
    """
    This class allows the orchestration of polling for updated
    test results by placing the appropriate Command in the
    External Message Queue for processing by the Service Daemon.

    When started and then every subsequent 5 minutes, the Polling
    Manager object will:
        - sync its state from its Polling Manager Entity Document.
        - search for new Polling Manager Entries that do not yet
            have a Polling Manager ID assigned, take assignment
            and update the Polling Entry Document with PMID.
        - update its last_sync time within its state

    Once started, after the initial state check described above,
    the Polling Manager will do the following every minute:
        - increment a counter for each assigned Polling Entry
        - check each entry to see if its counter equals or is
            greater than its interval attribute, if yes then
            place the Command on the External Message Queue
        - if Command created for any Polling Entry, reset the
            run count to 0
    """

    RAND_ROOT = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789'

    def __init__(self, logger):
        # self._pmid = self.__create_and_return_entity_id()
        self._logger = logger
        self._mins_running = 0
        self._last_sync = False
        self._dead_assignments: dict[str, int] = {}
        self._polling_assignments: set[PollingAssignment] = set()
        self.__event_loop()

    # def __create_and_return_entity_id(self) -> str:
    #     pmid = ""
    #     unique_pmid_found = False
    #     while not unique_pmid_found:
    #         proposed_pmid = "".join(choices(self.RAND_ROOT, k=8))
    #         try:
    #             PollingManagerEntity(
    #                 _id = proposed_pmid,
    #                 last_sync = datetime.now(timezone.utc),
    #             ).save()
    #         except DuplicateKeyError:
    #             """
    #             this seems crazy with a factor of 8 right?
    #             crazy would be knowing this is possible and
    #             the nightmare it could cause and not just
    #             accounting for it and providing a guarantee.
    #             """
    #             continue
    #         else:
    #             pmid = proposed_pmid
    #             unique_pmid_found = True
    #     return pmid

    def __event_loop(self):
        while True:
            # sync with datasource every 5 minutes
            if self._mins_running % 5 == 0:
                self.__state_sync()

            # every minute
            # get polling entries and check all assignments
            self.__get_new_polling_entries()
            assignments_to_run: list[PollingAssignment] = self.__check_assignments()
            self.__run_assignments(assignments_to_run)

            # increment then sleep for 1 minute, passed to
            # time.sleep() as seconds. this function just loops
            # and loops. Good refactor would be to add a bool
            # that gets checked on each run which is available for
            # other threads or processes to set to false to kill
            # this event loop.
            self._mins_running += 1
            sleep(60)

    def __run_assignments(self, assignments: list[PollingAssignment]):
        """
        This function accepts a list of PollingAssignment objects which
        it will convert to Update* Commands that get saved on the
        External Message Queue for processing by the Service Daemon.
        """

        self._logger.info(f"Running through provided list of assignments.")
        for assignment in assignments:
            try:
                ExternalMessageQueue(
                    meta_message_type="Command",
                    message_type="UpdateCampaignResults",
                    domain=assignment.domain,
                    campaign=assignment.campaign,
                    cid=get_cid(),
                    create_date=datetime.now(timezone.utc),
                    # test = assignment.test,
                ).save()
            except Exception as e:
                self._dead_assignments[assignment.entry_id] = 0
                self._polling_assignments.remove(assignment)
                self._logger.error(
                    f"Error encountered while placing Message on External Message Queue for {assignment}",
                    exc_info=True)
                self._logger.debug(f"Current local _dead_assignments {str(self._dead_assignments)}")
            else:
                PollingEntry.objects(_id=assignment.entry_id).update_one(last_schedule=datetime.now(timezone.utc))

        self._logger.info(f"Completed running through provided list of assignments.")

    def __check_assignments(self) -> list[PollingAssignment]:
        """
        Loop through assignments and check each to determine if
        its interval has been met. Return a list of assignments
        that need Messages placed on external queue.

        We do this by using the modulo operator to determine if
        the assignment's interval is a factor of the current
        _mins_running instance variable. If interval is 5 mins
        and we have been running 15 mins, 15 % 5 = 0 which means
        we should run that assignment now. At 16 mins, 16 % 5 = 1
        so the assignment is not acted upon.
        """

        assignments_due: list[PollingAssignment] = []

        self._logger.info(f"Checking local Active PollingAssignments.")
        for assignment in self._polling_assignments:
            if assignment.interval:
                if self._mins_running % assignment.interval == 0:
                    assignments_due.append(assignment)

        self._logger.debug(f"Identified the following assignments with a triggered interval: {str(assignments_due)}")
        return assignments_due

    def __get_new_polling_entries(self):
        """
        This queries for all PollingEntry objects, compares the results to
        the current PollingAssignments, and adds any that aren't being
        locally tracked to _polling_assignments
        """

        self._logger.info(f"Checking for new PollingEntry documents.")
        new_entries = PollingEntry.objects()
        for entry in new_entries:
            pa = pe_to_pa(entry)
            if pa not in self._polling_assignments:
                self._polling_assignments.add(pa)
                self._logger.info(f"Added {str(entry)} to local assignments as {pa}")
        self._logger.debug(f"Completed checking for new PollingEntry documents.")

    def __state_sync(self):
        """
        Sync PollingAssignments with their related PollingEntry datastore
        entries.

        Since a PollingAssignment is immutable, a change in the PollingEntry
        will result in the addition of the new Assignment and removal of the
        old.

        Also, the dead_assignments pile will be cycled through to see if dead
        assignments can be resynced.

        REFACTOR ALERT: Add logic to do something with dead assignments after
        a number of cycles, such as emailing a group or something.
        """
        state_changed = {}

        # check for any changes to source PollingEntry
        for assignment in self._polling_assignments:
            try:
                raw_truth = PollingEntry.objects(_id=assignment.entry_id).first()
                truth: PollingAssignment = pe_to_pa(raw_truth)  # convert to Assignment
                if not assignment == truth:
                    # assignments are immutable so they can be dict keys!
                    # model: {old_state: new_state}
                    self._logger.info(
                        f"PollingEntry document change detected PollingEntry with ID {assignment.entry_id} is scheduled to have the associated PollingAssignment updated.")
                    state_changed[assignment] = truth
                else:
                    # update the source that we synced
                    PollingEntry.objects(_id=assignment.entry_id).update_one(last_sync=datetime.now(timezone.utc))
                    self._logger.debug(
                        f"Successfully synced PollingEntry ID {assignment.entry_id} and found no changes.")
            except Exception as e:
                self._dead_assignments[assignment.entry_id] = 0
                self._logger.error(
                    f"Error encountered during sync with source of truth for assignment {str(assignment)}",
                    exc_info=True)
                self._polling_assignments.remove(assignment)
                self._logger.debug(f"{str(assignment)} successfully deleted from local polling_assignments")

        # refresh any detected stale polling assignments
        # most likely a user updated the Polling Entry and
        # we want to update the affected assignment
        for old_assignment, new_assignment in state_changed.items():
            # update the source that we synced, else add to dead pile
            try:
                PollingEntry.objects(_id=new_assignment.entry_id).update_one(last_sync=datetime.now(timezone.utc))
            except Exception as e:
                self._dead_assignments[new_assignment.entry_id] = 0
                self._logger.error(
                    f"Error encountered while attempting to incorporate PollingEntry change for {new_assignment.entry_id}, added to dead_assignments",
                    exc_info=True)
            else:
                self._polling_assignments.add(new_assignment)
                self._logger.warning(
                    f"Removed assignment {str(old_assignment)} and then added new assignment {str(new_assignment)}")
            finally:
                self._polling_assignments.remove(old_assignment)
                self._logger.info(f"Removed old assignment {old_assignment} as it was replaced with {new_assignment}")

        # loop through the dead pile to add back what we can, also
        # track & increment dead_assignments
        #
        # NOTE: currently we have no defined upper limit of cycles,
        # so they will just sit in the dead pile and the count will
        # accumulate, they will need to be manually removed. If this
        # becomes an issue then this is a STRONG candidate for
        # refactor!
        if self._dead_assignments:
            # since we alter _dead_assignments on the else clause, we
            # need to be looping over something else, so we assign the
            # values to dead_assignments and loop over that
            dead_assignments = [self._dead_assignments.keys()]
            self._logger.info(f"Checking local Dead PollingAssignments.")
            for entry_id in dead_assignments:
                try:
                    assignment = pe_to_pa(PollingEntry.objects(_id=entry_id).first())
                    self._polling_assignments.add(assignment)
                except Exception as e:
                    self._dead_assignments[entry_id] += 1
                    self._logger.error(
                        f"Error encountered while attempting to resync PollingEntry with ID {entry_id} this is error number {self._dead_assignments[entry_id]}",
                        exc_info=True)
                else:
                    self._logger.info(f"Successfull resync of PollingEntry ID {entry_id}")
                    self._logger.debug(f"Successfull resync of PollingEntry ID {entry_id} results in {str(assignment)}")
                    del self._dead_assignments[entry_id]
                    self._logger.debug(f"Successfully deleted the dead_assignment entry for PollingEntry ID {entry_id}")
