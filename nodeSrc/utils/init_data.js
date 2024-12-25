const fs = require('fs').promises;
const path = require('path');
const { Logger } = require('./logger');

const logger = new Logger('init');

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

    try {
        // 确保数据目录存在
        await fs.mkdir(dataDir, { recursive: true });

        // 检查文件是否存在且不为空
        try {
            const content = await fs.readFile(dataPath, 'utf8');
            if (!content.trim()) {
                throw new Error('File is empty');
            }
            JSON.parse(content); // 验证JSON格式
            logger.info('Data file exists and is valid');
            return true;
        } catch (error) {
            // 文件不存在、为空或格式错误，创建新文件
            logger.info('Creating new data file');
            await fs.writeFile(
                dataPath,
                JSON.stringify(INITIAL_DATA, null, 2),
                'utf8'
            );
            logger.info('Data file initialized successfully');
            return true;
        }
    } catch (error) {
        logger.error('Failed to initialize data structure', error);
        throw error;
    }
}

module.exports = {
    initializeDataStructure,
    INITIAL_DATA
}; 