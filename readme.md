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

如果接口被占用请更换`docker-compose.yml`中`port`字段**冒号前面**的端口，换一个没人用的端口。不要改冒号后面的端口。更改完端口之后搜索全文，将整个项目中原有使用端口改成新的修改后的端口。

留意输出，确保创建的网络名称和`celery_task/detector_backends`第`10`行的名称相同

```python
network = "code-clone-backend_network"
```

如果使用其他方法启动mongodb和redis，确保如下几个地方的url填写正确

- `run.py` 11行
- `celery_task/celery.py` 3-4行
- `celery_task/tasks` 8行

**注意！当前方法启动的mongodb数据库和redis数据库均没有设置密码，仅限开发过程使用。**

**注意！当前方法启动的两个数据库的数据都没有持久化，仅供开发过程使用，正式上线请修改compose文件将两个数据库持久化。**

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

异常停止时，检查container list是否有带`code_detector_`开头的名称容器。如果有请你将其停止，该容器会自动移除。

```bash
docker container list -a | grep code_detector
```

## 存储结构和Exception

MongoDB存储结构可参考`database.py`文件中的sample_structure。关于status字段的信息参考`utils.py`文件。如有需要请自行增加`STATUS`

如果有需要查阅Exception信息或者新增Exception，请在`utils.py`内更改或增加

## API文档

请求示例参见`test.http`文档

### 发起代码检测任务接口

用于发起代码检测任务，支持上传文件类型（Git仓库或文件）。

- `POST` /api/v1/code-detection/start
- Accept: application/json
- Content-Type: application/json

#### 请求参数

| 参数名           | 类型     | 必填  | 描述           |
|---------------|--------|-----|--------------|
| repositoryUrl | string | Yes | Git存储库       |
| language      | string | Yes | 编程语言（见下方注释）  |
| branch        | string | Yes | Git存储库分支/Tag |

其中，language的取值为：

- C/C++语言： `cpp`
- 待补充

```json
{
  "repositoryUrl": "https://github.com/openmvg/openmvg",
  "language": "cpp",
  "branch": "v1.6"
}
```

#### 返回参数

- 状态码：`202`

| 参数名    | 类型     | 描述       |
|--------|--------|----------|
| taskId | string | 任务Id（唯一） |

```json
{
  "taskId": "a39b3e25-97d7-41c9-b456-9c35c945d13f"
}
```

### 获取检测任务状态接口

用于发起代码检测任务，支持上传文件类型（Git仓库或文件）。

- `POST` /api/v1/code-detection/status
- Accept: application/json
- Content-Type: application/json

#### 请求参数

| 参数名    | 类型     | 必填  | 描述   |
|--------|--------|-----|------|
| taskId | string | Yes | 任务Id |

```json
{
  "taskId": "a39b3e25-97d7-41c9-b456-9c35c945d13f"
}
```

#### 返回参数

- 状态码： 状态为`Created`, `Pending`时为`202`，为`Finished`时为`200`，为`Error`, `Unknown`时为`500`

| 参数名          | 类型          | 描述                    |
|--------------|-------------|-----------------------|
| taskId       | string      | 任务Id（唯一）              |
| status       | string      | 状态信息                  |
| createAt     | string      | 任务创建时间                |
| startTime    | string/None | 任务开始时间（未开始则为None）     |
| endTime      | string/None | 任务结束时间（未开始或出现错误为None） |
| errorMessage | string | 错误信息（无错误则为空字符串）       |

```json
{
  "taskId": "a39b3e25-97d7-41c9-b456-9c35c945d13f",
  "status": "Pending", 
  "createAt": "2025-04-17 13:06:11", 
  "startTime": "2025-04-17 13:06:11", 
  "endTime": null, 
  "errorMessage": ""
}
```

### 获取检测结果统计接口

获取检测任务的统计结果，包括成功、失败的代码检测数量等。

请在status为`Finished`的情况下调用这个结果，否则将会报出“检测未完成或出错”的错误。

- `POST` /api/v1/code-detection/results/statistics
- Accept: application/json
- Content-Type: application/json

#### 请求参数

| 参数名    | 类型     | 必填  | 描述   |
|--------|--------|-----|------|
| taskId | string | Yes | 任务Id |

```json
{
  "taskId": "a39b3e25-97d7-41c9-b456-9c35c945d13f"
}
```

#### 返回参数

- 状态码： `200`

| 参数名          | 类型          | 描述                    |
|--------------|-------------|-----------------------|
| taskId       | string      | 任务Id（唯一）              |
| vulCnt       | integer     | 检测出的漏洞总数              |
| vulFuncCnt   | integer     | 含有漏洞的函数总数             |
| vulFileCnt   | integer     | 含有漏洞的文件总数             |

一个检出的漏洞对视为一个漏洞，若一个函数和多个cve对应，那么计多个`vulCnt`

```json
{
  "taskId": "a39b3e25-97d7-41c9-b456-9c35c945d13f",
  "vulCnt": 42, 
  "vulFuncCnt": 29, 
  "vulFileCnt": 12
 }
```

### 检测结果分页查询接口

分页查询指定任务的检测结果，支持按检测状态筛选。

请在status为`Finished`的情况下调用这个结果，否则将会报出“检测未完成或出错”的错误。

- `POST` /api/v1/code-detection/results/page
- Accept: application/json
- Content-Type: application/json

#### 请求参数

| 参数名        | 类型      | 必填  | 描述      |
|------------|---------|-----|---------|
| taskId     | string  | Yes | 任务Id    |
| pageNumber | integer | Yes | 页码，从1开始 |
| pageSize   | integer | Yes | 每页数量    |

```json
{
  "taskId": "a39b3e25-97d7-41c9-b456-9c35c945d13f",
  "pageNumber": 1,
  "pageSize": 5
}
```

#### 返回参数

- 状态码： `200`

| 参数名        | 类型           | 描述       |
|------------|--------------|----------|
| taskId     | string       | 任务Id（唯一） |
| pageNumber | integer      | 页号数      |
| pageSize   | integer      | 单页大小     |
| totalPage  | integer      | 总页数      |
| totalCount | integer      | 总记录数     |
| results    | list[object] | 检测结果     |

`results` 检测结果的一条结果的结构如下：

| 参数名      | 类型     | 描述      |
|----------|--------|---------|
| fileName | string | 含漏洞的文件名 |
| funcName | string | 含漏洞的函数名 |
| cve      | string | cve号    |

`results` 字段已删除部分结果

```json
{
  "taskId": "a39b3e25-97d7-41c9-b456-9c35c945d13f", 
  "pageNumber": 1, 
  "pageSize": 5, 
  "totalPages": 9, 
  "totalCount": 42, 
  "results": [
    {
      "fileName": "src/third_party/png/pngset.c", 
      "funcName": "png_set_IHDR", 
      "cve": "CVE-2015-0973"
    }
  ]
}
```

### 错误情况下返回结构

- 状态码：`400`,`404`,`500`

| 参数名          | 类型           | 描述  |
|--------------|--------------|-----|
| errorMessage | string       | 错误信息 |
| taskId       | string | 引发错误的taskId（optional） |

```json
{
  "errorMessage": "task_id not found",
  "taskId": "929275e4-3266-4947-a06d-83aec162bae1"
}
```