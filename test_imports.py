def test_import(module_name):
    try:
        if module_name == "github":
            from github import Github
        else:
            __import__(module_name)
        print(f"✅ {module_name} 导入成功")
    except ImportError as e:
        print(f"❌ {module_name} 导入失败: {e}")

# 逐个测试导入
modules = [
    "requests",
    "dotenv",
    "anthropic",
    "openai",
    "tweepy",
    "github"
]

for module in modules:
    test_import(module) 