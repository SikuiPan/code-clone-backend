from datetime import datetime
import pytz  # 使用 pytz 替代 zoneinfo

from utils import *

from pymongo import MongoClient, ASCENDING
import math

sample_structure = {
    "task_id": "abcdef-abcd-abcd-abcd-abcd",
    "status": STATUS_FINISHED,  # INTERGER
    "results": [
        {"target_file": "vul.c", "target_func": "vul_func", "cve": ["CVE-2001-1234", "CVE-2002-2345"]}
    ],
    "error": "errorMsg or empty str"
}

class MongoDB:
    def __init__(self, db_path="mongodb://localhost:27018/"):
        # 连接数据库
        client = MongoClient(db_path)
        self.db = client.code_clone_detect
        self.db.code_clone_detect.create_index([("task_id", ASCENDING)])

    def create_task(self, task_id):
        self.db.result.insert_one({
            "task_id": task_id,
            "status": STATUS_CREATED,
            "create_at": datetime.now(pytz.utc),  # 使用 pytz.utc 替代 timezone.utc

            "results": [],
            "error": "",
        })

    def start_the_task(self, task_id):
        self.db.result.update_one({"task_id": task_id},
                                  {"$set": {"status": STATUS_PENDING, "start_time": datetime.now(pytz.utc)}})

    def save_error(self, task_id, exception: Exception):
        self.db.result.update_one({"task_id": task_id},
                                  {"$set": {"status": STATUS_ERROR, "error": str(exception), "end_time": datetime.now(pytz.utc)}})

    @staticmethod
    def convert_time(time_obj):
        if time_obj is None:
            return None
        tz = pytz.timezone("Asia/Shanghai")  # 使用 pytz.timezone 替代 ZoneInfo
        return time_obj.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")

    def query_task_status(self, task_id):
        result = self.db.result.find_one({"task_id": task_id})
        if result is None:
            raise TaskIdNotFound
        status = result.get("status")
        create_at = self.convert_time(result.get("create_at"))
        start_time = self.convert_time(result.get("start_time"))
        end_time = self.convert_time(result.get("end_time"))
        error = result.get("error")

        return status, create_at, start_time, end_time, error

    def query_task_statistics(self, task_id):
        result = self.db.result.find_one({"task_id": task_id})
        if result is None:
            raise TaskIdNotFound
        status = result.get("status")
        if status != STATUS_FINISHED:
            raise NotFinished
        vul_cnt = result.get("vul_cnt")
        vul_func_cnt = result.get("vul_func_cnt")
        vul_file_cnt = result.get("vul_file_cnt")

        return vul_cnt, vul_func_cnt, vul_file_cnt

    def save_result(self, celery_uuid, results, vul_file_cnt, vul_func_cnt, vul_cnt):
        self.db.result.update_one({"task_id": celery_uuid},
                                  {"$set": {"status": STATUS_FINISHED, "results": results, "end_time": datetime.now(pytz.utc),
                                            "vul_file_cnt": vul_file_cnt, "vul_func_cnt": vul_func_cnt, "vul_cnt": vul_cnt}})

    def get_result(self, task_id, page, page_size):
        vul_cnt, _, _ = self.query_task_statistics(task_id)
        skip = (page - 1) * page_size
        total_page = int(math.ceil(vul_cnt / page_size))
        results = list(self.db.result.aggregate([
            {"$match": {"task_id": task_id}},  # 1. 筛选班级
            {"$unwind": "$results"},  # 2. 展开日志数组
            {"$replaceRoot": {"newRoot": "$results"}},  # 3. 将日志提升为根字段
            {"$skip": skip},  # 4. 跳过前N条
            {"$limit": page_size}  # 5. 限制返回数量
        ]))
        return total_page, vul_cnt, results