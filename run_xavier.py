#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
from datetime import datetime
import colorama  # 用于跨平台的颜色输出

# 初始化 colorama
colorama.init()

class Colors:
    """颜色定义"""
    GREEN = '\033[92m'    # 成功
    RED = '\033[91m'      # 错误
    YELLOW = '\033[93m'   # 警告
    BLUE = '\033[94m'     # 信息
    RESET = '\033[0m'     # 重置颜色

def print_success(msg):
    """打印成功信息"""
    print(f"{Colors.GREEN}{msg}{Colors.RESET}")

def print_error(msg):
    """打印错误信息"""
    print(f"{Colors.RED}{msg}{Colors.RESET}")

def print_warning(msg):
    """打印警告信息"""
    print(f"{Colors.YELLOW}{msg}{Colors.RESET}")

def print_info(msg):
    """打印普通信息"""
    print(f"{Colors.BLUE}{msg}{Colors.RESET}")

def setup_environment():
    """设置运行环境"""
    print_info("\n=== 设置运行环境 ===")
    
    # 设置 PYTHONPATH
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ['PYTHONPATH'] = root_dir
    print_success(f"- PYTHONPATH: {root_dir}")
    
    # 创建必要的目录
    dirs = [
        os.path.join('logs', 'dev', 'tech'),
        os.path.join('logs', 'dev', 'tweets'),
        os.path.join('data', 'dev'),
        os.path.join('data', 'prod')
    ]
    
    for dir_path in dirs:
        try:
            os.makedirs(dir_path, exist_ok=True)
            print_success(f"- 创建目录成功: {dir_path}")
        except Exception as e:
            print_error(f"- 创建目录失败: {dir_path}")
            print_error(f"  错误: {str(e)}")
    
    # 设置文件权限（仅在类Unix系统）
    if platform.system() != 'Windows':
        try:
            for dir_path in dirs:
                os.chmod(dir_path, 0o755)
            print_success("- 设置目录权限: 755")
        except Exception as e:
            print_warning(f"- 设置权限失败: {str(e)}")

def install_dependencies():
    """安装依赖包"""
    print_info("\n=== 安装依赖 ===")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        print_success("- 依赖安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"- 依赖安装失败: {e}")
        return False

def run_xavier():
    """运行主程序"""
    print_info("\n=== 运行 Xavier ===")
    try:
        start_time = datetime.now()
        print_info(f"- 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        cmd = [sys.executable, 'src/main.py', '--provider', 'xai']
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # 实时输出程序日志
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                # 根据输出内容添加颜色
                line = output.strip()
                if "错误" in line or "Error" in line or "失败" in line:
                    print_error(line)
                elif "警告" in line or "Warning" in line:
                    print_warning(line)
                elif "成功" in line or "Success" in line:
                    print_success(line)
                else:
                    print(line)
        
        # 检查返回码
        return_code = process.poll()
        end_time = datetime.now()
        duration = end_time - start_time
        
        if return_code == 0:
            print_success(f"\n- 程序运���成功")
            print_success(f"- 运行时间: {duration}")
        else:
            print_error(f"\n- 程序运行失败 (返回码: {return_code})")
            print_error(f"- 运行时间: {duration}")
            # 输出错误信息
            errors = process.stderr.read()
            if errors:
                print_error("错误详情:")
                print_error(errors)
            sys.exit(1)
            
    except Exception as e:
        print_error(f"- 运行出错: {str(e)}")
        sys.exit(1)

def main():
    print_info(f"平台: {platform.system()}")
    print_info(f"Python版本: {sys.version}")
    
    setup_environment()
    if not install_dependencies():
        print_error("依赖安装失败，程序退出")
        sys.exit(1)
    run_xavier()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print_error(f"\n程序异常退出: {str(e)}")
        sys.exit(1) 