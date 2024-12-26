# Xavier's Sim ACT II - Node.js 部分

这是项目的 Node.js 部分，主要负责推文生成、数据管理和工具函数。

## 目录结构

```
nodeSrc/
├── data/              # 数据文件目录
│   ├── dev/          # 开发环境数据
│   │   ├── tweets_public.json    # 待发送推文
│   │   ├── sent_tweets.json      # 已发送推文
│   │   └── tweet_replies.json    # 推文回复
│   └── prod/         # 生产环境数据（结构同dev）
├── generation/        # 推文生成相关代码
│   ├── tweet_generator.js   # 推文生成器
│   └── story_builder.js     # 故事构建器
├── utils/            # 工具函数
│   ├── init_data.js        # 数据初始化
│   ├── data_manager.js     # 数据管理
│   ├── data_migration.js   # 数据迁移
│   ├── logger.js           # 日志工具
│   └── path_utils.js       # 路径工具
└── storage/          # 存储相关
    └── github_operations.js # GitHub操作
```

## 环境配置

1. 安装依赖：
```bash
cd nodeSrc
npm install
```

2. 配置环境变量：
- 复制 `.env.example` 到 `.env`
- 填写必要的配置信息

## 主要功能

### 1. 推文生成 (generation/)

- `tweet_generator.js`: 生成推文内容
- `story_builder.js`: 构建故事情节

### 2. 数据管理 (utils/)

- 数据初始化：`init_data.js`
- 数据迁移：`data_migration.js`
- 数据管理：`data_manager.js`

### 3. 工具函数 (utils/)

- 日志记录：`logger.js`
- 路径处理：`path_utils.js`

### 4. 存储操作 (storage/)

- GitHub 操作：`github_operations.js`

## 开发/生产环境

### 开发环境

```bash
# 初始化开发环境数据
npm run init

# 运行程序（开发模式）
npm run start:dev
```

### 生产环境

```bash
# 初始化生产环境数据
npm run init:prod

# 运行程序（生产模式）
npm run start:prod
```

## 数据文件

### 1. tweets_public.json
```json
[
  {
    "id": "unique_id",
    "content": "推文内容",
    "created_at": "2023-01-01T00:00:00Z"
  }
]
```

### 2. sent_tweets.json
```json
[
  {
    "id": "tweet_id",
    "content": "已发送的推文内容",
    "sent_at": "2023-01-01T00:00:00Z"
  }
]
```

### 3. tweet_replies.json
```json
{
  "tweet_id": {
    "tweet": {
      "id": "tweet_id",
      "content": "原推文内容"
    },
    "replies": [
      {
        "id": "reply_id",
        "username": "user_name",
        "content": "回复内容"
      }
    ]
  }
}
```

## 错误处理

- 所有操作都有错误日志记录
- 文件操作使用原子写入确保数据安全
- 自动备份重要数据

## 开发指南

1. 代码风格
   - 使用 ES6+ 语法
   - 使用 async/await 处理异步
   - 保持代码简洁清晰

2. 错误处理
   - 使用 try/catch 捕获错误
   - 记录详细的错误信息
   - 优雅降级处理异常情况

3. 数据安全
   - 使用临时文件进行原子写入
   - 定期备份数据
   - 验证数据完整性

## 注意事项

1. 确保 Node.js 版本 >= 14.0.0
2. 开发环境和生产环境使用不同的数据记录
3. 定期检查和清理日志文件
4. 保持数据文件的备份 