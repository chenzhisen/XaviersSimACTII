import os
import platform

class PathUtils:
    """路径处理工具类"""
    
    @staticmethod
    def get_project_root():
        """获取项目根目录"""
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    @staticmethod
    def normalize_path(*paths):
        """标准化路径
        
        将路径转换为当前平台的格式，并处理相对路径
        
        参数:
            *paths: 路径片段
            
        返回:
            标准化后的路径
        """
        return os.path.normpath(os.path.join(*paths))
    
    @staticmethod
    def to_url_path(path):
        """转换为URL路径格式
        
        确保路径使用正斜杠，适用于API请求
        
        参数:
            path: 原始路径
            
        返回:
            转换后的URL路径
        """
        return path.replace(os.path.sep, '/')
    
    @staticmethod
    def ensure_dir(path):
        """确保目录存在
        
        如果目录不存在则创建，并在类Unix系统上设置权限
        
        参数:
            path: 目录路径
        """
        os.makedirs(path, exist_ok=True)
        # 在类Unix系统上设置权限
        if platform.system() != 'Windows':
            os.chmod(path, 0o755)
    
    @staticmethod
    def get_log_dir(env_dir, component):
        """获取日志目录路径
        
        参数:
            env_dir: 环境目录名（prod/dev）
            component: 组件名称（tech/tweets等）
            
        返回:
            日志目录的完整路径
        """
        log_dir = PathUtils.normalize_path("logs", env_dir, component)
        PathUtils.ensure_dir(log_dir)
        return log_dir
    
    @staticmethod
    def get_data_dir(env_dir):
        """获取数据目录路径
        
        参数:
            env_dir: 环境目录名（prod/dev）
            
        返回:
            数据目录的完整路径
        """
        data_dir = PathUtils.normalize_path("data", env_dir)
        PathUtils.ensure_dir(data_dir)
        return data_dir 