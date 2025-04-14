from .celery import app
from .detector_backend import DetectorBackend
from database import MongoDB

@app.task(bind=True, ignore_result=True)
def submit_detection(self, lang, git_url, branch) -> (dict, Exception):
    global detectors
    database = MongoDB("/path/to/mongodb")
    # STATUS changes to pending
    database.start_the_task(self.request.id)
    # Initialize Detect Docker
    detector =  DetectorBackend(detectors.get(lang), self.request.id)
    # Get detect result from sync HTTP VERY SLOW
    detect_result, error = detector.detect(git_url, branch)
    if error is None:
        # save result and set STATUS to FINISHED
        database.save_result(self.request.id, detect_result)
    else:
        # save error and set STATUS to ERROR
        database.save_result(self.request.id, error)
