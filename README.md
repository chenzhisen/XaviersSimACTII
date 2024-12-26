# Xavier's Sim ACT II

这是一个自动化的Twitter互动系统，用于模拟Xavier的行为并与粉丝互动。

## 功能特性

- 自动发送推文
- 自动获取和保存推文回复
- 支持开发和生产环境
- 智能回复生成
- 用户互动管理

## 目录结构

```
.
├── nodeSrc/
│   ├── data/
│   │   ├── dev/    # 开发环境数据
│   │   └── prod/   # 生产环境数据
│   ├── generation/ # 推文生成相关代码
│   └── utils/      # 工具函数
└── src/
    └── twitter/    # Twitter API 相关代码
```

## 环境配置

1. 安装 Python 依赖：
```bash
pip install -r requirements.txt
```

2. 配置 Twitter API 凭证：
- 在项目根目录创建 `.env` 文件
- 添加以下配置：
```env
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
```

## 使用方法

### 1. 自动发送推文 (auto_tweet.py)

```bash
# 开发环境，测试模式（默认）
python src/twitter/auto_tweet.py

# 开发环境，实际发送
python src/twitter/auto_tweet.py --no-dry-run

# 生产环境，测试模式
python src/twitter/auto_tweet.py --prod

# 生产环境，实际发送
python src/twitter/auto_tweet.py --prod --no-dry-run
```

参数说明：
- `--prod`: 使用生产环境（使用 `nodeSrc/data/prod` 目录）
- `--no-dry-run`: 实际发送推文（默认为测试模式）

运行效果：
- 测试模式：不会实际发送推文，只会模拟发送
- 实际发送：会真实发送推文到 Twitter
- 开发环境：使用 `dev` 目录的数据文件
- 生产环境：使用 `prod` 目录的数据文件

### 2. 获取推文回复

```bash
# 开发环境（默认）
python src/twitter/fetch_tweets_scheduler.py

# 生产环境
python src/twitter/fetch_tweets_scheduler.py --prod
```

### 3. 数据文件说明

- `tweets_public.json`: 待发送的推文
- `sent_tweets.json`: 已发送的推文记录
- `tweet_replies.json`: 推文回复数据

## 开发/生产环境

系统支持两种运行环境：

1. 开发环境 (dev)
   - 数据存储在 `nodeSrc/data/dev/` 目录
   - 用于本地测试和开发
   - 默认启用

2. 生产环境 (prod)
   - 数据存储在 `nodeSrc/data/prod/` 目录
   - 用于实际运行
   - 使用 `--prod` 参数启用

## 注意事项

1. 确保在运行前已正确配置 Twitter API 凭证
2. 开发环境和生产环境使用不同的数据目录，避免数据混淆
3. 建议先在开发环境测试无误后再切换到生产环境
4. 定期备份生产环境的数据文件

## 错误处理

- 如果遇到 API 限制，系统会自动等待并重试
- 文件操作使用临时文件和原子操作确保数据安全
- 详细的错误日志会打印到控制台

## 贡献指南

1. Fork 本仓库
2. 创建特性分支
3. 提交更改
4. 发起 Pull Request

## 许可证

MIT License
