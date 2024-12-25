const { Logger } = require('./logger');
const OpenAI = require('openai');
const dotenv = require('dotenv');
const { Config } = require('./config');
const chalk = require('chalk');
const fs = require('fs').promises;
const path = require('path');

class AICompletion {
    constructor(client, model, options = {}) {
        this.logger = new Logger('ai');
        const aiConfig = Config.getAIConfig();
            
        // 初始化 OpenAI 客户端
        if (client) {
            this.client = client;
            this.model = model;
            console.log(chalk.blue('Using provided AI client:', model));
        } else {
            this.model = aiConfig.model;
            this.client = new OpenAI({
                apiKey: aiConfig.apiKey,
                baseURL: aiConfig.baseUrl
            });
            console.log(chalk.blue('Initialized OpenAI client:', {
                model: this.model,
                baseURL: aiConfig.baseUrl
            }));
        }

        this.options = {
            useLocalSimulation: !this.client,
            ...options
        };

        console.log(chalk.blue('AI completion initialized:', {
            useLocalSimulation: this.options.useLocalSimulation,
            model: this.model
        }));

        // 添加日志路径
        this.logPath = path.resolve(__dirname, '..', 'data', 'ai_logs');
        this.consoleLogPath = path.join(this.logPath, 'console');

        this.systemPrompt = options.systemPrompt || '';
    }

    updateSystemPrompt(newPrompt) {
        this.systemPrompt = newPrompt;
    }

    async _logToConsoleAndFile(level, message, data = {}) {
        // 生成带时间戳的日志内容
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            level,
            message,
            data
        };

        // 控制台输出（带颜色）
        const colors = {
            info: 'blue',
            success: 'green',
            warning: 'yellow',
            error: 'red'
        };
        console.log(chalk[colors[level] || 'white'](message, data));

        try {
            // 确保日志目录存在
            await fs.mkdir(this.consoleLogPath, { recursive: true });

            // 生成日志文件名（按日期分文件）
            const date = new Date().toISOString().split('T')[0];
            const logFile = path.join(this.consoleLogPath, `console_${date}.log`);

            // 追加日志内容
            await fs.appendFile(
                logFile,
                JSON.stringify(logEntry) + '\n',
                'utf8'
            );
        } catch (error) {
            console.error('Error saving console log:', error);
        }
    }

    async getCompletion(systemMessage, userMessage) {
        try {
            if (this.options.useLocalSimulation) {
                return this._getLocalResponse(userMessage);
            }

            const messages = [
                { role: 'system', content: this.systemPrompt || systemMessage },
                { role: 'user', content: userMessage }
            ];

            let result;
            await this._logToConsoleAndFile('info', 'Calling OpenAI API');
            result = await this._getAICompletion(messages);

            await this._logToConsoleAndFile('success', 'Generated content', {
                mode: this.options.useLocalSimulation ? 'local' : 'api',
                tweetsCount: result.length,
                firstTweet: result[0]?.text?.substring(0, 50) + '...'
            });

            return result;
        } catch (error) {
            await this._logToConsoleAndFile('error', 'AI completion failed', error);
            throw error;
        }
    }

    async _getAICompletion(messages) {
        try {
            if (!this.client) {
                await this._logToConsoleAndFile('warning', 'No AI client available, using local simulation');
                return this._getLocalSimulation();
            }

            await this._logToConsoleAndFile('info', 'Making API request', {
                model: this.model,
                systemPrompt: this.systemPrompt?.substring(0, 50) + '...',
                userPrompt: messages[messages.length - 1].content?.substring(0, 50) + '...'
            });

            const response = await this.client.chat.completions.create({
                model: this.model,
                messages: messages
            });

            // 保存交互记录
            await this._saveInteraction({
                timestamp: new Date().toISOString(),
                model: this.model,
                systemPrompt: this.systemPrompt,
                userPrompt: messages[messages.length - 1].content,
                response: response.choices[0].message.content,
                success: true
            });

            await this._logToConsoleAndFile('success', 'API response received', {
                status: 'success',
                content: response.choices[0].message.content?.substring(0, 50) + '...'
            });

            const tweets = this._parseAIResponse(response.choices[0].message.content);
            return tweets;
        } catch (error) {
            // 保存错误记录
            await this._saveInteraction({
                timestamp: new Date().toISOString(),
                model: this.model,
                systemPrompt: this.systemPrompt,
                userPrompt: messages[messages.length - 1].content,
                error: error.message,
                success: false
            });

            await this._logToConsoleAndFile('error', 'AI API call failed', {
                error: error.message,
                model: this.model
            });
            await this._logToConsoleAndFile('warning', 'Falling back to local simulation');
            return this._getLocalSimulation();
        }
    }

    async _saveInteraction(data) {
        try {
            // 确保日志目录存在
            await fs.mkdir(this.logPath, { recursive: true });

            // 生成文件名
            const filename = `ai_interaction_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
            const filepath = path.join(this.logPath, filename);

            // 保存交互记录
            await fs.writeFile(
                filepath,
                JSON.stringify(data, null, 2),
                'utf8'
            );

            console.log(chalk.blue('Interaction log saved:', filepath));
        } catch (error) {
            console.log(chalk.red('Error saving interaction log:', error));
        }
    }

    _getLocalSimulation() {
        console.log(chalk.yellow('Generating local simulation content'));
        
        // 模拟 AI 生成
        const scenes = [
            this._generateScene('工作场景'),
            this._generateScene('生活场景'),
            this._generateScene('社交场景')
        ];

        // 将场景转换为推文格式
        const tweets = scenes.flatMap(scene => scene.map((text, index) => ({
            text,
            id: `tweet_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        })));

        console.log(chalk.green('Local simulation completed:', {
            scenesCount: scenes.length,
            tweetsCount: tweets.length
        }));

        return tweets;
    }

    _generateScene(type) {
        const templates = {
            '工作场景': [
                [
                    "1: 凌晨3点，第108次修改代码。这个bug太难找了，但我知道答案就在眼前。泡一杯咖啡，继续战斗。#coding #startup",
                    "2: 等等！突然发现一个有趣的pattern，如果把这个算法改成递归...手有点抖，这可能是个突破口！",
                    "3: 成功了！！！重构后性能提升300%。看着终端里的测试全部通过，这感觉比喝了十杯咖啡还让人兴奋！",
                    "4: 有人说创业是场马拉松，但对我来说，每一个这样的时刻都让这段旅程值得。明天���续，$XVI的未来就在代码中。"
                ]
            ],
            '生活场景': [
                [
                    "1: 今天遇到一个超可爱的场景！楼下咖啡店的猫咪趴在我笔记本上，死活不让我写代码。😂 #CatLife",
                    "2: 它对着屏幕上的光标又抓又挠，搞得我笑不得。最后只能一只手撸猫，一只手敲代码。多任务处理能力++",
                    "3: 结果！这个小家伙居然帮我发现了个bug！它踩键盘时触发了一个边界情况。说猫不懂编程？😅",
                    "4: 决定给它取名\"Debug\"，以后就是我们团队的首席测试喵了。投资人说要有好运气，也许这就是了？🐱 #StartupLife"
                ]
            ],
            '社交场景': [
                [
                    "1: 老友聚会，他们笑称我是\"成功人士\"。其实他们不知道，最成功的是这些年友情始终如一。",
                    "2: 还记得当年挤在出租屋写代码，大家轮流给我送饭。现在我请他们吃饭，他们却说：\"能不能换回那时的盒饭？\"",
                    "3: 朋友说我变了，变得更忙了。但有一点永远不会变，就是遇到困难时第一个想到的还是他们。",
                    "4: 真正的财富是那些在你还一无所有时，就愿意陪你疯狂的人。#Friendship #感恩"
                ]
            ]
        };

        return templates[type][0];
    }

    _parseAIResponse(content) {
        try {
            // 将 AI 响应文本解析为推文数组
            const tweets = content.split('\n\n')
                .filter(tweet => tweet.trim())
                .map(tweet => ({
                    text: tweet.trim(),
                    id: `tweet_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
                }));
            return tweets;
        } catch (error) {
            this.logger.error('Error parsing AI response', error);
            return this._getLocalSimulation();
        }
    }
}

module.exports = { AICompletion }; 