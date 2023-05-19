import requests


def login_to_netbrain(username: str, password: str):
    url = "http://10.139.225.12/ServicesAPI/API/V1/Session"

    headers = {"Content-Type": "application/json"}

    data = {
        "username": username,
        "password": password
    }
    token = ''
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            try:
                response_json = response.json()
                token = response_json["token"]
                status = 'Success.'
            except KeyError:
                status = f"Login successful, but token not found in response."
            except Exception as e:
                status = f"Login failed. Error: {str(e)}"
        else:
            status = f"Login failed. Status code: {response.status_code}, Message: {response.text}"
    except Exception as e:
        status = f"Login failed. Error: {str(e)}"

    result = {'status': status, 'token': token}
    return result


def logout_from_netbrain(token: str):
    url = "http://10.139.225.12/v1/session"

    headers = {
        "Content-Type": "application/json",
        "Token": token
    }
    try:
        response = requests.delete(url, headers=headers)

        if response.status_code == 200:
            status = 'Success.'
        else:
            status = f"Logout failed. Status code: {response.status_code}, Message: {response.text}"
    except Exception as e:
        status = f"Logout failed. Error: {str(e)}"

    return status


def add_benchmark(token, benchmark_payload_dict):
    url = "http://10.139.225.12/ServicesAPI/API/V1/CMDB/Benchmark/Tasks"

    headers = {
        "Content-Type": "application/json",
        "token": token
    }

    response = requests.post(url, headers=headers, json=benchmark_payload_dict)

    if response.status_code == 200:
        try:
            response_json = response.json()
            status = response_json["statusDescription"]  # expecting 'Success.' as response
        except KeyError:
            """assuming add benchmark is successful, but statusDescription not found in response."""
            status = 'Success.'
        except Exception as e:
            """capture if any other error"""
            status = f"Failed to add benchmark task. Error: {str(e)}"
    else:
        status = f"Failed to add benchmark task. Status code: {response.status_code}, Message: {response.text}"

    return status


def check_task_status(token, task_name):
    url = f"http://10.139.225.12/ServicesAPI/API/V1/CMDB/Benchmark/Tasks/{task_name}/Status"

    headers = {
        "Content-Type": "application/json",
        "token": token
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        try:
            response_json = response.json()
            status = response_json["statusDescription"]  # expecting 'Success.' as response
        except Exception as e:
            """capture if any other error"""
            status = f"Failed to get benchmark task status. Error: {str(e)}"
    else:
        status = f"Failed to get benchmark task status. Status code: {response.status_code}, Message: {response.text}"

    return status


def get_device_info(token, ipaddress):
    url = f"http://10.139.225.12/ServicesAPI/API/V1/CMDB/Devices/DeviceRawData"

    headers = {
        "Content-Type": "application/json",
        "token": token
    }

    query_params = {
        "IP": ipaddress,
        "dataType": "2",
        "cmd": "sh controllers tenGigE0/0/0/0  phy"
    }

    response = requests.get(url, headers=headers, params=query_params)
    content = ''
    if response.status_code == 200:
        try:
            response_json = response.json()
            content = response_json["content"]
            status = 'Success.'
        except Exception as e:
            """capture if any other error"""
            status = f"Failed to get benchmark task status. Error: {str(e)}"
    else:
        status = f"Failed to get device data. Status code: {response.status_code}, Message: {response.text}"

    return {"status": status, 'content': content}


def delete_task(token, task_name):
    url = f"http://10.139.225.12/ServicesAPI/API/V1/CMDB/Benchmark/Tasks/{task_name}"

    headers = {
        "Content-Type": "application/json",
        "token": token
    }

    response = requests.delete(url, headers=headers)

    if response.status_code == 200:
        try:
            response_json = response.json()
            status = response_json["statusDescription"]  # expecting 'Success.' as response
        except Exception as e:
            """capture if any other error"""
            status = f"Failed to get benchmark task status. Error: {str(e)}"
    else:
        status = f"Failed to get benchmark task. Status code: {response.status_code}, Message: {response.text}"

    return status
