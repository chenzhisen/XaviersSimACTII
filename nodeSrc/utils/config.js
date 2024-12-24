const dotenv = require('dotenv');
const path = require('path');

// 模仿 Python 的枚举类
const AIProvider = {
    ANTHROPIC: 'anthropic',
    XAI: 'xai'
};

class Config {
    static init() {
        dotenv.config();
        return this;
    }

    static getAIConfig() {
        const provider = process.env.AI_PROVIDER || AIProvider.XAI;
        const baseUrl = 'https://api.openai.com/v1'
        return {
            provider,
            apiKey: process.env.XAI_API_KEY,
            model:  process.env.XAI_MODEL,
            baseUrl
        };
    }

    static getStorageConfig() {
        return {
            dataDir: path.join(__dirname, '..', 'data'),
            cacheDir: path.join(__dirname, '..', '.cache')
        };
    }

    static getTwitterConfig() {
        return {
            bearerToken: process.env.TWITTER_BEARER_TOKEN,
            apiKey: process.env.TWITTER_API_KEY,
            apiSecret: process.env.TWITTER_API_SECRET,
            accessToken: process.env.TWITTER_ACCESS_TOKEN,
            accessTokenSecret: process.env.TWITTER_ACCESS_TOKEN_SECRET
        };
    }
}

module.exports = { Config, AIProvider }; 