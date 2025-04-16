from .celery import app
from .detector_backend import DetectorBackend
from database import MongoDB

@app.task(bind=True)
def submit_detection(self, image_name, git_url, branch) -> (dict, Exception):
    global detectors
    database = MongoDB("mongodb://localhost:27018")
    # STATUS changes to pending
    database.start_the_task(self.request.id)
    # Initialize Detect Docker
    detector = DetectorBackend(image_name, self.request.id)
    # Get detect result from sync HTTP VERY SLOW
    detect_result, vul_file_cnt, vul_func_cnt, vul_cnt, error = detector.detect(git_url, branch)
    if error is None:
        # save result and set STATUS to FINISHED
        database.save_result(self.request.id, detect_result, vul_file_cnt, vul_func_cnt, vul_cnt)
    else:
        # save error and set STATUS to ERROR
        database.save_error(self.request.id, error)
