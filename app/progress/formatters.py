"""
输出格式化工具

提供各种格式化功能用于进度显示。
"""

from datetime import datetime
from typing import Any, Dict, Optional


def format_duration(seconds: float) -> str:
    """
    格式化持续时间

    Args:
        seconds: 秒数

    Returns:
        格式化的时间字符串 (如 "1.5s", "2m 30s", "1h 15m")
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_percentage(value: float, decimals: int = 0) -> str:
    """
    格式化百分比

    Args:
        value: 百分比值 (0-100)
        decimals: 小数位数

    Returns:
        格式化的百分比字符串 (如 "45%", "67.5%")
    """
    format_str = f"{{:.{decimals}f}}%"
    return format_str.format(value)


def format_timestamp(dt: Optional[datetime] = None, format_str: str = "%H:%M:%S") -> str:
    """
    格式化时间戳

    Args:
        dt: datetime 对象，None 则使用当前时间
        format_str: 格式字符串

    Returns:
        格式化的时间字符串
    """
    dt = dt or datetime.now()
    return dt.strftime(format_str)


def format_step_info(current: int, total: Optional[int] = None) -> str:
    """
    格式化步骤信息

    Args:
        current: 当前步骤
        total: 总步骤数

    Returns:
        格式化的步骤字符串 (如 "5/10", "5")
    """
    if total is not None:
        return f"{current}/{total}"
    else:
        return str(current)


def format_speed(items: float, duration: float, unit: str = "items") -> str:
    """
    格式化处理速度

    Args:
        items: 处理的项目数
        duration: 持续时间（秒）
        unit: 单位名称

    Returns:
        格式化的速度字符串 (如 "15.5 items/s")
    """
    if duration <= 0:
        return f"? {unit}/s"

    speed = items / duration
    if speed < 1:
        return f"{speed:.2f} {unit}/s"
    elif speed < 100:
        return f"{speed:.1f} {unit}/s"
    else:
        return f"{speed:.0f} {unit}/s"


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    截断字符串

    Args:
        text: 输入字符串
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        截断后的字符串
    """
    if len(text) <= max_length:
        return text

    truncated_length = max_length - len(suffix)
    if truncated_length <= 0:
        return suffix[:max_length]

    return text[:truncated_length] + suffix


def format_bytes(bytes_count: int) -> str:
    """
    格式化字节数

    Args:
        bytes_count: 字节数

    Returns:
        格式化的大小字符串 (如 "1.5 KB", "2.3 MB")
    """
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(bytes_count)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def format_number(num: int) -> str:
    """
    格式化数字（添加千位分隔符）

    Args:
        num: 数字

    Returns:
        格式化的数字字符串 (如 "1,234,567")
    """
    return f"{num:,}"


def create_progress_bar(
    percentage: float,
    width: int = 20,
    filled_char: str = "█",
    empty_char: str = "░",
) -> str:
    """
    创建文本进度条

    Args:
        percentage: 百分比 (0-100)
        width: 进度条宽度
        filled_char: 填充字符
        empty_char: 空字符

    Returns:
        进度条字符串
    """
    filled_width = int(width * percentage / 100)
    empty_width = width - filled_width

    return filled_char * filled_width + empty_char * empty_width


def format_table_row(columns: list[str], widths: list[int], separator: str = " | ") -> str:
    """
    格式化表格行

    Args:
        columns: 列值列表
        widths: 列宽度列表
        separator: 分隔符

    Returns:
        格式化的表格行
    """
    formatted_columns = []
    for col, width in zip(columns, widths):
        formatted_columns.append(col.ljust(width))

    return separator.join(formatted_columns)


def colorize(text: str, color: str) -> str:
    """
    为文本添加 ANSI 颜色代码

    Args:
        text: 输入文本
        color: 颜色名称 (black, red, green, yellow, blue, magenta, cyan, white)

    Returns:
        带颜色代码的文本
    """
    colors = {
        "black": "\033[30m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "reset": "\033[0m",
    }

    color_code = colors.get(color.lower(), "")
    reset_code = colors["reset"]

    return f"{color_code}{text}{reset_code}"


def format_key_value_pairs(data: Dict[str, Any], indent: int = 0) -> str:
    """
    格式化键值对数据

    Args:
        data: 数据字典
        indent: 缩进级别

    Returns:
        格式化的字符串
    """
    lines = []
    indent_str = "  " * indent

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{indent_str}{key}:")
            lines.append(format_key_value_pairs(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{indent_str}{key}: [{len(value)} items]")
        else:
            lines.append(f"{indent_str}{key}: {value}")

    return "\n".join(lines)
