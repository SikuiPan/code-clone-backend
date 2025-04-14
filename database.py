from utils import *

from pymongo import MongoClient, ASCENDING

sample_structure = {
    "task_id": "abcdef-abcd-abcd-abcd-abcd",
    "status": STATUS_FINISHED,  #INTERGER
    "results": [
        {"target_file": "vul.c", "target_func": "vul_func", "cve": ["CVE-2001-1234", "CVE-2002-2345"]}
    ],
    "error": "errorMsg or empty str"
}

class MongoDB:
    def __init__(self, db_path = "mongodb://localhost:27017/"):
        # 连接数据库
        client = MongoClient(db_path)
        self.db = client.code_clone_detect
        self.db.code_clone_detect.create_index([("task_id", ASCENDING)])

    def create_task(self, task_id):
        self.db.result.insert_one({
            "task_id": task_id,
            "status": STATUS_CREATED,
            "results": [],
            "error": "",
        })

    def start_the_task(self, task_id):
        self.db.result.update_one({"task_id": task_id},
                                  {"$set": {"status": STATUS_PENDING}})

    def save_error(self, task_id, exception: Exception):
        self.db.result.update_one({"task_id": task_id},
                                  {"$set": {"status": STATUS_ERROR, "error": str(exception)}})

    def query_task_status(self, task_id):
        return self.db.result.find_one({"task_id": task_id}).get("status")

    def query_task_statistics(self, task_id):
        return self.db.result.aggregate([
            {"$match": {"task_id": task_id}},
            {"$project": {"result_cnt": {"$size": "$results"}}}
        ])

    def save_result(self, celery_uuid, results):
        self.db.result.update_one({"task_id": celery_uuid},
                           {"$set" : {"status": STATUS_FINISHED, "results": results}})

    def get_result(self, task_id, page, page_size):
        skip = (page - 1) * page_size
        return self.db.result.aggregate([
            {"$match": {"class_id": task_id}},  # 1. 筛选班级
            {"$unwind": "$results"},  # 2. 展开日志数组
            {"$replaceRoot": {"newRoot": "$results"}},  # 3. 将日志提升为根字段
            {"$skip": skip},  # 4. 跳过前N条
            {"$limit": page_size}  # 5. 限制返回数量
        ])