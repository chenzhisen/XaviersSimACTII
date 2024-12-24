const { Anthropic } = require('@anthropic-ai/sdk');
const { Logger } = require('./logger');
const { Config } = require('./config');

class AICompletion {
    constructor(client, model) {
        this.logger = new Logger('ai');
        const aiConfig = Config.getAIConfig();
        
        if (client) {
            this.client = client;
            this.model = model;
        } else {
            this.model = aiConfig.model || 'claude-3-sonnet-20240229';
            this.client = new Anthropic({
                apiKey: aiConfig.apiKey,
                baseURL: aiConfig.baseUrl
            });
        }
    }

    async getCompletion(systemPrompt, userPrompt, options = {}) {
        try {
            const response = await this.client.messages.create({
                model: this.model,
                system: systemPrompt,
                messages: [{ role: 'user', content: userPrompt }],
                temperature: options.temperature || 0.7,
                max_tokens: options.max_tokens || 1000
            });
            return response.content[0].text;
        } catch (error) {
            this.logger.error('Error in AI completion', error);
            throw error;
        }
    }
}

module.exports = { AICompletion }; 