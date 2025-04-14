# Status Code
STATUS_CREATED  = 1
STATUS_PENDING  = 2
STATUS_FINISHED = 3
STATUS_ERROR    = 4

# Exceptions
TaskIdNotFound          = FileNotFoundError("task_id not found")
CeleryTaskCreateFailed  = RuntimeError("celery task create failed")
DatabaseError           = RuntimeError("database error")
LangNotSupported        = NotImplementedError("language not supported")
NotFinished             = NotImplementedError("detect is not finished or have errors")