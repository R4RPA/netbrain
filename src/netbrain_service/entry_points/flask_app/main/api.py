import json

from flask import request, jsonify
from src.netbrain_service import logger
from src.netbrain_service.domain.common import get_cid
from src.netbrain_service.application.event_consumer import process_event


def incoming_payload():
    """Handle incoming request from stackstorm and send it to login_request"""
    temp_cid = get_cid()

    try:
        request_json = request.get_json(force=True, cache=False)
    except json.JSONDecodeError as jde:
        logger.warning(f"CID: {temp_cid} : JSONDecodeError: {str(jde)} :Request::Headers: { str(request.headers) } :Data: {str(request.get_data)}")
        return jsonify(400, f"Issue with the Request body. CID={temp_cid}")
    else:
        # inject CID if not provided in the Request body object
        if not request_json.get("cid"):
            request_json.update({"cid": temp_cid})
        logger.warning(f"CID: {temp_cid} : incoming payload: {str(request_json)}")
    # TODO convert the Request data into a DTO for easier field documentation & access

    # send payload to login request
    try:
        process_event(request_json)
    except Exception as e:
        logger.error(f"{temp_cid} Exception encountered while deserializing the Message body. request.data=\"{str(request.data)}\"", exc_info=True)
        return jsonify(500, f"CID={temp_cid} Error generated while deserializing the Message body provided.")
    return jsonify(200, "Success.")

