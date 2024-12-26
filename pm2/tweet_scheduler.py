#!/usr/bin/env python3
import sys
import os
import time
import schedule
import subprocess
from datetime import datetime

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)

def run_auto_tweet(is_production=False):
    """运行auto_tweet.py"""
    try:
        print(f"\n=== 开始执行自动发推 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
        
        # 构建命令
        cmd = [sys.executable, os.path.join(project_root, 'src', 'twitter', 'auto_tweet.py')]
        if is_production:
            cmd.extend(['--no-dry-run', '--prod'])  # 生产环境参数
        else:
            cmd.append('--no-dry-run')  # 开发环境参数
            
        # 执行命令
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # 实时输出日志
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                
        # 获取错误输出
        _, stderr = process.communicate()
        if stderr:
            print("错误信息:", stderr)
            
        # 检查返回码
        if process.returncode == 0:
            print("发推执行成功")
        else:
            print(f"发推执行失败，返回码: {process.returncode}")
            
    except Exception as e:
        print(f"执行出错: {str(e)}")
    finally:
        print(f"=== 执行结束 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")

def main(is_production=False):
    print(f"自动发推定时任务启动")
    print(f"运行环境: {'生产环境' if is_production else '开发环境'}")
    print(f"定时设置: 每小时的0分和30分")
    
    # 设置定时任务
    schedule.every().hour.at(":00").do(run_auto_tweet, is_production)
    
    schedule.every().hour.at(":30").do(run_auto_tweet, is_production)
   
   
    # 立即执行一次
   # run_auto_tweet(is_production)
    
    # 持续运行
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n收到停止信号，正在退出...")
            break
        except Exception as e:
            print(f"运行出错: {str(e)}")
            time.sleep(60)  # 出错后等待1分钟

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='自动发推定时任务')
    parser.add_argument('--prod', action='store_true', help='使用生产环境')
    args = parser.parse_args()
    
    main(is_production=args.prod) 