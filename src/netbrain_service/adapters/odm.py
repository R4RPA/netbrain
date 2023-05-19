from mongoengine import (
    Document
)

from datetime import (
    datetime,
    timezone,
)

"""
The purpose of this adapter is Object Document Mapping, or
mapping data objects to documents. Our current ODM is MongoEngine.
"""


class Sessions(Document):
    token = StringField(required=True)
    datetime = DateTimeField(required=True)


class ExternalMessageQueue(Document):
    pass
