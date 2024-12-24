const { Anthropic } = require('@anthropic-ai/sdk');
const { Logger } = require('./logger');
const { Config } = require('./config');

class AICompletion {
    constructor(client, model, baseUrl) {
        this.logger = new Logger('ai');
        const aiConfig = Config.getAIConfig();
        if (client) {
            console.log('client 11', client.messages);
        }
        if (client) {
            this.client = client;
            this.model = aiConfig.model;
            this.baseUrl = aiConfig.baseUrl;
        } else {
            this.model = aiConfig.model;
            this.baseUrl = aiConfig.baseUrl;
            this.client = new Anthropic({
                apiKey: aiConfig.apiKey,
                baseURL: this.baseUrl
            });
            // console.log('AI Client initialized:', {
            //     model: this.model,
            //     hasClient: this.client.messages.create
            // });
        }
        // return this.client
    }

    async getCompletion(systemPrompt, userPrompt, options = {}) {
        console.log('systemPrompt', systemPrompt);
        console.log('userPrompt', userPrompt);

        try {
            // console.log('this.model', this.model);
            // const response = await this.client.messages.create({
            //     model: this.model,
            //     system: systemPrompt,
            //     messages: [{ role: "user", content: "Hello, Claude" }],
            //     temperature: options.temperature || 0.7,
            //     max_tokens: options.max_tokens || 1000
            // });
            // console.log('response', response);
            // return response.content[0].text;
            const msg = await this.client.messages.create({
                model:"grok-beta",
                max_tokens: 1024,
                messages: [{ role: "user", content: "Hello, Claude" }],
              });
              console.log(msg);
        } catch (error) {
            this.logger.error('Error in AI completion', error);
            throw error;
        }
    }
}

module.exports = { AICompletion }; 