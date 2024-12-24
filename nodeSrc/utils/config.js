const dotenv = require('dotenv');
const path = require('path');

class Config {
    static init() {
        dotenv.config();
        console.log('Environment variables loaded:', {
            ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY ? '***' + process.env.ANTHROPIC_API_KEY.slice(-4) : 'undefined',
            ANTHROPIC_MODEL: process.env.ANTHROPIC_MODEL,
            AI_BASE_URL: process.env.AI_BASE_URL
        });
        return this;
    }

    static getAIConfig() {
        const config = {
            apiKey: process.env.ANTHROPIC_API_KEY,
            model: process.env.ANTHROPIC_MODEL || 'claude-3-sonnet-20240229',
            baseUrl: process.env.AI_BASE_URL || 'https://api.anthropic.com/v1'
        };
        // console.log('AI Config:', {
        //     apiKey: config.apiKey ? '***' + config.apiKey.slice(-4) : 'undefined',
        //     model: config.model,
        //     baseUrl: config.baseUrl
        // });
        return config;
    }

    static getStorageConfig() {
        return {
            dataDir: path.join(__dirname, '..', 'data'),
            cacheDir: path.join(__dirname, '..', '.cache')
        };
    }
}

module.exports = { Config }; 