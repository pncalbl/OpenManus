"""
Error diagnosis and suggestion system.
"""

from typing import Dict, List, Optional

from app.recovery.errors import ErrorCategory, classify_error


class ErrorDiagnosis:
    """Diagnose errors and provide actionable suggestions."""

    def __init__(self):
        """Initialize error diagnosis system."""
        self.error_patterns = self._load_error_patterns()
        self.suggestions_db = self._load_suggestions()
        self.docs_links = self._load_docs_links()

    def diagnose(self, error: Exception) -> Dict:
        """
        Analyze an error and provide diagnosis information.

        Args:
            error: The exception to diagnose

        Returns:
            Dictionary containing diagnosis details
        """
        category = classify_error(error)
        error_str = str(error)

        return {
            "category": category.value,
            "error_type": type(error).__name__,
            "message": error_str,
            "cause": self._analyze_cause(error, category),
            "suggestions": self._get_suggestions(category, error_str),
            "docs_link": self._get_docs_link(category),
            "is_retryable": self._is_retryable(category),
        }

    def _analyze_cause(self, error: Exception, category: ErrorCategory) -> str:
        """
        Analyze the likely cause of an error.

        Args:
            error: The exception
            category: Error category

        Returns:
            Human-readable cause description
        """
        causes = {
            ErrorCategory.NETWORK: "网络连接问题或服务不可达",
            ErrorCategory.TIMEOUT: "操作超时，可能由于网络慢或服务响应慢",
            ErrorCategory.RATE_LIMIT: "API 请求频率超过限制",
            ErrorCategory.AUTHENTICATION: "认证失败，API Key 可能无效或过期",
            ErrorCategory.BROWSER: "浏览器自动化过程中出现问题",
            ErrorCategory.FILESYSTEM: "文件系统操作失败",
            ErrorCategory.API: "API 服务返回错误",
            ErrorCategory.CONFIGURATION: "配置错误或缺少必要配置",
            ErrorCategory.RESOURCE: "系统资源不足（内存、磁盘等）",
            ErrorCategory.UNKNOWN: "未知错误，需要进一步调查",
        }

        return causes.get(category, "无法确定具体原因")

    def _get_suggestions(self, category: ErrorCategory, error_str: str) -> List[str]:
        """
        Get actionable suggestions for fixing an error.

        Args:
            category: Error category
            error_str: Error message string

        Returns:
            List of suggestions
        """
        base_suggestions = self.suggestions_db.get(category, [])

        # Add context-specific suggestions based on error message
        specific_suggestions = self._get_context_suggestions(category, error_str)

        return base_suggestions + specific_suggestions

    def _get_context_suggestions(
        self, category: ErrorCategory, error_str: str
    ) -> List[str]:
        """
        Get context-specific suggestions based on error details.

        Args:
            category: Error category
            error_str: Error message string

        Returns:
            List of context-specific suggestions
        """
        suggestions = []
        error_lower = error_str.lower()

        if category == ErrorCategory.NETWORK:
            if "dns" in error_lower:
                suggestions.append("DNS 解析失败，检查域名是否正确")
            if "proxy" in error_lower:
                suggestions.append("代理配置可能有问题，检查代理设置")

        elif category == ErrorCategory.API:
            if "500" in error_lower:
                suggestions.append("服务器内部错误，稍后重试")
            if "503" in error_lower:
                suggestions.append("服务暂时不可用，等待几分钟后重试")

        elif category == ErrorCategory.AUTHENTICATION:
            if "expired" in error_lower:
                suggestions.append("API Key 已过期，需要更新")
            if "invalid" in error_lower:
                suggestions.append("API Key 格式不正确，检查是否完整复制")

        return suggestions

    def _get_docs_link(self, category: ErrorCategory) -> Optional[str]:
        """
        Get documentation link for an error category.

        Args:
            category: Error category

        Returns:
            Documentation URL or None
        """
        return self.docs_links.get(category)

    def _is_retryable(self, category: ErrorCategory) -> bool:
        """
        Determine if errors in this category are typically retryable.

        Args:
            category: Error category

        Returns:
            True if retryable
        """
        retryable_categories = {
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.API,
            ErrorCategory.BROWSER,
        }

        return category in retryable_categories

    def _load_error_patterns(self) -> Dict:
        """Load error pattern matching rules."""
        return {
            # Add custom pattern matching rules here
        }

    def _load_suggestions(self) -> Dict[ErrorCategory, List[str]]:
        """Load suggestion database for each error category."""
        return {
            ErrorCategory.NETWORK: [
                "检查网络连接是否正常",
                "确认目标服务是否可访问",
                "检查防火墙或代理设置",
                "尝试使用 VPN 或更换网络环境",
            ],
            ErrorCategory.TIMEOUT: [
                "增加超时时间设置",
                "检查网络延迟",
                "确认服务是否响应缓慢",
                "考虑将任务拆分为更小的子任务",
            ],
            ErrorCategory.RATE_LIMIT: [
                "等待几分钟后重试",
                "检查 API 配额使用情况",
                "考虑升级 API 计划或增加配额",
                "实现请求速率控制",
            ],
            ErrorCategory.AUTHENTICATION: [
                "检查 API Key 是否正确配置在 config.toml 中",
                "验证 API Key 是否有效且未过期",
                "确认 API Key 具有所需的权限",
                "登录服务提供商网站查看 API Key 状态",
            ],
            ErrorCategory.BROWSER: [
                "确认已安装浏览器驱动：playwright install",
                "检查浏览器是否正在运行",
                "尝试重启浏览器",
                "检查页面是否正确加载",
                "考虑增加页面加载超时时间",
            ],
            ErrorCategory.FILESYSTEM: [
                "检查文件路径是否正确",
                "确认文件或目录存在",
                "验证读写权限",
                "检查磁盘空间是否充足",
            ],
            ErrorCategory.API: [
                "查看 API 服务状态页面",
                "检查 API 版本是否支持",
                "验证请求参数是否正确",
                "稍后重试",
            ],
            ErrorCategory.CONFIGURATION: [
                "检查 config/config.toml 文件是否存在",
                "确认所有必需的配置项已填写",
                "参考 config/config.example.toml 示例",
                "验证配置格式是否正确",
            ],
            ErrorCategory.RESOURCE: [
                "关闭不必要的应用程序释放资源",
                "检查系统内存和磁盘使用情况",
                "考虑增加系统资源",
                "优化任务以减少资源使用",
            ],
            ErrorCategory.UNKNOWN: [
                "查看完整的错误日志获取更多信息",
                "搜索相关错误信息",
                "在 GitHub Issues 中报告问题",
                "联系技术支持",
            ],
        }

    def _load_docs_links(self) -> Dict[ErrorCategory, str]:
        """Load documentation links for each error category."""
        base_url = "https://github.com/FoundationAgents/OpenManus"

        return {
            ErrorCategory.NETWORK: f"{base_url}#network-issues",
            ErrorCategory.TIMEOUT: f"{base_url}#timeout-issues",
            ErrorCategory.RATE_LIMIT: f"{base_url}#rate-limiting",
            ErrorCategory.AUTHENTICATION: f"{base_url}#configuration",
            ErrorCategory.BROWSER: f"{base_url}#browser-automation-tool-optional",
            ErrorCategory.FILESYSTEM: f"{base_url}#installation",
            ErrorCategory.API: f"{base_url}#configuration",
            ErrorCategory.CONFIGURATION: f"{base_url}#configuration",
            ErrorCategory.RESOURCE: f"{base_url}#installation",
        }

    def format_diagnosis(self, diagnosis: Dict) -> str:
        """
        Format diagnosis information for display.

        Args:
            diagnosis: Diagnosis dictionary

        Returns:
            Formatted string
        """
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append("错误诊断")
        lines.append(f"{'='*60}")
        lines.append(f"类别: {diagnosis['category']}")
        lines.append(f"类型: {diagnosis['error_type']}")
        lines.append(f"可重试: {'是' if diagnosis['is_retryable'] else '否'}")
        lines.append(f"\n原因:")
        lines.append(f"  {diagnosis['cause']}")

        if diagnosis['suggestions']:
            lines.append(f"\n建议:")
            for i, suggestion in enumerate(diagnosis['suggestions'], 1):
                lines.append(f"  {i}. {suggestion}")

        if diagnosis['docs_link']:
            lines.append(f"\n文档: {diagnosis['docs_link']}")

        lines.append(f"{'='*60}\n")

        return "\n".join(lines)
