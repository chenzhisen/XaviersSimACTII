const { AICompletion } = require('../utils/ai_completion');
const { Logger } = require('../utils/logger');
const fs = require('fs').promises;
const path = require('path');

class TechEvolutionGenerator {
    constructor(client, model, isProduction = false) {
        this.logger = new Logger('tech');
        this.ai = new AICompletion(client, model);
        this.isProduction = isProduction;

        this.paths = {
            dataDir: path.resolve(__dirname, '..', 'data'),
            mainFile: path.resolve(__dirname, '..', 'data', 'XaviersSim.json')
        };

        // 技术发展阶段
        this.techPhases = {
            early: {
                focus: ['基础架构', '核心算法', '产品原型'],
                challenges: ['技术选型', '性能优化', '安全性']
            },
            growth: {
                focus: ['系统扩展', '新特性', '技术升级'],
                challenges: ['架构重构', '团队协作', '技术债务']
            },
            mature: {
                focus: ['创新突破', '技术领导', '行业标准'],
                challenges: ['技术演进', '平台化', '生态建设']
            }
        };
    }

    async generateTechUpdate(currentAge, tweetCount) {
        try {
            const context = await this._prepareTechContext(currentAge);
            const techUpdate = await this._generateUpdate(context);
            await this._saveTechUpdate(techUpdate, currentAge);
            return techUpdate;
        } catch (error) {
            this.logger.error('Error generating tech update', error);
            throw error;
        }
    }

    async _prepareTechContext(currentAge) {
        try {
            const data = await fs.readFile(this.paths.mainFile, 'utf8');
            const storyData = JSON.parse(data);

            // 确定当前技术阶段
            const phase = this._getTechPhase(currentAge);
            
            // 获取最近的技术更新
            const recentUpdates = storyData.techUpdates?.slice(-3) || [];
            
            return {
                currentAge,
                phase,
                focus: this.techPhases[phase].focus,
                challenges: this.techPhases[phase].challenges,
                recentUpdates,
                totalTweets: storyData.tweets?.length || 0
            };
        } catch (error) {
            this.logger.error('Error preparing tech context', error);
            throw error;
        }
    }

    async _generateUpdate(context) {
        const prompt = this._buildTechPrompt(context);
        
        const response = await this.ai.getCompletion(
            'You are describing technological evolution of a startup.',
            prompt
        );

        return {
            content: response,
            timestamp: new Date().toISOString(),
            age: context.currentAge,
            phase: context.phase,
            focus: context.focus,
            challenges: context.challenges
        };
    }

    _buildTechPrompt(context) {
        return `Technology Evolution Update:
Age: ${context.currentAge}
Phase: ${context.phase}
Current Focus: ${context.focus.join(', ')}
Current Challenges: ${context.challenges.join(', ')}

Recent Tech Updates:
${context.recentUpdates.map(u => u.content).join('\n\n')}

Create a technology evolution update that:
1. Describes current technical achievements
2. Outlines ongoing challenges and solutions
3. Shows innovation and progress
4. Reflects the startup's growth stage
5. Sets up future technical directions

Guidelines:
- Focus on technical depth and innovation
- Show problem-solving approaches
- Include both successes and challenges
- Maintain realistic progression
- Consider market and user needs

Format the response as a detailed technical narrative that captures this phase of development.`;
    }

    async _saveTechUpdate(update, currentAge) {
        try {
            const data = await fs.readFile(this.paths.mainFile, 'utf8');
            const storyData = JSON.parse(data);

            // 添加新的技术更新
            storyData.techUpdates = storyData.techUpdates || [];
            storyData.techUpdates.push({
                ...update,
                age: currentAge,
                timestamp: new Date().toISOString()
            });

            // 更新最新技术状态
            storyData.currentTechState = {
                phase: update.phase,
                focus: update.focus,
                challenges: update.challenges,
                lastUpdate: new Date().toISOString()
            };

            // 保存更新
            await fs.writeFile(
                this.paths.mainFile,
                JSON.stringify(storyData, null, 2),
                'utf8'
            );

            this.logger.info('Saved tech update', {
                age: currentAge,
                phase: update.phase
            });
        } catch (error) {
            this.logger.error('Error saving tech update', error);
            throw error;
        }
    }

    _getTechPhase(age) {
        if (age < 32) return 'early';
        if (age < 52) return 'growth';
        return 'mature';
    }
}

module.exports = { TechEvolutionGenerator };