const { program } = require('commander');
const ora = require('ora');
const XavierSimulation = require('./simulation');
const { Config } = require('./utils/config');
const { Logger } = require('./utils/logger');
const { initializeDataStructure } = require('./utils/init_data');

class SimulationRunner {
    constructor() {
        this.logger = new Logger('main');
    }

    async initialize() {
        try {
            // 初始化配置
            Config.init();
            
            // 初始化数据结构
            await initializeDataStructure();
            
            this.logger.info('Initialization completed');
            return true;
        } catch (error) {
            this.logger.error('Initialization failed', error);
            return false;
        }
    }

    async run(options) {
        const spinner = ora('Starting simulation...').start();
        
        try {
            const simulation = new XavierSimulation(options.production);
            const result = await simulation.run();
            
            spinner.succeed('Story generation completed');
            this.logger.info('Generated content:', {
                tweetCount: result.tweets.length,
                currentAge: result.currentAge,
                hasDigest: !!result.digest
            });

            return true;
        } catch (error) {
            spinner.fail('Simulation failed');
            this.logger.error('Simulation error', error);
            return false;
        }
    }
}

// 主程序
async function main() {
    const runner = new SimulationRunner();
    
    if (!await runner.initialize()) {
        process.exit(1);
    }

    program
        .command('run')
        .description('Run the story simulation')
        .option('-p, --production', 'Run in production mode')
        .action(async (options) => {
            const success = await runner.run(options);
            process.exit(success ? 0 : 1);
        });

    program.parse();
}

main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
}); 