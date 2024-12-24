#!/usr/bin/env node

require('dotenv').config();
const { program } = require('commander');
const ora = require('ora');
const { XavierSimulation } = require('./main');
const { Config } = require('./utils/config');
const { Logger } = require('./utils/logger');
const { PathUtils } = require('./utils/path_utils');

// 初始化配置和目录
async function init() {
    Config.init();
    const logger = new Logger('index');

    try {
        // 创建必要的目录
        await PathUtils.ensureDir('data');
        await PathUtils.ensureDir('logs');
        await PathUtils.ensureDir('.cache');
        
        logger.info('Initialization completed');
    } catch (error) {
        logger.error('Initialization failed', error);
        process.exit(1);
    }
}

// 主程序
async function main() {
    await init();
    const logger = new Logger('index');

    program
        .command('run')
        .description('Run the simulation')
        .option('-p, --production', 'Run in production mode')
        .action(async (options) => {
            const spinner = ora('Starting simulation...').start();
            
            try {
                const simulation = new XavierSimulation(options.production);
                const result = await simulation.run();
                
                spinner.succeed('Simulation completed');
                logger.info('Generated content:', {
                    tweet: result.tweet.text,
                    age: result.tweet.age,
                    hasDigest: !!result.digest,
                    hasTech: !!result.techEvolution
                });
            } catch (error) {
                spinner.fail('Simulation failed');
                logger.error('Simulation error', error);
                process.exit(1);
            }
        });

    program.parse();
}

// 启动程序
main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
}); 