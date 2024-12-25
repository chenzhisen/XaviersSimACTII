const { program } = require('commander');
const ora = require('ora');
const { XavierSimulation } = require('./simulation');
const { Config } = require('./utils/config');
const { Logger } = require('./utils/logger');
const { initializeDataStructure } = require('./utils/init_data');
const { CommentHandler } = require('./interaction/comment_handler');

class SimulationRunner {
    constructor() {
        this.logger = new Logger('main');
        
        // 初始化评论处理器
        const aiConfig = Config.getAIConfig();
        this.commentHandler = new CommentHandler(null, aiConfig.model);
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
            // 运行主要模拟
            const simulation = new XavierSimulation(options.production);
            const result = await simulation.run();
            
            // 处理新评论
            await this.commentHandler.handleNewComments();
            
            spinner.succeed('Simulation and interaction completed');
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
        .description('Run the simulation')
        .option('-p, --production', 'Run in production mode')
        .action(async (options) => {
            const success = await runner.run(options);
            process.exit(success ? 0 : 1);
        });

    program.parse();
}

// 启动程序
main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
}); 