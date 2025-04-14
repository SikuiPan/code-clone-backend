# Status Code
STATUS_CREATED  = 1
STATUS_PENDING  = 2
STATUS_FINISHED = 3
STATUS_ERROR    = 4

# Exceptions
TaskIdNotFound          = Exception("task_id not found")
CeleryTaskCreateFailed  = Exception("celery task create failed")
DatabaseError           = Exception("database error")