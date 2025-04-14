import json

from flask import Flask, Blueprint, request

from celery_task import tasks
from database import MongoDB
from utils import *

code_detector = Blueprint('code_detector', __name__)
database_url = "http://path_to_database.db"

def error_message(exception: Exception, **kwargs) -> str:
    error_json = {
        "errorMessage": str(exception)
    }
    error_json.update(kwargs)
    return json.dumps(error_json)

@code_detector.post("/start")
def start_code_detection():
    # Params Parsing
    data = request.get_json()
    task_name = data["taskName"]            # NOT USED
    task_type = data["taskType"]            # NOT USED
    repository_url = data["repositoryUrl"]
    file_path = data["filePath"]            # NOT USED
    language = data["language"]
    config_params = data["configParams"]    # NOT USED
    branch = data["branch"]                 # SHOULD BE ADD

    # Creating Detecting Job
    try:
        task_id = tasks.submit_detection(lang=language, git_url=repository_url, branch = branch)
    except:
        return 500, error_message(CeleryTaskCreateFailed)

    # Registering Detecting Job
    try:
        database = MongoDB(database_url)
        database.create_task(task_id)
    except:
        return 500, error_message(DatabaseError)

    return 202, json.dumps({
        "taskId": task_id
    })

def get_status_code_msg(status):
    if status == STATUS_CREATED:
        status_code = 202
        status_msg = "Created"
    elif status == STATUS_PENDING:
        status_code = 202
        status_msg = "Pending"
    elif status == STATUS_FINISHED:
        status_code = 200
        status_msg = "Finished"
    elif status == STATUS_ERROR:
        status_code = 500
        status_msg = "Error"
    else:
        status_code = 500
        status_msg = "Unknown"
    return status_code, status_msg

@code_detector.post("/status")
def status():
    # Param Parsing
    data = request.get_json()
    task_id = data["taskID"]

    try:
        database = MongoDB(database_url)
        status, create_at, start_time, end_time, error = database.query_task_status(task_id)
    except TaskIdNotFound as e:
        return 404, error_message(e, task_id=task_id)
    except Exception as e:
        return 500, error_message(DatabaseError)    # internal error

    status_code, status_msg = get_status_code_msg(status)

    return status_code, json.dumps({
        "taskId": task_id,
        "status": status_msg,
        "createAt": create_at,
        "startTime": start_time,
        "endTime": end_time,
        "errorMessage": error,
    })

@code_detector.post("/statistics")
def statistics():
    # Params Parsing
    data = request.get_json()
    task_id = data["taskID"]

    # Load Stats
    try:
        database = MongoDB(database_url)
        vul_cnt = database.query_task_statistics(task_id)
    except TaskIdNotFound as e:
        return 404, error_message(e, task_id=task_id)
    except Exception as e:
        return 500, error_message(e)

    return 200, json.dumps({
        "taskId": task_id,
        "vul_cnt": vul_cnt,
    })


@code_detector.delete("/result/page")
def result():
    # Params Parsing
    data = request.get_json()
    task_id = data["taskID"]
    page_number = data["pageNumber"]
    page_size = data["pageSize"]
    statusFilter = data["statusFilter"] # NOT USED

    # Load Result
    try:
        database = MongoDB(database_url)
        total_pages, total_count, results = database.get_result(task_id, page_number, page_size)
    except TaskIdNotFound as e:
        return 404, error_message(e, task_id=task_id)
    except Exception as e:
        return 500, error_message(DatabaseError)

    return 200, json.dumps({
        "taskId": task_id,
        "pageNumber": page_number,
        "pageSize": page_size,
        "totalPages": total_pages,
        "totalCount": total_count,
        "results": results,
    })
app = Flask(__name__)
app.register_blueprint(code_detector, url_prefix="/api/v1/code-detection")