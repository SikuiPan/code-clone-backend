import urllib.parse

import docker
import docker.errors
import requests

client = docker.from_env()

class DetectorBackend:

    def __init__(self, image_name, uuid):
        try:
            self.container = client.containers.run(
                image = image_name,
                name = f"code_detector_{uuid}",
                detach = True,
                network = "code_detector_network",
                auto_remove = True,
            )
            ip_address = self.container.attrs['NetworkSettings']['Networks']['code_detector_network']['IPAddress']

            self.backend_url = f"http://{ip_address}:8000"

        except docker.errors.ImageNotFound:
            raise RuntimeError(f"Image {image_name} not found")
        except docker.errors.APIError:
            raise RuntimeError(f"DockerAPI Failed, Please recheck")

    def __del__(self):
        self.container.stop()


    @staticmethod
    def old_new_funcs_to_cve(old_new_func_filename):
        return old_new_func_filename.split("_")[0]

    @staticmethod
    def get_target_func_and_filename(target_func_filename):
        split_filename = target_func_filename.split("@#@")
        func_name = split_filename[0]
        filename = split_filename[1]
        return func_name, filename

    def convert_vul_info(self, vul_info):
        info = {}
        for target_func, old_new_func in vul_info.items():
            func_name, file_name = self.get_target_func_and_filename(target_func)
            cve = self.old_new_funcs_to_cve(old_new_func)
            if file_name not in info:
                info[file_name] = {}
            if func_name not in info[file_name]:
                info[file_name][func_name] = []
            info[file_name][func_name].append(cve)
        return info

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
            return self.convert_vul_info(vul_info), None
        except Exception as e:
            return {}, e
