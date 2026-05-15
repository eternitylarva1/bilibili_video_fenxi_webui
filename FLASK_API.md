# Flask API 说明文档

## 基础信息

- **端口**: 30001
- **基路径**: `/api`
- **响应格式**: JSON
- **字符编码**: UTF-8

---

## API 端点

### 1. 获取爬虫配置
```
GET /api/config
```

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "keyword": "杀戮尖塔2",
    "order": "pubdate",
    "target_count": 100,
    "page_size": 30,
    "filter": {
      "within_24h": {
        "max_hours": 24,
        "min_play_per_hour": 2000
      },
      "beyond_24h": {
        "min_play_count": 20000
      }
    },
    "last_page": 172,
    "max_pages_per_run": 100,
    "request_interval": 0.5
  }
}
```

---

### 2. 更新爬虫配置
```
POST /api/config
```

**请求体**:
```json
{
  "keyword": "杀戮尖塔2",
  "target_count": 100,
  "filter": {
    "within_24h": {
      "min_play_per_hour": 2000
    },
    "beyond_24h": {
      "min_play_count": 20000
    }
  }
}
```

**响应示例**:
```json
{
  "code": 0,
  "message": "配置已更新"
}
```

---

### 3. 获取爬虫状态
```
GET /api/status
```

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "is_running": false,
    "current_page": 172,
    "total_videos": 52,
    "new_videos_this_run": 0,
    "last_run": "2026-05-13 23:31:38",
    "progress": 52
  }
}
```

---

### 4. 启动爬虫
```
POST /api/spider/start
```

**响应示例**:
```json
{
  "code": 0,
  "message": "爬虫已启动",
  "data": {
    "pid": 12345
  }
}
```

**错误响应** (爬虫已在运行时):
```json
{
  "code": 4001,
  "message": "爬虫已在运行中"
}
```

---

### 5. 停止爬虫
```
POST /api/spider/stop
```

**响应示例**:
```json
{
  "code": 0,
  "message": "爬虫已停止"
}
```

---

### 6. 获取爬取结果列表
```
GET /api/videos
```

**Query 参数**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页数量 |
| sort | string | "pubdate" | 排序字段 |
| order | string | "desc" | 排序方向 (asc/desc) |
| keyword | string | "" | 搜索关键词 |

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "videos": [
      {
        "title": "这才是真正的华丽收场的特效",
        "bvid": "BV12x5t6FEzD",
        "author": "青天零云",
        "play_count": 305890,
        "like_count": 12273,
        "pubdate": 1778509420,
        "pubdate_str": "2026-05-11 22:23:40",
        "duration": "0:20",
        "url": "https://www.bilibili.com/video/BV12x5t6FEzD",
        "filter_threshold": 305890,
        "filter_type": "total_play"
      }
    ],
    "total": 52,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  }
}
```

---

### 7. 获取单条视频详情
```
GET /api/videos/<bvid>
```

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "title": "这才是真正的华丽收场的特效",
    "bvid": "BV12x5t6FEzD",
    "author": "青天零云",
    "play_count": 305890,
    "like_count": 12273,
    "pubdate": 1778509420,
    "pubdate_str": "2026-05-11 22:23:40",
    "duration": "0:20",
    "url": "https://www.bilibili.com/video/BV12x5t6FEzD",
    "filter_threshold": 305890,
    "filter_type": "total_play"
  }
}
```

**错误响应**:
```json
{
  "code": 4004,
  "message": "视频不存在"
}
```

---

### 8. 获取运行日志
```
GET /api/logs
```

**Query 参数**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| lines | int | 100 | 返回行数 |
| tail | bool | true | 是否从末尾获取 |

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "logs": [
      "[23:31:38] 开始运行爬虫...",
      "[23:31:38] 已加载 52 条历史记录",
      "[23:31:38] 开始爬取，从第 172 页"
    ],
    "total_lines": 797
  }
}
```

---

### 9. 清除日志
```
POST /api/logs/clear
```

**响应示例**:
```json
{
  "code": 0,
  "message": "日志已清空"
}
```

---

### 10. 获取统计数据
```
GET /api/stats
```

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "total_videos": 52,
    "total_plays": 1245390,
    "total_likes": 68320,
    "avg_plays": 23950,
    "play_distribution": {
      "0-5k": 5,
      "5-10k": 8,
      "10-20k": 15,
      "20-50k": 12,
      "50-100k": 7,
      "100k+": 5
    },
    "duration_distribution": {
      "lt_1min": 18,
      "1_5min": 13,
      "5_15min": 12,
      "15_30min": 6,
      "gt_30min": 3
    },
    "time_distribution": {
      "today": 4,
      "yesterday": 8,
      "2_3days": 15,
      "3_7days": 20,
      "gt_7days": 5
    }
  }
}
```

---

### 11. 导出数据
```
GET /api/export
```

**响应**: 返回 `filtered_videos.json` 文件下载

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 4001 | 爬虫已在运行中 |
| 4002 | 爬虫未在运行 |
| 4003 | 配置更新失败 |
| 4004 | 资源不存在 |
| 5001 | 服务器内部错误 |

---

## Flask 路由示例

```python
from flask import Flask, jsonify, request, send_file
import subprocess
import threading
import os

app = Flask(__name__)

SPIDER_DIR = '/home/gaoming/UseAgentForDaily/bilibili_video_fenxi'
PORT = 30001

# 爬虫进程
spider_process = None

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取爬虫配置"""
    import yaml
    config_path = os.path.join(SPIDER_DIR, 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return jsonify({
        'code': 0,
        'data': config
    })

@app.route('/api/config', methods=['POST'])
def update_config():
    """更新爬虫配置"""
    import yaml
    config_path = os.path.join(SPIDER_DIR, 'config.yaml')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 更新配置
    data = request.get_json()
    if 'keyword' in data:
        config['keyword'] = data['keyword']
    if 'target_count' in data:
        config['target_count'] = data['target_count']
    if 'filter' in data:
        config['filter'] = data['filter']
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    return jsonify({'code': 0, 'message': '配置已更新'})

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取爬虫状态"""
    import yaml
    config_path = os.path.join(SPIDER_DIR, 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return jsonify({
        'code': 0,
        'data': {
            'is_running': spider_process is not None,
            'current_page': config.get('last_page', 1),
            'total_videos': 52,  # 需要从 filtered_videos.json 读取
            'last_run': config.get('last_run', ''),
            'progress': 52  # 需要计算
        }
    })

@app.route('/api/spider/start', methods=['POST'])
def start_spider():
    """启动爬虫"""
    global spider_process
    
    if spider_process is not None:
        return jsonify({'code': 4001, 'message': '爬虫已在运行中'})
    
    def run():
        global spider_process
        result = subprocess.run(
            ['bash', 'run_spider.sh'],
            cwd=SPIDER_DIR,
            capture_output=True,
            text=True
        )
        spider_process = None
    
    spider_process = subprocess.Popen(
        ['bash', 'run_spider.sh'],
        cwd=SPIDER_DIR
    )
    
    thread = threading.Thread(target=run)
    thread.start()
    
    return jsonify({
        'code': 0,
        'message': '爬虫已启动',
        'data': {'pid': spider_process.pid}
    })

@app.route('/api/spider/stop', methods=['POST'])
def stop_spider():
    """停止爬虫"""
    global spider_process
    
    if spider_process is None:
        return jsonify({'code': 4002, 'message': '爬虫未在运行'})
    
    spider_process.terminate()
    spider_process = None
    
    return jsonify({'code': 0, 'message': '爬虫已停止'})

@app.route('/api/videos', methods=['GET'])
def get_videos():
    """获取视频列表"""
    import json
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    
    videos_path = os.path.join(SPIDER_DIR, 'filtered_videos.json')
    with open(videos_path, 'r', encoding='utf-8') as f:
        videos = json.load(f)
    
    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    
    return jsonify({
        'code': 0,
        'data': {
            'videos': videos[start:end],
            'total': len(videos),
            'page': page,
            'page_size': page_size,
            'total_pages': (len(videos) + page_size - 1) // page_size
        }
    })

@app.route('/api/videos/<bvid>', methods=['GET'])
def get_video(bvid):
    """获取单个视频"""
    import json
    videos_path = os.path.join(SPIDER_DIR, 'filtered_videos.json')
    with open(videos_path, 'r', encoding='utf-8') as f:
        videos = json.load(f)
    
    video = next((v for v in videos if v['bvid'] == bvid), None)
    
    if video is None:
        return jsonify({'code': 4004, 'message': '视频不存在'})
    
    return jsonify({'code': 0, 'data': video})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取日志"""
    lines = int(request.args.get('lines', 100))
    
    log_path = os.path.join(SPIDER_DIR, 'spider.log')
    with open(log_path, 'r', encoding='utf-8') as f:
        all_logs = f.readlines()
    
    logs = all_logs[-lines:] if request.args.get('tail', 'true') == 'true' else all_logs[:lines]
    
    return jsonify({
        'code': 0,
        'data': {
            'logs': [l.strip() for l in logs],
            'total_lines': len(all_logs)
        }
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计数据"""
    import json
    import time
    
    videos_path = os.path.join(SPIDER_DIR, 'filtered_videos.json')
    with open(videos_path, 'r', encoding='utf-8') as f:
        videos = json.load(f)
    
    total_plays = sum(v['play_count'] for v in videos)
    total_likes = sum(v['like_count'] for v in videos)
    
    return jsonify({
        'code': 0,
        'data': {
            'total_videos': len(videos),
            'total_plays': total_plays,
            'total_likes': total_likes,
            'avg_plays': total_plays // len(videos) if videos else 0
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
```

---

## 启动方式

```bash
# 直接运行
python app.py

# 或使用 gunicorn
gunicorn -w 2 -b 0.0.0.0:30001 app:app
```

---

## 前端对接说明

前端通过 Fetch API 调用后端接口:

```javascript
// 获取配置
fetch('/api/config')
  .then(res => res.json())
  .then(data => {
    if (data.code === 0) {
      updateConfigUI(data.data);
    }
  });

// 启动爬虫
fetch('/api/spider/start', { method: 'POST' })
  .then(res => res.json())
  .then(data => {
    if (data.code === 0) {
      updateStatus('running');
    }
  });

// 获取视频列表 (轮询)
setInterval(() => {
  fetch('/api/videos?page=1&page_size=20')
    .then(res => res.json())
    .then(data => {
      if (data.code === 0) {
        updateVideosTable(data.data);
      }
    });
}, 5000);
```