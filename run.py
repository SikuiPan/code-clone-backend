import json
import traceback
from sys import exception

from flask import Flask, Blueprint, request

from celery_task import tasks
from database import MongoDB
from utils import *

code_detector = Blueprint('code_detector', __name__)
database_url = "mongodb://localhost:27017"

detectors = {
    "cpp": "fire/fire:v1.3.0",
}

def error_message(exception: Exception, **kwargs) -> str:
    error_json = {
        "errorMessage": str(exception)
    }
    error_json.update(kwargs)
    return json.dumps(error_json)

@code_detector.get("/ping")
def ping():
    return "Code Clone Backend Starts", 200

@code_detector.post("/start")
def start_code_detection():
    # Params Parsing
    data = request.get_json()
    task_name = data.get("taskName","")            # NOT USED
    task_type = data.get("taskType","")            # NOT USED
    repository_url = data.get("repositoryUrl","")
    file_path = data.get("filePath", "")            # NOT USED
    language = data.get("language", "")
    config_params = data.get("configParams", "")    # NOT USED
    branch = data.get("branch", "")                 # SHOULD BE ADD

    # TODO: 参数Validate

    # Load Image name
    if language not in detectors:
        return error_message(LangNotSupported), 404
    detector_image = detectors[language]

    # Creating Detecting Job
    try:
        task = tasks.submit_detection.delay(image_name = detector_image, git_url=repository_url, branch = branch)
    except Exception as e:
        traceback.print_exc()   # debug only
        return error_message(e), 500

    # Registering Detecting Job
    try:
        database = MongoDB(database_url)
        database.create_task(task.id)
    except Exception as e:
        return error_message(DatabaseError), 500

    return json.dumps({
        "taskId": task.id
    }), 202

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
    task_id = data.get("taskId", "")

    # TODO: 参数Validate

    try:
        database = MongoDB(database_url)
        status, create_at, start_time, end_time, error = database.query_task_status(task_id)
    except FileNotFoundError as e:
        return error_message(e, task_id=task_id), 404
    except Exception as e:
        return error_message(DatabaseError), 500    # internal error

    status_code, status_msg = get_status_code_msg(status)

    return json.dumps({
        "taskId": task_id,
        "status": status_msg,
        "createAt": create_at,
        "startTime": start_time,
        "endTime": end_time,
        "errorMessage": error,
    }), status_code

@code_detector.post("/statistics")
def statistics():
    # Params Parsing
    data = request.get_json()
    task_id = data.get("taskId", "")

    # TODO: 参数Validate

    # Load Stats
    try:
        database = MongoDB(database_url)
        vul_cnt, vul_func_cnt, vul_file_cnt = database.query_task_statistics(task_id)
    except FileNotFoundError as e:
        return error_message(e, task_id=task_id), 404
    except NotImplementedError as e:
        return error_message(e, task_id=task_id), 400
    except Exception as e:
        return error_message(e), 500

    return json.dumps({
        "taskId": task_id,
        "vul_cnt": vul_cnt,
        "vul_func_cnt": vul_func_cnt,
        "vul_file_cnt": vul_file_cnt,
    }), 200


@code_detector.post("/result/page")
def result():
    # Params Parsing
    data = request.get_json()
    task_id = data.get("taskId", "")
    page_number = data.get("pageNumber", "")
    page_size = data.get("pageSize", "")
    statusFilter = data.get("statusFilter", "") # NOT USED

    # TODO: 参数Validate

    # Load Result
    try:
        database = MongoDB(database_url)
        total_pages, total_count, results = database.get_result(task_id, page_number, page_size)
    except FileNotFoundError as e:
        return error_message(e, task_id=task_id), 404
    except NotImplementedError as e:
        return error_message(e, task_id=task_id), 400
    except Exception as e:
        return error_message(DatabaseError), 500

    return json.dumps({
        "taskId": task_id,
        "pageNumber": page_number,
        "pageSize": page_size,
        "totalPages": total_pages,
        "totalCount": total_count,
        "results": results,
    }), 200
app = Flask(__name__)
app.register_blueprint(code_detector, url_prefix="/api/v1/code-detection")

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)