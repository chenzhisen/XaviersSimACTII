module.exports = {
  apps: [
    // Node.js 生产环境定时任务
    {
      name: 'xavier-prod',
      script: '../nodeSrc/prod_scheduler.js',
      cwd: __dirname,
      watch: false,
      autorestart: true,
      max_memory_restart: '1G',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        NODE_ENV: 'production'
      }
    },
    // Python 自动发推定时任务
    {
      name: 'xavier-tweet',
      script: './tweet_scheduler.py',
      interpreter: 'python3',
      cwd: __dirname,
      watch: false,
      autorestart: true,
      max_memory_restart: '1G',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      args: '--prod',  // 生产环境参数
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'  // 确保Python输出不被缓存
      }
    },
    // Python 抓取推文定时任务
    {
      name: 'xavier-fetch',
      script: './fetch_scheduler.py',
      interpreter: 'python3',
      cwd: __dirname,
      watch: false,
      autorestart: true,
      max_memory_restart: '1G',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      args: '--prod',  // 生产环境参数
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'  // 确保Python输出不被缓存
      }
    }
  ]
}; 