def login_to_netbrain(username: str, password: str):
    token = 'dummy_login_token'
    status = 'Success.'
    return {'status': status, 'token': token}


def logout_from_netbrain(token: str):
    return 'Success.'


def add_benchmark(token, benchmark_payload_dict):
    return 'Success.'


def check_task_status(token, task_name):
    return 'Success.'


def get_device_info(token, ipaddress):
    content = 'some random content to test'
    status = 'Success.'
    return {"status": status, 'content': content}


def delete_task(token, task_name):
    return 'Success.'
