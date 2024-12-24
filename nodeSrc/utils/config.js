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
        const baseUrl = provider === AIProvider.XAI ? 'https://api.x.ai/v1' : 'https://api.anthropic.com/v1';

        return {
            provider,
            apiKey: provider === AIProvider.XAI ? process.env.XAI_API_KEY : process.env.ANTHROPIC_API_KEY,
            model: provider === AIProvider.XAI ? process.env.XAI_MODEL : process.env.ANTHROPIC_MODEL,
            baseUrl
        };
    }

    static getStorageConfig() {
        return {
            githubToken: process.env.GITHUB_TOKEN,
            githubOwner: process.env.GITHUB_OWNER,
            githubRepo: process.env.GITHUB_REPO,
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