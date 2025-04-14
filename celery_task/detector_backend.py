import time
import traceback
import urllib.parse
from ipaddress import ip_address

import docker
import docker.errors
import requests

client = docker.from_env()

class DetectorBackend:
    network_name = "code-clone-backend_network"

    def __init__(self, image_name, uuid):

        try:
            self.container = client.containers.run(
                image = image_name,
                name = f"code_detector_{uuid}",
                detach = True,
                network = self.network_name,
                auto_remove = True,
            )
            # Get IP Address
            ip_address = None
            while not ip_address:
                self.container.reload()

                networks = self.container.attrs['NetworkSettings']['Networks']

                if self.network_name in networks:
                    ip_address = networks[self.network_name]['IPAddress']
                else:
                    time.sleep(1)
            # Waiting Flask Starts
            self.backend_url = f"http://{ip_address}:8000"
            for try_times in range(6):
                try:
                    response = requests.get(self.backend_url, timeout=5)
                    if response.status_code == 200:
                        print(f"Container Start at {self.backend_url}")
                        break
                    else:
                        print(f"Flask not started. Waiting {2**try_times} seconds before retrying ({try_times + 1}/ 6)")
                        time.sleep(2**try_times)
                except Exception as e:
                    print(f"Flask not started. Waiting {2 ** try_times} seconds before retrying ({try_times + 1}/ 6): {str(e)}")  # 重试间隔
                    time.sleep(2**try_times)
            else:
                raise RuntimeError(f"Cannot start the docker after 6 tries (127s)")

        except docker.errors.ImageNotFound:
            raise RuntimeError(f"Image {image_name} not found")
        except docker.errors.APIError as e:
            traceback.print_exc() # debug only
            raise RuntimeError(f"DockerAPI Failed, Please recheck")

    def __del__(self):
        self.container.stop()


    @staticmethod
    def old_new_funcs_to_cve(old_new_func_filename):
        return old_new_func_filename.split("_")[0]

    @staticmethod
    def get_target_func_and_filename(target_func_filename):
        split_filename = target_func_filename.split("@@@")
        func_name = split_filename[0]
        filename = split_filename[1]
        filename = filename.replace("@#@", "/")
        return func_name, filename

    def convert_vul_info(self, vul_info):
        info = {}
        vul_file_cnt = 0
        vul_funcs_cnt = 0
        vul_cnt = 0
        for target_func_path, old_new_funcs in vul_info.items():
            target_func = target_func_path.split("/")[-1]
            func_name, file_name = self.get_target_func_and_filename(target_func)
            for old_new_func_path in old_new_funcs:
                old_new_func = old_new_func_path.split("/")[-1]
                cve = self.old_new_funcs_to_cve(old_new_func)
                if file_name not in info:
                    info[file_name] = {}
                    vul_file_cnt += 1
                if func_name not in info[file_name]:
                    info[file_name][func_name] = []
                    vul_funcs_cnt += 1
                info[file_name][func_name].append(cve)
                vul_cnt += 1

        info_list = []
        for file_name in info.keys():
            for func_name in info[file_name].keys():
                for cve in info[file_name][func_name]:
                    info_list.append({"file_name": file_name, "func_name": func_name, "cve": cve})

        return info_list, vul_file_cnt, vul_funcs_cnt, vul_cnt

    def detect(self, target_git_url, branch="master") -> (dict, Exception):
        relative_url = "/process"
        params = {
            "git_url": target_git_url,
            "branch": branch,
        }
        url = urllib.parse.urljoin(self.backend_url, relative_url) + "?" + urllib.parse.urlencode(params)
        # timeout = 1h
        try:
            res = requests.get(url, timeout=3600)
        except Exception as e:
            return {}, e
        try:
            res_json = res.json()
            if res.status_code != 200:
                return {}, res_json.get("Error", "detector unknown error")
            vul_info = res_json["vul"]
            info, vul_file_cnt ,vul_funcs_cnt, vul_cnt = self.convert_vul_info(vul_info)
            return info, vul_file_cnt, vul_funcs_cnt, vul_cnt, None
        except Exception as e:
            return {}, e
