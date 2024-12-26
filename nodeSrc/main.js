const { program } = require('commander');
let spinner;

async function initSpinner() {
    const ora = (await import('ora')).default;
    spinner = ora('正在初始化...');
    return spinner;
}

const XavierSimulation = require('./simulation');
const { Config } = require('./utils/config');
const { Logger } = require('./utils/logger');
const { initializeDataStructure } = require('./utils/init_data');

class SimulationRunner {
    constructor() {
        this.logger = new Logger('main');
        this.simulation = null;
    }

    async initialize(options = {}) {
        try {
            // 初始化配置
            Config.init();
            
            // 初始化数据结构
            await initializeDataStructure(options.production);
            
            this.logger.info('Initialization completed');
            return true;
        } catch (error) {
            this.logger.error('Initialization failed', error);
            return false;
        }
    }

    async run(options) {
        spinner = await initSpinner();
        spinner.start();
        console.log('run options',options);
        try {
            this.simulation = new XavierSimulation(options.production);
            
            if (options.continuous) {
                // 持续运行模式
                spinner.succeed('Starting continuous simulation');
                await this.simulation.start();
            } else {
                // 单次运行模式
                const result = await this.simulation.runOnce();
                spinner.succeed('Simulation completed');
                this.logger.info('Generated content:', {
                    tweets: result.tweets.length,
                    hasDigest: !!result.digest,
                    currentAge: result.currentAge
                });
            }
            
            return true;
        } catch (error) {
            spinner.fail('Simulation failed');
            this.logger.error('Simulation error', error);
            return false;
        }
    }

    stop() {
        if (this.simulation) {
            this.simulation.stop();
        }
    }
}

// 主程序
async function main() {
    spinner = await initSpinner();
    spinner.start();
    const runner = new SimulationRunner();
    
    program
        .command('run')
        .description('Run the story simulation')
        .option('-p, --production', 'Run in production mode')
        .option('-c, --continuous', 'Run continuously')
        .action(async (options) => {
            if (!await runner.initialize(options)) {
                process.exit(1);
            }
            const success = await runner.run(options);
            if (!options.continuous) {
                process.exit(success ? 0 : 1);
            }
        });

    // 处理进程终止信号
    process.on('SIGINT', () => {
        console.log('\nReceived SIGINT. Gracefully shutting down...');
        runner.stop();
    });

    process.on('SIGTERM', () => {
        console.log('\nReceived SIGTERM. Gracefully shutting down...');
        runner.stop();
    });

    program.parse();
}

main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
}); 