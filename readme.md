# 多语言检测后端网关

## Requirements

- Python 3.13
- MongoDB(Docker)
- Redis(Docker)

推荐将当前应用部署在docker外面，若部署到docker里面需要自行处理宿主机docker启动权限、数据库连接问题。

## Installation

### 前期准备

将所有的FIRE多语言image load到宿主机的image list里面

你收集的FIRE多语言镜像应为`.tar.gz`格式

```shell
gunzip -c docker load -i <fire_image>.tar.gz | docker load
```

获得所有已加载FIRE image列表

```shell
docker image list
```

将所有的docker image信息写入`run.py`。格式为`lang: image_name:tag`。请确保你在这里填入的lang信息和前端传入后端的lang信息保持一致。

```python
detectors = {
    "cpp": "FIRE/FIRE:cpp",
}
```

### Python 环境启动

创建Python venv环境并安装`requirements.txt`

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Docker 环境启动

> [!important]
> 请确保运行该后端的程序的用户具备docker的权限

安装docker-compose

REF: https://docs.docker.com/compose/install/linux/

启动`MongoDB`和`Redis`

```bash
docker compose up -d
```

留意输出，确保创建的网络名称和`celery_task/detector_backends`第`10`行的名称相同

```python
network = "code-clone-backend_network"
```

如果使用其他方法启动mongodb和redis，确保如下几个地方的url填写正确

- `run.py` 11行
- `celery_task/celery.py` 3-4行
- `celery_task/tasks` 8行

**注意！当前方法启动的mongodb数据库和redis数据库均没有设置密码，仅限开发过程使用。**

### Celery启动

注意这里只启动1个celery worker，不然服务器可能会扛不住。

```bash
celery -A celery_task worker --pool=solo --loglevel INFO
```

celery服务应该是不太能在后台跑的，这是前台服务，用`tmux`或者`screen`跑个后台就可以。

### Flask启动

Flask自带WSGI不太适用于生产环境，转到生产环境的时候请使用其他WSGI

启动flask

```bash
python3 run.py
```

flask也是前台服务，轻为它开个终端保活。

服务将在5000端口上开启，若占用请更改port。

### 停止

celery和flask直接`Ctrl+C`停止就行，celery停止需要一点时间所以请有耐心。

docker停止通过`docker compose down`即可

### 异常停止处理

异常停止时，检查containerlist是否有带`code_detector_`开头的名称容器。如果有请你将其停止，该容器会自动移除。