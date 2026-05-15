"""
B站视频爬虫 WebUI - Flask 后端服务
端口: 30001
"""

from flask import Flask, jsonify, request, send_file
import subprocess
import threading
import os
import json
import time
import yaml
from datetime import datetime

app = Flask(__name__)

# 配置路径
SPIDER_DIR = '/home/gaoming/UseAgentForDaily/bilibili_video_fenxi'
OUTPUT_FILE = 'filtered_videos.json'
CONFIG_FILE = 'config.yaml'
LOG_FILE = 'spider.log'

# 爬虫进程
spider_process = None
spider_lock = threading.Lock()


# ==================== 辅助函数 ====================

def load_config():
    """加载配置文件"""
    config_path = os.path.join(SPIDER_DIR, CONFIG_FILE)
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_config(config):
    """保存配置文件"""
    config_path = os.path.join(SPIDER_DIR, CONFIG_FILE)
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


def load_videos():
    """加载视频数据"""
    videos_path = os.path.join(SPIDER_DIR, OUTPUT_FILE)
    if os.path.exists(videos_path):
        with open(videos_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def load_logs(lines=100, tail=True):
    """加载日志"""
    log_path = os.path.join(SPIDER_DIR, LOG_FILE)
    if not os.path.exists(log_path):
        return []
    
    with open(log_path, 'r', encoding='utf-8') as f:
        all_logs = f.readlines()
    
    if tail:
        return [l.strip() for l in all_logs[-lines:]]
    return [l.strip() for l in all_logs[:lines]]


def calculate_stats(videos):
    """计算统计数据"""
    if not videos:
        return {
            'total_videos': 0,
            'total_plays': 0,
            'total_likes': 0,
            'avg_plays': 0,
            'play_distribution': {},
            'duration_distribution': {},
            'time_distribution': {}
        }
    
    total_plays = sum(v.get('play_count', 0) for v in videos)
    total_likes = sum(v.get('like_count', 0) for v in videos)
    
    # 播放量分布 - 使用万(W)单位
    play_dist = {'0-5W': 0, '5-10W': 0, '10-20W': 0, '20-50W': 0, '50-100W': 0, '100W+': 0}
    for v in videos:
        p = v.get('play_count', 0)
        if p < 50000:
            play_dist['0-5W'] += 1
        elif p < 100000:
            play_dist['5-10W'] += 1
        elif p < 200000:
            play_dist['10-20W'] += 1
        elif p < 500000:
            play_dist['20-50W'] += 1
        elif p < 1000000:
            play_dist['50-100W'] += 1
        else:
            play_dist['100W+'] += 1
    
    # 时长分布
    dur_dist = {'lt_1min': 0, '1_5min': 0, '5_15min': 0, '15_30min': 0, 'gt_30min': 0}
    for v in videos:
        dur = v.get('duration', '0:0')
        parts = dur.split(':')
        minutes = int(parts[0])
        if len(parts) > 1:
            minutes += int(parts[1]) / 60
        else:
            minutes = 0
        
        if minutes < 1:
            dur_dist['lt_1min'] += 1
        elif minutes < 5:
            dur_dist['1_5min'] += 1
        elif minutes < 15:
            dur_dist['5_15min'] += 1
        elif minutes < 30:
            dur_dist['15_30min'] += 1
        else:
            dur_dist['gt_30min'] += 1
    
    # 时间分布
    now = time.time()
    day = 86400
    time_dist = {'today': 0, 'yesterday': 0, '2_3days': 0, '3_7days': 0, 'gt_7days': 0}
    for v in videos:
        pub = v.get('pubdate', 0)
        diff = now - pub
        if diff < day:
            time_dist['today'] += 1
        elif diff < 2 * day:
            time_dist['yesterday'] += 1
        elif diff < 3 * day:
            time_dist['2_3days'] += 1
        elif diff < 7 * day:
            time_dist['3_7days'] += 1
        else:
            time_dist['gt_7days'] += 1
    
    return {
        'total_videos': len(videos),
        'total_plays': total_plays,
        'total_likes': total_likes,
        'avg_plays': total_plays // len(videos),
        'play_distribution': play_dist,
        'duration_distribution': dur_dist,
        'time_distribution': time_dist,
        'last_run': load_config().get('last_run', '')
    }


# ==================== API 路由 ====================

@app.route('/')
def index():
    """返回 HTML 页面"""
    return send_file(os.path.join(SPIDER_DIR, '../bilibili_video_fenxi_webui/index.html'))


@app.route('/styles.css')
def styles():
    """返回 CSS 文件"""
    return send_file(os.path.join(SPIDER_DIR, '../bilibili_video_fenxi_webui/styles.css'))


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取爬虫配置"""
    try:
        config = load_config()
        # 过滤敏感信息
        safe_config = {k: v for k, v in config.items() if k not in ['sessdata', 'cookies']}
        return jsonify({'code': 0, 'data': safe_config})
    except Exception as e:
        return jsonify({'code': 5001, 'message': f'获取配置失败: {str(e)}'})


@app.route('/api/config', methods=['POST'])
def update_config():
    """更新爬虫配置"""
    try:
        config = load_config()
        data = request.get_json()
        
        # 允许更新的字段
        updatable = ['keyword', 'order', 'target_count', 'page_size', 'filter', 
                     'max_pages_per_run', 'request_interval', 'interval_minutes', 'last_page']
        
        for key in updatable:
            if key in data:
                config[key] = data[key]
        
        save_config(config)
        return jsonify({'code': 0, 'message': '配置已更新'})
    except Exception as e:
        return jsonify({'code': 4003, 'message': f'配置更新失败: {str(e)}'})


@app.route('/api/status', methods=['GET'])
def get_status():
    """获取爬虫状态"""
    global spider_process
    
    try:
        config = load_config()
        videos = load_videos()
        
        return jsonify({
            'code': 0,
            'data': {
                'is_running': spider_process is not None,
                'current_page': config.get('last_page', 1),
                'total_videos': len(videos),
                'new_videos_this_run': 0,
                'last_run': config.get('last_run', ''),
                'progress': len(videos),
                'target_count': config.get('target_count', 100)
            }
        })
    except Exception as e:
        return jsonify({'code': 5001, 'message': f'获取状态失败: {str(e)}'})


@app.route('/api/spider/start', methods=['POST'])
def start_spider():
    """启动爬虫"""
    global spider_process
    
    with spider_lock:
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
            cwd=SPIDER_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
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
    
    with spider_lock:
        if spider_process is None:
            return jsonify({'code': 4002, 'message': '爬虫未在运行'})
        
        spider_process.terminate()
        spider_process = None
        
        return jsonify({'code': 0, 'message': '爬虫已停止'})


@app.route('/api/videos', methods=['GET'])
def get_videos():
    """获取视频列表"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        sort = request.args.get('sort', 'pubdate')
        order = request.args.get('order', 'desc')
        keyword = request.args.get('keyword', '').lower()
        
        videos = load_videos()
        
        # 搜索过滤
        if keyword:
            videos = [v for v in videos if 
                     keyword in v.get('title', '').lower() or 
                     keyword in v.get('author', '').lower()]
        
        # 排序
        reverse = order == 'desc'
        videos = sorted(videos, key=lambda x: x.get(sort, 0), reverse=reverse)
        
        # 分页
        total = len(videos)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        start = (page - 1) * page_size
        end = start + page_size
        
        return jsonify({
            'code': 0,
            'data': {
                'videos': videos[start:end],
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
        })
    except Exception as e:
        return jsonify({'code': 5001, 'message': f'获取视频列表失败: {str(e)}'})


@app.route('/api/videos/<bvid>', methods=['GET'])
def get_video(bvid):
    """获取单个视频"""
    videos = load_videos()
    video = next((v for v in videos if v['bvid'] == bvid), None)
    
    if video is None:
        return jsonify({'code': 4004, 'message': '视频不存在'})
    
    return jsonify({'code': 0, 'data': video})


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取日志"""
    try:
        lines = int(request.args.get('lines', 100))
        tail = request.args.get('tail', 'true') == 'true'
        
        logs = load_logs(lines, tail)
        
        return jsonify({
            'code': 0,
            'data': {
                'logs': logs,
                'total_lines': len(load_logs(lines=999999, tail=False))
            }
        })
    except Exception as e:
        return jsonify({'code': 5001, 'message': f'获取日志失败: {str(e)}'})


@app.route('/api/logs/clear', methods=['POST'])
def clear_logs():
    """清除日志"""
    try:
        log_path = os.path.join(SPIDER_DIR, LOG_FILE)
        with open(log_path, 'w') as f:
            f.write('')
        return jsonify({'code': 0, 'message': '日志已清空'})
    except Exception as e:
        return jsonify({'code': 5001, 'message': f'清空日志失败: {str(e)}'})


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计数据"""
    try:
        videos = load_videos()
        stats = calculate_stats(videos)
        return jsonify({'code': 0, 'data': stats})
    except Exception as e:
        return jsonify({'code': 5001, 'message': f'获取统计失败: {str(e)}'})


@app.route('/api/export', methods=['GET'])
def export_data():
    """导出数据"""
    videos_path = os.path.join(SPIDER_DIR, OUTPUT_FILE)
    return send_file(videos_path, mimetype='application/json', 
                     as_attachment=True, download_name='filtered_videos.json')


# ==================== 启动 ====================

if __name__ == '__main__':
    print(f"""
╔══════════════════════════════════════════════════╗
║       B站视频爬虫 WebUI  -  端口: 30001         ║
╠══════════════════════════════════════════════════╣
║  访问地址: http://localhost:30001                ║
║  API文档:   http://localhost:30001/api/docs     ║
╚══════════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=30001, debug=False)