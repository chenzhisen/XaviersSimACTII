const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

// 获取项目根目录
const projectRoot = path.resolve(__dirname, '..');

// 确保目录存在
function ensureDirectoryExists(dirPath) {
    if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
    }
}

// 初始化必要的目录
function initializeDirectories() {
    const dirs = [
        path.join(projectRoot, 'nodeSrc', 'data', 'prod'),
        path.join(projectRoot, 'nodeSrc', 'data', 'dev'),
        path.join(projectRoot, 'logs')
    ];

    dirs.forEach(dir => ensureDirectoryExists(dir));
}

function runCommand() {
    console.log('=== 开始执行生产环境命令 ===');
    console.log('时间:', new Date().toLocaleString());
    console.log('工作目录:', projectRoot);

    // 执行npm命令
    const child = exec('npm run start:prod', {
        cwd: projectRoot
    });

    // 输出信息
    child.stdout.on('data', (data) => {
        console.log(data.toString());
    });

    // 输出错误
    child.stderr.on('data', (data) => {
        console.error('错误:', data.toString());
    });

    // 命令执行完成
    child.on('close', (code) => {
        console.log(`命令执行完成，退出码: ${code}`);
        console.log('=== 执行结束 ===\n');
    });
}

// 初始化目录
initializeDirectories();

// 首次执行
runCommand();

// 每5分钟执行一次
setInterval(runCommand, 5 * 60 * 1000); 