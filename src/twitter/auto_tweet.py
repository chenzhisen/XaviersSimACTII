import sys
import os
import json
import time
from datetime import datetime
from twitter_client import TwitterClientV2

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

class AutoTweeter:
    def __init__(self):
        """初始化自动发推器"""
        self.client = TwitterClientV2()
        self.data_dir = "tweets_archive"
        self._ensure_data_directory()

    def _ensure_data_directory(self):
        """确保数据保存目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            print(f"创建数据目录: {self.data_dir}")

    def _get_timestamp(self):
        """获取当前时间戳字符串"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def save_tweet_data(self, tweet_id, tweet_text, response_data):
        """保存推特数据到JSON文件
        
        Args:
            tweet_id (str): 推特ID
            tweet_text (str): 推特内容
            response_data (dict): API响应数据
        """
        timestamp = self._get_timestamp()
        filename = os.path.join(self.data_dir, f"tweet_{timestamp}.json")
        
        data = {
            "tweet_id": tweet_id,
            "content": tweet_text,
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "api_response": response_data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已保存推特数据到: {filename}")

        # 同时更新推特ID列表
        id_file = os.path.join(self.data_dir, "tweet_ids.json")
        try:
            if os.path.exists(id_file):
                with open(id_file, 'r', encoding='utf-8') as f:
                    id_data = json.load(f)
            else:
                id_data = {"tweets": []}
            
            id_data["tweets"].append({
                "id": tweet_id,
                "timestamp": timestamp,
                "content": tweet_text
            })
            
            with open(id_file, 'w', encoding='utf-8') as f:
                json.dump(id_data, f, ensure_ascii=False, indent=2)
            print("已更新推特ID列表")
        except Exception as e:
            print(f"更新推特ID列表时出错: {e}")

    def post_tweet(self, text):
        """发布推特并保存数据
        
        Args:
            text (str): 推特内容
            
        Returns:
            str: 成功时返回推特ID，失败时返回None
        """
        try:
            # 发布推特
            tweet_id = self.client.post_tweet(text)
            if not tweet_id:
                print("发布推特失败")
                return None
            
            print(f"推特发布成功，ID: {tweet_id}")
            
            # 直接保存推特数据
            self.save_tweet_data(tweet_id, text, {"id": tweet_id, "text": text})
            
            return tweet_id
            
        except Exception as e:
            print(f"发布推特时发生错误: {e}")
            return None

def main():
    """主函数"""
    tweeter = AutoTweeter()
    
    # 示例：发布一条测试推特
    tweet_text = f"这是一条自动发布的测试推特 🤖 #{time.strftime('%Y%m%d_%H%M%S')}"
    tweet_id = tweeter.post_tweet(tweet_text)
    
    if tweet_id:
        print("推特发布并保存成功！")
    else:
        print("推特发布失败")

if __name__ == "__main__":
    main() 