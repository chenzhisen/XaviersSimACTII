module.exports = {
  apps: [{
    name: 'xavier-prod',
    script: './prod_scheduler.js',
    cwd: __dirname,
    watch: false,
    autorestart: true,
    max_memory_restart: '1G',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    env: {
      NODE_ENV: 'production'
    }
  }]
}; 