
from mongoengine import Document, DateTimeField, ListField, DictField, EmbeddedDocument, EmbeddedDocumentField, connect
from mongoengine.fields import StringField, ObjectIdField

# Connect to MongoDB
connect(host='mongodb://localhost:27017/netbrain')


class LoginToken(Document):
    meta = {
        'collection': 'login_token'
    }
    token = StringField(required=True)
    datetime = DateTimeField(required=True)


class IncomingPayload(Document):
    meta = {
        'collection': 'incoming_payload'
    }
    devicename = StringField(required=True)
    objectname = StringField(required=True)
    ipaddress = StringField(required=True)
    cid = StringField(required=True)
    status = StringField(required=True)
    created_datetime = DateTimeField(required=True)


class Schedule(EmbeddedDocument):
    frequency = StringField(required=True)
    startTime = ListField(StringField(), required=True)


class DeviceScope(EmbeddedDocument):
    scopeType = StringField(required=True)
    scopes = ListField(StringField())
    ipaddress = StringField(required=True)


class Benchmark(EmbeddedDocument):
    taskName = StringField(required=True)
    startDate = StringField(required=True)
    schedule = EmbeddedDocumentField(Schedule, required=True)
    deviceScope = EmbeddedDocumentField(DeviceScope, required=True)
    cliCommands = ListField(StringField(), required=True)


class BenchmarkPayload(Document):
    meta = {
        'collection': 'benchmark_payload'
    }
    parent_id = ObjectIdField(required=True)
    benchmark_payload = EmbeddedDocumentField(Benchmark, required=True)
    status = StringField(required=True)
    created_datetime = DateTimeField(required=True)


class TaskLog(Document):
    meta = {
        'collection': 'task_log'
    }
    parent_id = ObjectIdField(required=True)
    task_name = StringField(required=True)
    ipaddress = StringField(required=True)
    content = StringField(required=True)
    status = StringField(required=True)
    created_datetime = DateTimeField(required=True)
