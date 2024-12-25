const { AICompletion } = require('../utils/ai_completion');
const { GithubOperations } = require('../storage/github_operations');
const { Logger } = require('../utils/logger');

class TweetGenerator {
    constructor(client, model, isProduction = false) {
        this.logger = new Logger('tweet');
        this.ai = new AICompletion(client, model);
        this.githubOps = new GithubOperations(isProduction);
        
        // 人生阶段配置
        this.lifePhases = {
            // 奋斗期 (22-32岁): 创业与加密货币早期
            earlyCareer: {
                ageRange: [22, 32],
                themes: ['编程创业', '加密货币', '技术创新', '投资冒险'],
                events: ['创建$XVI代币', '区块链创业', '技术突破', '市场波动'],
                tone: '充满激情与冒险精神',
                techFocus: ['区块链', 'Web3', '智能合约', 'DeFi']
            },
            
            // 发展期 (32-42岁): 技术与投资成熟
            midCareer: {
                ageRange: [32, 42],
                themes: ['技术领导', '投资布局', '市场洞察', '团队建设'],
                events: ['XVI生态扩张', '技术架构升级', '投资组合', '社区建设'],
                tone: '稳重而战略性',
                techFocus: ['架构设计', '技术创新', '加密经济', '社区治理']
            },
            
            // 成熟期 (42-52岁): 技术与财富的巅峰
            peakLife: {
                ageRange: [42, 52],
                themes: ['技术愿景', '财富自由', '行业影响', '创新引领'],
                events: ['技术革新', '财富增长', '行业变革', '投资回报'],
                tone: '睿智而前瞻',
                techFocus: ['未来技术', '创新方向', '市场趋势', '投资策略']
            },
            
            // 收获期 (52-62岁): 经验传承
            harvestLife: {
                ageRange: [52, 62],
                themes: ['技术传承', '投资智慧', '生活平衡', '回馈社会'],
                events: ['技术导师', '投资顾问', '创业孵化', '公益项目'],
                tone: '从容而睿智',
                techFocus: ['技术教育', '投资指导', '创业辅导', '社会责任']
            },
            
            // 智慧期 (62-72岁): 技术与投资的沉淀
            wisdomLife: {
                ageRange: [62, 72],
                themes: ['技术展望', '投资哲学', '生活智慧', '价值传承'],
                events: ['技术回顾', '投资总结', '经验分享', '价值实现'],
                tone: '智慧而豁达',
                techFocus: ['技术演进', '投资思想', '未来展望', '价值观']
            }
        };

        // 年度配置
        this.yearConfig = {
            tweetsPerYear: 48,
            scenesPerYear: 12,
            tweetsPerScene: 4
        };

        // 加密货币相关配置
        this.cryptoContext = {
            mainCoin: '$XVI',
            marketMoods: ['牛市', '熊市', '盘整', '突破', '回调'],
            tradingEvents: ['暴涨', '暴跌', '横盘', '突破历史新高', '技术升级'],
            techStack: ['Python', 'Solidity', 'React', 'Node.js', 'Rust']
        };
    }

    _getCurrentPhase(age) {
        return Object.values(this.lifePhases).find(phase => 
            age >= phase.ageRange[0] && age < phase.ageRange[1]
        );
    }

    _buildScenePrompt(context) {
        const currentPhase = this._getCurrentPhase(context.current_age);
        const yearProgress = (context.tweet_count % 48) / 48;
        const marketMood = this._getMarketContext(context);
        
        return `Character Context:
Age: ${context.current_age}
Identity: 程序员/加密货币创始人/技术创新者
Current Phase: ${currentPhase.ageRange[0]}-${currentPhase.ageRange[1]}
Tech Focus: ${currentPhase.techFocus.join(', ')}
Market Context: ${marketMood}

Phase Themes: ${currentPhase.themes.join(', ')}
Story Tone: ${currentPhase.tone}
Year Progress: ${(yearProgress * 100).toFixed(1)}%

Recent Story:
${context.recent_tweets.map(t => t.text).join('\n')}

Create an engaging scene of 4 connected tweets that:
1. Blends tech insights with crypto market views
2. Shows both coding passion and investment wisdom
3. Creates relatable tech/investment moments
4. Maintains the $XVI token storyline
5. Includes both technical depth and humor

Format:
TWEET 1: [Tech/Market Scene Setup]
TWEET 2: [Development/Challenge]
TWEET 3: [Technical/Investment Insight]
TWEET 4: [Wisdom/Future Vision]

Guidelines:
- Balance tech talk with investment insights
- Include coding/crypto humor
- Reference real tech trends
- Show market understanding
- Add programmer life moments
- Create meme-worthy content
- Use tech/crypto hashtags naturally`;
    }

    _getMarketContext(context) {
        // 基于年份创建周期性的市场情绪
        const yearInPhase = Math.floor(context.tweet_count / 48) % 4;
        const marketCycle = [
            '牛市启动，$XVI突破新高',
            '市场回调，但技术开发稳步推进',
            '熊市积累，专注产品创新',
            '市场企稳，新特性发布在即'
        ];
        return marketCycle[yearInPhase];
    }

    async generateTweetScene(digest, currentAge, tweetCount) {
        try {
            const context = await this._prepareContext(digest, tweetCount);
            const prompt = this._buildScenePrompt(context);
            
            const response = await this.ai.getCompletion(
                'You are crafting a 50-year life journey through engaging tweets.',
                prompt
            );

            const tweets = this._parseTweets(response);
            
            return tweets.map((text, index) => ({
                id: `tweet_${Date.now()}_${index}`,
                text: text.slice(0, 280),
                age: currentAge,
                timestamp: new Date().toISOString(),
                metadata: {
                    tweet_number: tweetCount + index + 1,
                    life_phase: this._getCurrentPhase(currentAge).ageRange[0],
                    year_in_phase: Math.floor((currentAge - this._getCurrentPhase(currentAge).ageRange[0])),
                    year_progress: (tweetCount % 48) / 48 * 100
                }
            }));
        } catch (error) {
            this.logger.error('Error generating tweet scene', error);
            throw error;
        }
    }

    async _prepareContext(digest, tweetCount) {
        const [recentTweets, _] = await this.getOngoingTweets();
        const lastTweets = recentTweets.slice(-5);

        return {
            current_age: 22 + (tweetCount / 48),
            tweet_count: tweetCount,
            latest_digest: digest,
            recent_tweets: lastTweets,
            year_progress: (tweetCount % 48) / 48 * 100
        };
    }

    // ... 其他必要方法 ...
}

module.exports = { TweetGenerator }; 