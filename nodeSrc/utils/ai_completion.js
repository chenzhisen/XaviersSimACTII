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
            this.model = aiConfig.model;
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
            console.log('Sending request:', {
                model: this.model,
                systemPrompt: systemPrompt?.slice(0, 50) + '...',
                userPrompt: userPrompt?.slice(0, 50) + '...'
            });

            // 重试机制
            const maxRetries = 3;
            const retryDelay = 5000; // 5秒
            let attempt = 0;

            while (attempt < maxRetries) {
                try {
                    const response = await this.client.chat.completions.create({
                        model: this.model,
                        messages: [
                            { role: 'system', content: systemPrompt },
                            { role: 'user', content: userPrompt }
                        ],
                        temperature: options.temperature || 0.7,
                        max_tokens: options.max_tokens || 1000
                    });

                    console.log('AI Response received:', {
                        status: 'success',
                        hasChoices: !!response.choices,
                        contentLength: response.choices?.[0]?.message?.content?.length
                    });

                    return response.choices[0].message.content;

                } catch (error) {
                    attempt++;
                    console.error(`Attempt ${attempt} failed:`, {
                        error: error.message,
                        status: error.status,
                        type: error.type
                    });

                    if (attempt === maxRetries) {
                        throw error;
                    }

                    // 等待后重试
                    await new Promise(resolve => setTimeout(resolve, retryDelay));
                }
            }

        } catch (error) {
            this.logger.error('Error in AI completion', error);
            console.error('Detailed error:', {
                name: error.name,
                message: error.message,
                status: error.status,
                type: error.type,
                response: error.response
            });
            throw error;
        }
    }
}

module.exports = { AICompletion }; 