import logging

from datetime import datetime

from src.netbrain_service.application.mongo_models import LoginToken
from src.netbrain_service.application.mongo_models import BenchmarkPayload, Benchmark, Schedule, DeviceScope
from src.netbrain_service.application.mongo_models import IncomingPayload
from src.netbrain_service.application.mongo_models import TaskLog

#from src.netbrain_service.application import requests_consumer

""" in case API is unavailable - use requests_consumer_dummy: 
    below is a dummy request module only to do basic functionality testing"""
import src.netbrain_service.application.requests_consumer_dummy as requests_consumer

logger = logging.getLogger(__name__)


def generate_login_token(username, password):
    """
        function to Generate Login Token
        first check if token exists, else get new token
    """
    try:
        token_entry = LoginToken.objects().first()
        if not token_entry:
            """Login to netbrain and get token"""
            result = requests_consumer.login_to_netbrain(username, password)
            if result['status'] == 'Success.':
                login_token = LoginToken(token=result['token'], datetime=datetime.utcnow())
                login_token.save()
                token_doc = login_token.to_mongo().to_dict()
                logger.info(f"generate_login_token > login status: {str(result)}")
                logger.info(f"generate_login_token > token added: {str(token_doc)}")
                status = 'Success.'
            else:
                status = result['status']
                logger.error(f"generate_login_token > login status: {str(result)}")
        else:
            logger.info(f"generate_login_token > login status: token exists")
            status = 'Success.'
    except Exception as e:
        status = 'login failed'
        logger.error(f"generate_login_token > Error: '{str(e)}'")
    return status


def get_login_token():
    """function to get login token - to be used in-process functions"""
    token_entry = LoginToken.objects().first()
    if token_entry:
        token = token_entry.token
    else:
        token = ''
        logger.error(f"get_login_token > no token exists")
    return token


def logout_api():
    try:
        """function to log out from netbrain"""
        token = get_login_token()
        if token != '':
            status = requests_consumer.logout_from_netbrain(token)
            if status == 'Success.':
                """Delete the token entry from the login_token collection"""
                login_token = LoginToken.objects(token=token).first()
                token_doc = login_token.to_mongo().to_dict()
                login_token.delete()
                logger.info(f"logout_api > token deleted: {str(token_doc)}")
                logger.info(f"logout_api > logout status: {status}")
            else:
                logger.error(f"logout_api > logout status:{status}")
        else:
            status = 'No active token found'
            logger.error(f"logout_api > logout status: {status}")
    except Exception as e:
        status = 'logout failed'
        logger.error(f"logout_api > Error: '{str(e)}'")
    return status


def create_event_entry(payload):
    """Log incoming payload in DB"""
    try:
        devicename = payload['devicename']
        ipaddress = payload['ipaddress']
        objectname = payload['objectname']
        cid = payload['cid']
        logger.info(f"create_event_entry > payload: {str(payload)}")
        incoming_payload = IncomingPayload(devicename=devicename,
                                           ipaddress=ipaddress,
                                           objectname=objectname,
                                           cid=str(cid),
                                           status='NEW',
                                           created_datetime=datetime.utcnow())
        incoming_payload.save()
        payload_doc = incoming_payload.to_mongo().to_dict()
        logger.info(f"create_event_entry > document: {str(payload_doc)}")
        status = 'Success.'
    except Exception as e:
        status = f"create_event_entry failed. Error: {str(e)}"
        logger.error(f"create_event_entry > status: {str(status)}")
    return status


def get_device_name(device):
    """dummy device mapping, needs to be updated based on incoming payload params"""
    device_mapp = {'SAP1': 'My Network/USA/TEXAS/Westlake/Westlake Lab/ADRMTXAA7',
                   'NEC1': 'My Network/USA/TEXAS/Westlake/Westlake Lab/ICRSTXAA',
                   'NEC2': 'My Network/USA/TEXAS/Westlake/Westlake Lab/MRCRYTX'}

    if device in device_mapp:
        return device_mapp[device]
    else:
        return 'Invalid device'


def translate_incoming_payload_to_benchmark_payload():
    """Check if there are any new payloads received, and log them as benchmark payload"""
    logger.info(f"translate_incoming_payload_to_benchmark_payload > start")
    new_payloads = IncomingPayload.objects(status='NEW')
    for payload in new_payloads:
        device = payload.devicename
        ipaddress = payload.ipaddress
        payload_id = payload.id
        try:
            """translate incoming payload to benchmark payload"""
            entry_count = BenchmarkPayload.objects().count()
            task_name = f"Benchmark_event_{entry_count + 1}"
            device_name = get_device_name(device)
            start_date = datetime.utcnow().strftime('%Y-%m-%d')
            start_time = datetime.utcnow().strftime('%H:%M:%S')
            new_payload = Benchmark(
                taskName=task_name,
                startDate=start_date,
                schedule=Schedule(frequency="once", startTime=[start_time]),
                deviceScope=DeviceScope(scopeType="site", scopes=[device_name], ipaddress=ipaddress),
                cliCommands=["showversion", "showarp", "showinterface"]
            )

            """log benchmark payload"""
            benchmark_payload_entry = BenchmarkPayload(
                parent_id=payload_id,
                benchmark_payload=new_payload,
                status='NEW',
                created_datetime=datetime.utcnow()
            )
            benchmark_payload_entry.save()
            benchmark = benchmark_payload_entry.to_mongo().to_dict()
            logger.info(f"translate_incoming_payload_to_benchmark_payload > {str(benchmark)}")
            """set incoming payload status to completed"""
            payload.status = 'COMPLETED'
            payload.save()
        except Exception as e:
            logger.error(f"translate_incoming_payload_to_benchmark_payload > Error: '{str(e)}'")
    logger.info(f"translate_incoming_payload_to_benchmark_payload > end")


def check_and_add_benchmark():
    """Check if there are any new bechnmark payload to be added"""
    new_benchmark_payloads = BenchmarkPayload.objects(status='NEW')
    for new_benchmark_payload in new_benchmark_payloads:
        benchmark_payload = new_benchmark_payload.benchmark_payload
        benchmark_payload_dict = benchmark_payload.to_mongo().to_dict()
        benchmark_payload_id = new_benchmark_payload.id
        try:
            logger.info(f"check_and_add_benchmark > {str(benchmark_payload_dict)}")
            status = add_benchmark(benchmark_payload_dict)
            if status == 'Success.':
                """set benchmark payload status to completed"""
                new_benchmark_payload.status = 'COMPLETED'
                new_benchmark_payload.save()

                logger.info(f"check_and_add_benchmark > statu: {str(status)}")

                """log taskname and ipaddress in task log"""
                task_name = benchmark_payload['taskName']
                ipaddress = benchmark_payload['deviceScope']['ipaddress']
                task_log = TaskLog(parent_id=benchmark_payload_id,
                                   task_name=task_name,
                                   ipaddress=ipaddress,
                                   content='',
                                   status='NEW',
                                   created_datetime=datetime.utcnow())
                task_log.save()
                task_log_dict = task_log.to_mongo().to_dict()
                logger.info(f"check_and_add_benchmark > create task log : {str(task_log_dict)}")
            else:
                logger.error(f"check_and_add_benchmark > status: {str(status)}")
        except Exception as e:
            logger.error(f"check_and_add_benchmark > Error: '{str(e)}'")


def add_benchmark(benchmark_payload_dict):
    """add benchmark"""
    token = get_login_token()
    if token == '':
        return "Error: No token found"
    return requests_consumer.add_benchmark(token, benchmark_payload_dict)


def get_benchmark_status():
    """Check if there are any new task logs"""
    task_logs = TaskLog.objects(status='NEW')
    for task_log in task_logs:
        task_name = task_log.task_name
        try:
            logger.info(f"get_benchmark_status > task name: '{str(task_name)}'")
            """get benchmark status for the given task name"""
            status = check_task_status(task_name)
            if status == 'Success.':
                task_log.status = 'GET_DEVICE_INFO'
                task_log.save()
                logger.info(f"get_benchmark_status > task status: '{str(status)}'")
            else:
                logger.error(f"get_benchmark_status > task status: '{str(status)}'")
        except Exception as e:
            logger.error(f"get_benchmark_status > Error: '{str(e)}'")


def check_task_status(task_name):
    """get benchmark status by task name"""
    token = get_login_token()
    if token == '':
        return "Error: No token found"
    return requests_consumer.check_task_status(token, task_name)


def get_device_info():
    """Check if there are any new task with status as get device info"""
    task_logs = TaskLog.objects(status='GET_DEVICE_INFO')
    for task_log in task_logs:
        ipaddress = task_log.ipaddress
        try:
            logger.info(f"get_device_info > ipaddress: '{str(ipaddress)}'")
            """get device info for the given ip address"""
            result = check_device_info(ipaddress)
            if result['status'] == 'Success.':
                task_log.content = str(result['content'])
                task_log.status = 'PROCESS_CONTENT'
                task_log.save()
                logger.info(f"get_device_info > result: '{str(result)}'")
            else:
                logger.error(f"get_device_info > result: '{str(result)}'")
        except Exception as e:
            logger.error(f"get_device_info > Error: '{str(e)}'")


def check_device_info(ipaddress):
    """get devise info by ip address"""
    token = get_login_token()
    if token == '':
        return {'status': "Error: No token found", 'content': ''}
    return requests_consumer.get_device_info(token, ipaddress)


def process_device_content():
    """Check if there are any new task with status as process content"""
    task_logs = TaskLog.objects(status='PROCESS_CONTENT')
    for task_log in task_logs:
        content = task_log.content
        try:
            logger.info(f"process_device_content > content: '{str(content)}'")
            """get device info for the given ip address"""
            status = next_process_with_device_content(content)
            if status == 'Success.':
                task_log.status = 'DELETE_TASK'
                task_log.save()
                logger.info(f"process_device_content > status: '{str(status)}'")
            else:
                logger.error(f"process_device_content > status: '{str(status)}'")
        except Exception as e:
            logger.error(f"process_device_content > Error: '{str(e)}'")


def next_process_with_device_content(content):
    """dummy function: placeholder to process device content"""
    return 'Success.'


def delete_benchmark():
    """Check if there are any new task with status as delete task"""
    task_logs = TaskLog.objects(status='DELETE_TASK')
    for task_log in task_logs:
        task_name = task_log.task_name
        try:
            logger.info(f"delete_benchmark > task_name: '{str(task_name)}'")
            """get benchmark status for the given task name"""
            status = delete_task(task_name)
            if status == 'Success.':
                task_log.status = 'COMPLETED'
                task_log.save()
                logger.info(f"delete_benchmark > status: '{str(status)}'")
            else:
                logger.error(f"delete_benchmark > status: '{str(status)}'")
        except Exception as e:
            logger.error(f"delete_benchmark > Error: '{str(e)}'")


def delete_task(task_name):
    """delete benchmark / task"""
    token = get_login_token()
    if token == '':
        return "Error: No token found"

    return requests_consumer.delete_task(token, task_name)
