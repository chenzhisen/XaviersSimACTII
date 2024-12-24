const { Anthropic } = require('@anthropic-ai/sdk');
const axios = require('axios');
const { Logger } = require('./logger');
const { Config, AIProvider } = require('./config');

class AICompletion {
    constructor(client, model, baseUrl) {
        model='grok-beta'
        baseUrl='https://api.openai.com/v1'
        this.logger = new Logger('ai');
        const aiConfig = Config.getAIConfig();
        
        if (client) {
            this.client = client;
            this.model = model;
            this.baseUrl = baseUrl;
        } else {
            this.model = aiConfig.model;
            if (aiConfig.provider === AIProvider.XAI) {
                this.baseUrl = aiConfig.baseUrl;
                this.apiKey = aiConfig.apiKey;
                this.client = new Anthropic({
                    apiKey: aiConfig.apiKey,
                    baseURL: aiConfig.baseUrl
                });
            } else {
                this.client = new Anthropic({
                    apiKey: aiConfig.apiKey,
                    baseURL: aiConfig.baseUrl
                });
            }
        }
    }

    async getCompletion(systemPrompt, userPrompt, options = {}) {
        try {
            if (this.client instanceof Anthropic) {
                const response = await this.client.messages.create({
                    model: this.model,
                    system: systemPrompt,
                    messages: [{ role: 'user', content: userPrompt }],
                    temperature: options.temperature || 0.7,
                    max_tokens: options.max_tokens || 1000
                });
                return response.content[0].text;
            } else {
                const response = await this.client.post('/chat/completions', {
                    model: this.model,
                    messages: [
                        { role: 'system', content: systemPrompt },
                        { role: 'user', content: userPrompt }
                    ],
                    temperature: options.temperature || 0.7,
                    max_tokens: options.max_tokens || 1000
                });
                return response.data.choices[0].message.content;
            }
        } catch (error) {
            this.logger.error('Error in AI completion', error);
            throw error;
        }
    }
}

module.exports = { AICompletion }; 