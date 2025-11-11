"""
辅助工具函数

提供各种通用的辅助功能
"""

import uuid
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta


def generate_task_id() -> str:
    """
    生成任务ID
    
    Returns:
        任务ID字符串
    """
    return str(uuid.uuid4())


def format_duration(seconds: float) -> str:
    """
    格式化持续时间
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的时间字符串
    """
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def validate_task_data(task_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    验证任务数据
    
    Args:
        task_data: 任务数据字典
        
    Returns:
        (是否有效, 错误信息)
    """
    required_fields = ["type", "description"]
    
    for field in required_fields:
        if field not in task_data:
            return False, f"缺少必需字段: {field}"
        
        if not task_data[field]:
            return False, f"字段 {field} 不能为空"
    
    # 验证任务类型
    valid_types = ["travel_planning", "code_development", "research_report", "general"]
    if task_data["type"] not in valid_types:
        return False, f"无效的任务类型: {task_data['type']}"
    
    return True, None


def deep_merge_dict(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并字典
    
    Args:
        dict1: 第一个字典
        dict2: 第二个字典
        
    Returns:
        合并后的字典
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value
    
    return result


def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    安全获取字典值，支持点号分隔的嵌套键
    
    Args:
        data: 数据字典
        key: 键名，支持点号分隔
        default: 默认值
        
    Returns:
        获取到的值
    """
    keys = key.split('.')
    value = data
    
    try:
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        return default


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    将列表分块
    
    Args:
        lst: 原始列表
        chunk_size: 块大小
        
    Returns:
        分块后的列表
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
):
    """
    带退避的重试装饰器
    
    Args:
        func: 要重试的函数
        max_retries: 最大重试次数
        base_delay: 基础延迟时间
        max_delay: 最大延迟时间
        exponential_base: 指数退避基数
        jitter: 是否添加随机抖动
        
    Returns:
        装饰后的函数
    """
    def wrapper(*args, **kwargs):
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == max_retries:
                    raise last_exception
                
                # 计算延迟时间
                delay = min(base_delay * (exponential_base ** attempt), max_delay)
                
                if jitter:
                    import random
                    delay *= (0.5 + random.random() * 0.5)
                
                time.sleep(delay)
        
        raise last_exception
    
    return wrapper


def format_timestamp(timestamp: Union[datetime, str, float]) -> str:
    """
    格式化时间戳
    
    Args:
        timestamp: 时间戳
        
    Returns:
        格式化的时间字符串
    """
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp)
        except ValueError:
            return timestamp
    
    if isinstance(timestamp, (int, float)):
        timestamp = datetime.fromtimestamp(timestamp)
    
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def calculate_elapsed_time(start_time: datetime, end_time: Optional[datetime] = None) -> float:
    """
    计算经过的时间
    
    Args:
        start_time: 开始时间
        end_time: 结束时间，如果为None则使用当前时间
        
    Returns:
        经过的秒数
    """
    if end_time is None:
        end_time = datetime.now()
    
    return (end_time - start_time).total_seconds()


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    截断字符串
    
    Args:
        text: 原始字符串
        max_length: 最大长度
        suffix: 后缀
        
    Returns:
        截断后的字符串
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    import re
    
    # 移除或替换非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # 移除首尾空格和点
    filename = filename.strip(' .')
    
    # 确保不为空
    if not filename:
        filename = "unnamed"
    
    return filename


def create_progress_bar(current: int, total: int, width: int = 50) -> str:
    """
    创建进度条
    
    Args:
        current: 当前进度
        total: 总数
        width: 进度条宽度
        
    Returns:
        进度条字符串
    """
    if total == 0:
        return "[" + " " * width + "] 0/0 (0%)"
    
    percentage = current / total
    filled_width = int(width * percentage)
    
    bar = "█" * filled_width + "░" * (width - filled_width)
    percentage_str = f"{percentage:.1%}"
    
    return f"[{bar}] {current}/{total} ({percentage_str})"


def parse_duration(duration_str: str) -> Optional[float]:
    """
    解析持续时间字符串
    
    Args:
        duration_str: 持续时间字符串，如 "1h30m", "45s", "2d"
        
    Returns:
        秒数，如果解析失败返回None
    """
    import re
    
    # 匹配模式
    patterns = [
        (r'(\d+)d', lambda m: int(m.group(1)) * 24 * 3600),  # 天
        (r'(\d+)h', lambda m: int(m.group(1)) * 3600),       # 小时
        (r'(\d+)m', lambda m: int(m.group(1)) * 60),         # 分钟
        (r'(\d+)s', lambda m: int(m.group(1))),              # 秒
    ]
    
    total_seconds = 0
    
    for pattern, converter in patterns:
        matches = re.findall(pattern, duration_str)
        for match in matches:
            total_seconds += converter(match)
    
    return total_seconds if total_seconds > 0 else None


def generate_summary(data: Dict[str, Any], max_items: int = 5) -> str:
    """
    生成数据摘要
    
    Args:
        data: 数据字典
        max_items: 最大显示项目数
        
    Returns:
        摘要字符串
    """
    if not data:
        return "空数据"
    
    items = []
    for key, value in data.items():
        if isinstance(value, (list, dict)):
            items.append(f"{key}: {len(value)} 项")
        else:
            items.append(f"{key}: {value}")
        
        if len(items) >= max_items:
            break
    
    summary = ", ".join(items)
    
    if len(data) > max_items:
        summary += f" ... (共 {len(data)} 项)"
    
    return summary
