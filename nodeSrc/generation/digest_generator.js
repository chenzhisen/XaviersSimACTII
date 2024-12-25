const { AICompletion } = require('../utils/ai_completion');
const { Logger } = require('../utils/logger');
const fs = require('fs').promises;
const path = require('path');
const chalk = require('chalk');

class DigestGenerator {
    constructor(client, model, digestInterval = 4, options = {}) {
        this.logger = new Logger('digest');
        this.ai = new AICompletion(client, model, options);
        this.digestInterval = digestInterval;
        this.isProduction = options.isProduction || false;

        // 文件路径配置
        this.paths = {
            dataDir: path.resolve(__dirname, '..', 'data'),
            mainFile: path.resolve(__dirname, '..', 'data', 'XaviersSim.json')
        };

        // 本地摘要模板
        this.digestTemplates = {
            early_career: [
                `在这段时间里，Xavier展现出了典型的创业初期特征。他专注于技术开发，不断挑战自我。与此同时，他也在学习平衡工作与生活，建立重要的人际关系。Debug猫的出现为他的创业生活增添了一份意外的惊喜，也象征着好运的开始。

这个阶段的关键发展包括：
1. 技术突破：成功解决了关键性能问题
2. 团队建设：开始组建核心团队
3. 个人成长：学会在压力下保持乐观
4. 人际关系：深化了重要的友情纽带

展望未来，Xavier需要继续保持这种积极的态度，同时更多关注团队建设和产品市场适配性。他的故事正在朝着一个有趣的方向发展。`,

                `这段时期是Xavier创业旅程的重要起点。他展现出了技术专家和创业者的双重特质，在解决技术难题的同时，也在探索创业之路。重要的是，他没有忘记生活中的其他方面，特别是与朋友们的珍贵情谊。

主要进展：
1. 产品开发：取得重要技术突破
2. 创业准备：初步建立团队框架
3. 生活平衡：保持工作与生活的平衡
4. 情感支持：维系重要的友情关系

未来展望：随着项目的推进，Xavier将面临更多挑战，但他已经展现出应对这些挑战的潜力。`
            ]
        };
    }

    async checkAndGenerateDigest(newTweets, currentAge, timestamp, totalTweets) {
        try {
            console.log(chalk.blue('Checking digest generation:', {
                totalTweets,
                interval: this.digestInterval
            }));

            // 获取最近的推文
            const recentTweets = await this._getRecentTweets();
            
            // 确保 recentTweets 是数组
            const validTweets = Array.isArray(recentTweets) ? recentTweets : [];
            
            // 生成摘要
            let digest;
            if (this.ai.options.useLocalSimulation) {
                console.log(chalk.yellow('Using local digest template'));
                digest = this._getLocalDigest(currentAge);
            } else {
                console.log(chalk.blue('Generating AI digest'));
                digest = await this._generateAIDigest(validTweets, currentAge);
            }

            // 保存摘要
            if (digest) {
                const calculatedAge = this._calculateAge(totalTweets);
                await this._saveDigest(digest, calculatedAge, timestamp);
                console.log(chalk.green('Digest generated and saved:', {
                    age: calculatedAge,
                    tweetCount: totalTweets
                }));
            }

            return digest;
        } catch (error) {
            console.log(chalk.red('Error in digest generation:', error));
            throw error;
        }
    }

    async _getRecentTweets() {
        try {
            const data = await fs.readFile(this.paths.mainFile, 'utf8');
            const storyData = JSON.parse(data);
            return storyData.story?.tweets?.slice(-this.digestInterval) || [];
        } catch (error) {
            this.logger.error('Error getting recent tweets', error);
            return [];
        }
    }

    _getLocalDigest(currentAge) {
        // 根据 Introduction.json 生成初始摘要
        const intro = require('../data/Introduction.json');
        const phase = this._getPhase(currentAge);
        const phaseData = intro.story.phases[phase];

        const digest = `这是Xavier故事的开始。作为一位${intro.protagonist.background.education}的毕业生，他怀揣着构建${intro.story.company.vision}的梦想，开启了他的创业之旅。在${intro.story.setting.location}这片创新热土上，他正式成立了${intro.story.company.name}，致力于${intro.story.company.mission}。

主要进展：
1. 技术基础：凭借${intro.protagonist.background.expertise.join('、')}等专业知识，开始构建${intro.story.company.product.name}
2. 创业准备：确立了"${intro.story.company.product.description}"的产品定位
3. 核心能力：专注于${intro.story.company.product.features.join('、')}等关键特性
4. 个人成长：展现出${intro.protagonist.personality.traits.slice(0, 3).join('、')}等特质

未来展望：在${intro.story.setting.context}的大背景下，Xavier将专注于${phaseData.focus.join('、')}等方向，以实现产品的技术突破和市场验证。`;

        return {
            content: digest,
            timestamp: new Date().toISOString(),
            age: Number(currentAge.toFixed(2)),
            tweetCount: this.digestInterval
        };
    }

    async _generateAIDigest(tweets, currentAge) {
        try {
            const prompt = this._buildDigestPrompt(tweets, currentAge);
            const response = await this.ai.getCompletion(
                'You are crafting a story digest summarizing recent events.',
                prompt
            );

            // 检查 AI 响应内容
            let content = response[0]?.text;
            if (!content || content.length < 50) {
                console.log(chalk.yellow('AI response too short or invalid, using local template'));
                return this._getLocalDigest(currentAge);
            }

            // 确保摘要格式正确
            if (!this._validateDigestFormat(content)) {
                content = this._formatDigest(content);
            }

            return {
                content,
                timestamp: new Date().toISOString(),
                age: Number(currentAge.toFixed(2)),
                tweetCount: tweets.length
            };
        } catch (error) {
            console.log(chalk.red('Error generating AI digest:', error));
            console.log(chalk.yellow('Falling back to local digest template'));
            return this._getLocalDigest(currentAge);
        }
    }

    _validateDigestFormat(content) {
        // 检查摘要是否包含必要的部分
        return content.includes('这段时期') && 
               content.includes('主要进展：') && 
               content.includes('未来展望：');
    }

    _formatDigest(content) {
        // 如果内容不符合格式要求，重新格式化
        const lines = content.split('\n').filter(line => line.trim());
        
        let overview = lines[0] || '这段时期Xavier展现出了积极的成长态势。';
        let developments = [];
        let outlook = '';

        // 提取主要进展
        for (const line of lines) {
            if (line.includes('进展') || line.includes('发展') || line.includes('成就')) {
                developments.push(line.replace(/^\d+[\.\、]?\s*/, ''));
            } else if (line.includes('未来') || line.includes('展望') || line.includes('期待')) {
                outlook = line;
            }
        }

        // 确保有足够的进展点
        while (developments.length < 4) {
            developments.push('持续学习和成长');
        }

        // 如果没有找到展望，添加默认展望
        if (!outlook) {
            outlook = '未来展望：Xavier将继续在技术和创业道路上探索，相信会有更多突破和成长。';
        }

        // 组装格式化的摘要
        return `${overview}\n\n主要进展：\n1. ${developments[0]}\n2. ${developments[1]}\n3. ${developments[2]}\n4. ${developments[3]}\n\n${outlook}`;
    }

    _calculateAge(totalTweets) {
        const tweetsPerYear = 48; // 每年48条推文
        const yearsPassed = totalTweets / tweetsPerYear;
        const startAge = 22;
        return Number((startAge + yearsPassed).toFixed(2));
    }

    _getPhase(age) {
        if (age < 32) return 'early_career';
        if (age < 42) return 'growth_phase';
        if (age < 52) return 'peak_phase';
        if (age < 62) return 'mature_phase';
        return 'wisdom_phase';
    }

    async _saveDigest(digest, currentAge, timestamp) {
        try {
            const data = await fs.readFile(this.paths.mainFile, 'utf8');
            const storyData = JSON.parse(data);

            // 添加新摘要到 story.digests
            storyData.story.digests.push({
                ...digest,
                age: Number(currentAge.toFixed(2)),
                timestamp
            });

            // 更新统计信息和年龄
            storyData.stats.digestCount = storyData.story.digests.length;
            storyData.metadata.currentAge = Number(currentAge.toFixed(2));

            // 保存更新
            await fs.writeFile(
                this.paths.mainFile,
                JSON.stringify(storyData, null, 2),
                'utf8'
            );

            this.logger.info('Saved new digest', {
                age: Number(currentAge.toFixed(2)),
                timestamp
            });
        } catch (error) {
            this.logger.error('Error saving digest', error);
            throw error;
        }
    }

    _buildDigestPrompt(tweets, currentAge) {
        try {
            const phase = this._getPhase(currentAge);
            const tweetsText = tweets
                .map(tweet => tweet.text)
                .join('\n\n');

            return `
作为一个故事摘要生成器，请为以下推文���成一个详细的中文摘要。
这些推文描述了Xavier在${phase}阶段（${currentAge}岁）的经历。

推文内容：
${tweetsText}

请按以下格式生成摘要：
1. 开头概述这段时期的整体特点和主要发展（2-3句话）
2. 列出4个具体的主要进展，包括：技术/产品、团队/人际、个人成长等方面
3. 最后加上对未来的展望（1-2句话）

要求：
- 保持积极向上的基调
- 突出重要的转折点和成就
- 体现人物的成长轨迹
- 注意情���和故事性
- 确保内容前后连贯

请严格按照以下模板输出：
[开头概述，2-3句话描述这段时期的特点]

主要进展：
1. [具体进展1]
2. [具体进展2]
3. [具体进展3]
4. [具体进展4]

未来展望：[1-2句话的展望]
`;
        } catch (error) {
            console.log(chalk.red('Error building digest prompt:', error));
            throw error;
        }
    }
}

module.exports = { DigestGenerator }; 