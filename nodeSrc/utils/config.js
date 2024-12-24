const dotenv = require('dotenv');
const path = require('path');

class Config {
    static init() {
        dotenv.config();
        return this;
    }

    static getAIConfig() {
        return {
            apiKey: process.env.XAI_API_KEY,
            model: process.env.XAI_MODEL || 'gpt-4',
            baseUrl: 'https://api.openai.com/v1'
        };
    }

    static getStorageConfig() {
        return {
            dataDir: path.join(__dirname, '..', 'data'),
            cacheDir: path.join(__dirname, '..', '.cache')
        };
    }
}

module.exports = { Config }; 