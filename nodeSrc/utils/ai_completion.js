const OpenAI = require('openai');
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
            this.model = aiConfig.model || 'gpt-4';
            this.client = new OpenAI({
                apiKey: aiConfig.apiKey,
                baseURL: aiConfig.baseUrl
            });
        }
        
        console.log('AI Client initialized:', {
            model: this.model,
            hasClient: !!this.client
        });
    }

    async getCompletion(systemPrompt, userPrompt, options = {}) {
        try {
          

            const response = await this.client.chat.completions.create({
                model: this.model,
                messages: [
                    {
                        role: "system",
                        content:
                            "You are Grok, a chatbot inspired by the Hitchhiker's Guide to the Galaxy.",
                    },
                    {
                        role: "user",
                        content:
                            "What is the meaning of life, the universe, and everything?",
                    },
                ],
            });

            console.log('AI Response:', response);

            return response.choices[0].message.content;
        } catch (error) {
            this.logger.error('Error in AI completion', error);
            console.error('Detailed error:', {
                name: error.name,
                message: error.message,
                status: error.status,
                response: error.response
            });
            throw error;
        }
    }
}

module.exports = { AICompletion }; 