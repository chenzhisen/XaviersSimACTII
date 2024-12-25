const { AICompletion } = require('../utils/ai_completion');
const { GithubOperations } = require('../storage/github_operations');
const { Logger } = require('../utils/logger');

class TweetGenerator {
    constructor(client, model, isProduction = false) {
        this.logger = new Logger('tweet');
        this.ai = new AICompletion(client, model);
        this.githubOps = new GithubOperations(isProduction);
        
        // 故事主线配置
        this.storyConfig = {
            protagonist: {
                name: 'Xavier',
                identity: '程序员/创业者/$XVI创始人',
                startAge: 22,
                endAge: 72
            },
            
            // 人生阶段
            lifePhases: {
                earlyPhase: {
                    age: [22, 32],
                    focus: '技术创新与创业',
                    events: ['创建$XVI', '团队组建', '产品研发']
                },
                growthPhase: {
                    age: [32, 42],
                    focus: '事业扩张期',
                    events: ['生态建设', '市场扩张', '技术突破']
                },
                peakPhase: {
                    age: [42, 52],
                    focus: '行业领袖期',
                    events: ['行业影响', '战略布局', '价值实现']
                },
                maturePhase: {
                    age: [52, 62],
                    focus: '回馈社会期',
                    events: ['经验分享', '投资孵化', '行业引领']
                },
                wisdomPhase: {
                    age: [62, 72],
                    focus: '智慧传承期',
                    events: ['人生总结', '价值传承', '新生代培养']
                }
            },

            // 年度节奏
            yearlyPace: {
                tweetsPerYear: 48,
                scenesPerYear: 12,
                tweetsPerScene: 4
            }
        };

        // 故事元素
        this.storyElements = {
            // 核心主题
            themes: {
                tech: ['技术创新', '编程艺术', '架构设计'],
                crypto: ['代币经济', '市场洞察', '价值创造'],
                life: ['个人成长', '生活感悟', '人生哲学']
            },
            
            // 情节类型
            plotTypes: {
                milestone: '重要里程碑',
                challenge: '困境与突破',
                reflection: '思考与感悟',
                progress: '日常进展'
            }
        };
    }

    async generateTweetScene(digest, currentAge, tweetCount) {
        try {
            const context = await this._prepareContext(digest, tweetCount);
            const plotContext = this._getPlotContext(context);
            const prompt = this._buildStoryPrompt(context, plotContext);
            console.log(prompt);
            const response = await this.ai.getCompletion(
                'You are crafting a compelling life story through tweets.',
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
                    year_progress: Math.floor((tweetCount % 48) / 48 * 100),
                    life_phase: this._getCurrentPhase(currentAge).focus,
                    plot_type: plotContext.plotType,
                    themes: plotContext.activeThemes
                }
            }));
        } catch (error) {
            this.logger.error('Error generating story scene', error);
            throw error;
        }
    }

    _buildStoryPrompt(context, plotContext) {
        return `Story Context:
Age: ${context.current_age}
Life Phase: ${plotContext.currentPhase.focus}
Current Focus: ${plotContext.currentFocus}
Active Themes: ${plotContext.activeThemes.join(', ')}

Recent Story:
${context.recent_tweets.map(t => t.text).join('\n')}

Create a scene of 4 connected tweets that:
1. Advances the life story naturally
2. Shows character growth and insights
3. Reflects current life phase themes
4. Creates memorable moments
5. Maintains story continuity

Scene Structure:
TWEET 1: [Set the scene and mood]
TWEET 2: [Develop the situation]
TWEET 3: [Key moment or insight]
TWEET 4: [Resolution and future hint]

Writing Guidelines:
- Focus on personal growth and insights
- Show both successes and challenges
- Include technical and financial elements
- Create authentic character voice
- Build towards larger story arcs`;
    }

    _getCurrentPhase(age) {
        return Object.values(this.storyConfig.lifePhases).find(
            phase => age >= phase.age[0] && age < phase.age[1]
        );
    }

    _getPlotContext(context) {
        const currentPhase = this._getCurrentPhase(context.current_age);
        const yearProgress = (context.tweet_count % 48) / 48;

        // 选择当前主题
        const activeThemes = this._selectThemes(currentPhase, yearProgress);
        
        return {
            currentPhase,
            currentFocus: this._selectFocus(currentPhase, yearProgress),
            plotType: this._selectPlotType(yearProgress),
            activeThemes
        };
    }

    // ... 其他必要方法 ...
}

module.exports = { TweetGenerator }; 