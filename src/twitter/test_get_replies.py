import sys
import os

# Add the root directory of the project to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from twitter_client import TwitterClientV2
import time
from pprint import pprint

def test_get_replies():
    """测试获取推文回复的功能"""
    try:
        # 初始化 Twitter 客户端
        print("初始化 Twitter 客户端...")
        client = TwitterClientV2()

        # 步骤1：发送一条测试推文
        print("\n发送测试推文...")
        main_tweet_text = f"这是一条测试推文，用于测试获取回复功能 🧪 #{time.strftime('%Y%m%d_%H%M%S')}"
       # main_tweet_id = client.post_tweet(main_tweet_text)
        # if not main_tweet_id:
        #     raise Exception("发送主推文失败")
        # print(f"主推文已发送，ID: {main_tweet_id}")
        main_tweet_id = "1871899627718590937"
        # 步骤2：发送几条回复
        print("\n发送测试回复...")
        reply_ids = []
        for i in range(3):
            reply_text = f"这是第 {i+1} 条测试回复 🔄 {time.strftime('%H:%M:%S')}"
            reply_id = client.reply_to_tweet(reply_text, main_tweet_id)
            if reply_id:
                reply_ids.append(reply_id)
                print(f"回复 {i+1} 已发送，ID: {reply_id}")
            time.sleep(2)  # 避免请求过快

        # 步骤3：等待一段时间确保回复已被索引
        wait_time = 10
        print(f"\n等待 {wait_time} 秒让回复被索引...")
        time.sleep(wait_time)

        # 步骤4：获取并显示回复
        print("\n获取回复...")
        replies = client.get_replies(main_tweet_id)
        
        if replies and 'data' in replies:
            print(f"\n找到 {len(replies['data'])} 条回复:")
            for i, reply in enumerate(replies['data'], 1):
                print(f"\n回复 {i}:")
                print(f"ID: {reply['id']}")
                print(f"内容: {reply['text']}")
                print(f"创建时间: {reply.get('created_at', 'unknown')}")
                print(f"作者ID: {reply.get('author_id', 'unknown')}")
                print("-" * 50)
        else:
            print("\n未找到回复或响应格式不正确")
            pprint(replies)

        # 步骤5：清理测试推文（可选）
        print("\n是否要删除测试推文？(y/n)")
        if input().lower() == 'y':
            print("删除测试推文...")
            if client.delete_tweet(main_tweet_id):
                print("测试推文已删除")
            for reply_id in reply_ids:
                if client.delete_tweet(reply_id):
                    print(f"回复 {reply_id} 已删除")
                time.sleep(1)

    except Exception as e:
        print(f"\n测试失败: {str(e)}")
        raise

def main():
    print("开始测试获取回复功能...")
    try:
        test_get_replies()
        print("\n测试完成! 🎉")
    except Exception as e:
        print(f"\n测试失败: {str(e)}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main()) 