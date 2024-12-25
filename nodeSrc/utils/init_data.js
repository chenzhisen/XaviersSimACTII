const fs = require('fs').promises;
const path = require('path');
const { Logger } = require('./logger');

const logger = new Logger('init');

// 清理文件配置
const CLEANUP_CONFIG = {
    enabled: true,              // 是否启用清理
    targets: {
        mainFile: true,         // 是否清理 XaviersSim.json
        aiLogs: true           // 是否清理 ai_logs 目录
    }
};

const INITIAL_DATA = {
    metadata: {
        protagonist: 'Xavier',
        startAge: 22,
        currentAge: 22,
        currentPhase: 'early_career',
        lastUpdate: new Date().toISOString(),
        version: '1.0.0'
    },

    story: {
        tweets: [],
        digests: [{
            content: `Xavier is at a crossroads, seriously considering leaving college to focus on quant trading and his involvement with $XVI. This marks a significant shift in his life priorities and indicates a desire to take control of his future..`,
            timestamp: new Date().toISOString()
        }],
        keyPlotPoints: [],
        relationships: []
    },
    tech: {
        updates: [],
        currentState: {
            phase: 'early',
            focus: ['基础架构', '核心算法', '产品原型'],
            challenges: ['技术选型', '性能优化', '安全性'],
            lastUpdate: new Date().toISOString()
        }
    },
    career: {
        milestones: [],
        currentState: {
            role: '创始人/技术负责人',
            company: '$XVI Labs',
            stage: '初创期',
            team_size: 1
        }
    },
    personal: {
        relationships: {
            family: [],
            friends: [],
            colleagues: [],
            mentors: []
        },
        interests: [
            '编程',
            '区块链技术',
            '创业',
            '投资'
        ],
        traits: [
            '技术驱动',
            '创新思维',
            '持续学习',
            '追求卓越'
        ]
    },
    stats: {
        totalTweets: 0,
        digestCount: 0,
        techUpdateCount: 0,
        yearProgress: 0
    }
};

async function initializeDataStructure() {
    const dataPath = path.resolve(__dirname, '..', 'data', 'XaviersSim.json');
    const dataDir = path.dirname(dataPath);
    const aiLogsDir = path.resolve(dataDir, 'ai_logs');

    try {
        logger.info('Starting data initialization...', { cleanup: CLEANUP_CONFIG });

        // 根据配置清理文件
        if (CLEANUP_CONFIG.enabled) {
            // 清理主文件
            if (CLEANUP_CONFIG.targets.mainFile) {
                try {
                    await fs.unlink(dataPath);
                    logger.info('Deleted XaviersSim.json');
                } catch (error) {
                    if (error.code !== 'ENOENT') {
                        throw error;
                    }
                }
            }

            // 清理 AI 日志
            if (CLEANUP_CONFIG.targets.aiLogs) {
                try {
                    await fs.rm(aiLogsDir, { recursive: true, force: true });
                    logger.info('Deleted ai_logs directory');
                } catch (error) {
                    if (error.code !== 'ENOENT') {
                        throw error;
                    }
                }
            }
        } else {
            logger.info('File cleanup disabled');
        }

        // 确保数据目录存在
        await fs.mkdir(dataDir, { recursive: true });

        // 创建新的数据文件
        await fs.writeFile(
            dataPath,
            JSON.stringify(INITIAL_DATA, null, 2),
            'utf8'
        );

        logger.info('Data structure initialized successfully');
        return true;

    } catch (error) {
        logger.error('Failed to initialize data structure', error);
        throw error;
    }
}

module.exports = {
    initializeDataStructure,
    INITIAL_DATA,
    CLEANUP_CONFIG  // 导出配置以便其他模块使用
}; 