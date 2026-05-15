"""
B站视频爬虫 - 支持断点续爬和定时运行
状态持久化到 config.yaml
"""
import requests
import json
import time
import yaml
from datetime import datetime
from urllib.parse import unquote
from pathlib import Path

# ============== 配置 ==============
CONFIG_FILE = "config.yaml"

def load_config():
    """加载配置文件"""
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_config(config):
    """保存配置到文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

def get_config():
    """获取配置"""
    config_path = Path(CONFIG_FILE)
    if not config_path.exists():
        print(f"配置文件 {CONFIG_FILE} 不存在")
        return None
    return load_config()

# ============== 工具函数 ==============

def calculate_play_per_hour(play_count, pubdate_timestamp):
    """计算每小时播放量"""
    current_time = time.time()
    hours_since_publish = (current_time - pubdate_timestamp) / 3600
    if hours_since_publish <= 0:
        hours_since_publish = 0.1
    return play_count / hours_since_publish

def format_pubdate(pubdate_timestamp):
    """将时间戳转换为可读字符串"""
    return datetime.fromtimestamp(pubdate_timestamp).strftime('%Y-%m-%d %H:%M:%S')

def log_to_file(message):
    """写入详细日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}\n"
    with open("spider_detail.log", "a", encoding="utf-8") as f:
        f.write(log_line)

def clear_log():
    """清空详细日志"""
    open("spider_detail.log", "w", encoding="utf-8").close()

# ============== 核心功能 ==============

def search_videos(keyword, page=1, page_size=30, order="pubdate", sessdata="", cookies=None, headers=None):
    """搜索B站视频，返回视频列表或特殊标记"""
    url = "https://api.bilibili.com/x/web-interface/search/type"
    params = {
        "search_type": "video",
        "keyword": keyword,
        "page": page,
        "page_size": page_size,
        "order": order,
    }

    request_headers = headers.copy() if headers else {}
    request_headers["Accept"] = "application/json, text/plain, */*"
    request_headers["Accept-Language"] = "zh-CN,zh;q=0.9,en;q=0.8"

    request_cookies = cookies.copy() if cookies else {}
    if sessdata:
        request_cookies["SESSDATA"] = unquote(sessdata)

    try:
        response = requests.get(url, params=params, headers=request_headers, cookies=request_cookies, timeout=10)
        data = response.json()
        if data["code"] == 0:
            videos = data["data"].get("result", [])
            log_to_file(f"    [API成功] 第{page}页返回{len(videos)}个视频")
            return videos
        elif data.get("code") == -412:
            # 被B站封禁，返回特殊标记
            log_to_file(f"    [API 412] 第{page}页被B站封禁 (request was banned)")
            return "__BANNED__"
        else:
            error_msg = data.get('message', '未知错误')
            error_code = data.get('code', '?')
            log_to_file(f"    [API失败] 第{page}页错误码:{error_code} 错误信息:{error_msg}")
            print(f"搜索失败: {error_msg} (code: {error_code})")
            return []
    except Exception as e:
        log_to_file(f"    [请求异常] 第{page}页异常:{str(e)}")
        print(f"请求异常: {e}")
        return []

def filter_video(video, filter_config):
    """判断视频是否通过筛选"""
    pubdate = video.get("pubdate", 0)
    play_count_str = video.get("play", "0")

    try:
        play_count = int(play_count_str) if play_count_str else 0
    except ValueError:
        play_count = 0

    current_time = time.time()
    hours_since_publish = (current_time - pubdate) / 3600

    within_24h_config = filter_config.get("within_24h", {})
    beyond_24h_config = filter_config.get("beyond_24h", {})

    max_hours = within_24h_config.get("max_hours", 24)
    min_play_per_hour = within_24h_config.get("min_play_per_hour", 2000)
    min_play_count = beyond_24h_config.get("min_play_count", 20000)

    if hours_since_publish <= max_hours:
        play_per_hour = calculate_play_per_hour(play_count, pubdate)
        return play_per_hour >= min_play_per_hour, play_per_hour, hours_since_publish
    else:
        return play_count >= min_play_count, play_count, hours_since_publish

def clean_title(title):
    """清除HTML标签"""
    import re
    clean = re.sub(r'<[^>]+>', '', title)
    return clean

def standardize_video(video, filter_result):
    """标准化视频数据结构"""
    pubdate = video.get("pubdate", 0)
    play_count_str = video.get("play", "0")
    try:
        play_count = int(play_count_str) if play_count_str else 0
    except ValueError:
        play_count = 0

    bvid = video.get("bvid", "")
    threshold, threshold_type = filter_result

    return {
        "title": clean_title(video.get("title", "")),
        "bvid": bvid,
        "author": video.get("author", ""),
        "play_count": play_count,
        "like_count": video.get("like", 0),
        "pubdate": pubdate,
        "pubdate_str": format_pubdate(pubdate),
        "duration": video.get("duration", ""),
        "url": f"https://www.bilibili.com/video/{bvid}",
        "filter_threshold": threshold,
        "filter_type": threshold_type
    }

def save_results(videos, output_file):
    """保存结果（去重）"""
    seen = {}
    for v in videos:
        bvid = v.get("bvid", "")
        if bvid not in seen:
            seen[bvid] = v
    unique_videos = list(seen.values())

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_videos, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(unique_videos)} 条结果到 {output_file}")
    return len(unique_videos)

def load_existing_results(output_file):
    """加载已有结果"""
    if Path(output_file).exists():
        with open(output_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def merge_results(existing, new_videos):
    """合并结果，去重"""
    existing_bvids = {v["bvid"] for v in existing}
    merged = existing.copy()
    for video in new_videos:
        bvid = video.get("bvid", "")
        if bvid not in existing_bvids:
            merged.append(video)
            existing_bvids.add(bvid)
    return merged

def sort_videos_by_time(videos):
    """按发布时间排序，从新到旧"""
    return sorted(videos, key=lambda x: x.get("pubdate", 0), reverse=True)

# ============== 主流程 ==============

def run_spider():
    """运行爬虫"""
    print("=" * 50)
    print("B站视频爬虫 - 断点续爬版")
    print("=" * 50)

    # 每次运行清空详细日志
    clear_log()
    log_to_file("========== 爬虫运行开始 ==========")

    config = get_config()
    if config is None:
        return

    keyword = config.get("keyword", "")
    order = config.get("order", "pubdate")
    page_size = config.get("page_size", 30)
    filter_config = config.get("filter", {})
    sessdata = config.get("sessdata", "")
    cookies = config.get("cookies", {"buvid3": "F"})
    headers = config.get("headers", {})
    request_interval = config.get("request_interval", 0.5)
    output_file = config.get("output_file", "filtered_videos.json")
    target_count = config.get("target_count", 100)
    max_pages = config.get("max_pages_per_run", 100)
    interval_minutes = config.get("interval_minutes", 0)

    # 从配置读取进度
    start_page = config.get("last_page", 1)
    last_run = config.get("last_run", None)

    print(f"\n配置信息:")
    print(f"  关键词: {keyword}")
    print(f"  排序方式: {order}")
    print(f"  目标数量: {target_count}")
    print(f"  24小时内筛选: 播放量/小时 > {filter_config.get('within_24h', {}).get('min_play_per_hour', 2000)}")
    print(f"  超过24小时筛选: 播放量 > {filter_config.get('beyond_24h', {}).get('min_play_count', 20000)}")
    print(f"  起始页码: {start_page}")
    print(f"  上次运行: {last_run}")
    if interval_minutes > 0:
        print(f"  定时模式: 每 {interval_minutes} 分钟")
    print()

    # 加载已有结果
    existing_results = load_existing_results(output_file)
    existing_count = len(existing_results)
    if existing_count > 0:
        print(f"已加载 {existing_count} 条历史记录")

    # 持续运行
    while True:
        page = start_page
        unique_bvids = set(v["bvid"] for v in existing_results)
        all_filtered = existing_results.copy()
        new_count = 0

        print(f"\n{'='*50}")
        print(f"开始爬取，从第 {page} 页")
        print(f"当前已有: {len(all_filtered)} 条视频")
        print(f"目标: {target_count} 条")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")

        pages_in_this_run = 0
        consecutive_empty = 0
        consecutive_limit = 3
        consecutive_412 = 0  # 连续412计数器
        max_consecutive_412 = 3  # 连续412达到此值则停止

        try:
            while len(unique_bvids) < target_count and pages_in_this_run < max_pages:
                print(f"\n正在获取第 {page} 页... (已收集 {len(all_filtered)}/{target_count})")

                videos = search_videos(
                    keyword=keyword,
                    page=page,
                    page_size=page_size,
                    order=order,
                    sessdata=sessdata,
                    cookies=cookies,
                    headers=headers
                )

                if videos == "__BANNED__":
                    consecutive_412 += 1
                    log_to_file(f"  [连续412] 第{page}页被ban ({consecutive_412}/{max_consecutive_412})")
                    print(f"  连续第{consecutive_412}次被B站封禁")
                    if consecutive_412 >= max_consecutive_412:
                        log_to_file(f"  [停止] 连续{max_consecutive_412}次被ban，停止爬取")
                        print(f"连续{max_consecutive_412}次被B站封禁，停止爬取")
                        break
                    page += 1
                    time.sleep(request_interval)
                    continue

                if not videos:
                    log_to_file(f"  [无数据] 第{page}页没有返回视频（可能被ban或真的没有更多结果）")
                    print("  没有更多结果或请求失败")
                    break

                print(f"  获取到 {len(videos)} 个视频")

                page_filtered = []
                for video in videos:
                    passed, threshold, value = filter_video(video, filter_config)
                    bvid = video.get("bvid", "")
                    title = clean_title(video.get("title", ""))
                    play = video.get("play", "0")
                    pubdate = video.get("pubdate", 0)
                    pubdate_str = format_pubdate(pubdate) if pubdate else "未知"

                    if passed:
                        std_video = standardize_video(video, (threshold, "play_per_hour" if value < 24 else "total_play"))
                        if bvid not in unique_bvids:
                            page_filtered.append(std_video)
                            unique_bvids.add(bvid)
                            all_filtered.append(std_video)
                            new_count += 1
                            log_to_file(f"    [新增] {bvid} | {title[:40]}... | 播放:{play} | 时间:{pubdate_str} | 阈值:{threshold:.1f}")
                            print(f"    ✓ [{bvid}] {title[:30]}... (阈值: {threshold:.1f})")
                        else:
                            log_to_file(f"    [跳过-已存在] {bvid} | {title[:40]}...")
                            print(f"    ○ [{bvid}] 已存在，跳过")
                    else:
                        if value < 24:
                            reason = f"播放量/小时={threshold:.1f} < {filter_config.get('within_24h', {}).get('min_play_per_hour', 2000)}"
                        else:
                            reason = f"总播放={play} < {filter_config.get('beyond_24h', {}).get('min_play_count', 20000)}"
                        log_to_file(f"    [过滤] {bvid} | {title[:40]}... | 原因:{reason}")
                        print(f"    ✗ [{bvid}] {title[:30]}... 未通过筛选")

                pages_in_this_run += 1
                print(f"  本页新增: {len(page_filtered)} 条，当前累计: {len(all_filtered)} 条")

                if len(page_filtered) == 0:
                    consecutive_empty += 1
                else:
                    consecutive_empty = 0

                # 连续空页则停止
                if consecutive_empty >= consecutive_limit and len(all_filtered) >= target_count:
                    print(f"连续{consecutive_limit}页无新增，停止爬取")
                    break

                page += 1
                time.sleep(request_interval)

        except KeyboardInterrupt:
            print("\n用户中断")

        # 保存结果
        if all_filtered:
            all_filtered = sort_videos_by_time(all_filtered)
            save_results(all_filtered, output_file)

        print(f"\n=== 本次爬取完成 ===")
        print(f"本次新增: {new_count} 条")
        print(f"历史累计: {len(all_filtered)} 条")
        print(f"下次起始页: {page}")

        # 更新配置中的进度
        config["last_page"] = page
        config["last_run"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_config(config)

        if interval_minutes <= 0:
            print("\n单次运行完成")
            break

        print(f"\n等待 {interval_minutes} 分钟...")
        print(f"按 Ctrl+C 停止持续运行\n")
        time.sleep(interval_minutes * 60)

    print("\n" + "=" * 50)
    print("执行完成")
    print("=" * 50)

if __name__ == "__main__":
    run_spider()