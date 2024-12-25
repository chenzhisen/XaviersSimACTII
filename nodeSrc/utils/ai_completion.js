const OpenAI = require('openai');
const { Logger } = require('./logger');
const { Config } = require('./config');

class AICompletion {
    constructor(client, model) {
        this.model = model;
        this.client = client;

        // 模拟回复模板
        this.mockResponses = {
            earlyPhase: [
                `TWEET 1: 凌晨3点，第108次修改代码。这个bug太难找了，但我知道答案就在眼前。泡一杯咖啡，继续战斗。#coding #startup

TWEET 2: 等等！突然发现一个有趣的pattern，如果把这个算法改成递归...手有点抖，这可能是个突破口！

TWEET 3: 成功了！！！重构后性能提升300%。看着终端里的测试全部通过，这感觉比喝了十杯咖啡还让人兴奋！

TWEET 4: 有人说创业是场马拉松，但对我来说，每一个这样的时刻都让这段旅程值得。明天继续，$XVI的未来就在代码中。`,

                `TWEET 1: 刚和潜在投资人开完视频会议。他们对$XVI的愿景很感兴趣，但质疑技术实现难度。深呼吸。

TWEET 2: 打开我们的代码库，开始演示。当讲到我们如何解决扩容问题时，他们的表情变了。这感觉真好。

TWEET 3: "从未见过这样的解决方案..."投资人说。是啊，因为这是我在无数个深夜调试出来的。创新就是这样。

TWEET 4: 会议结束，Term sheet已发。但比融资更重要的是，他们真正理解了我们想要构建的未来。继续向前。`
            ],
            growthPhase: [
                `TWEET 1: 团队从5人变成50人。看着新办公室里忙碌的身影，恍然意识到我们真的在创造改变。

TWEET 2: 站在白板前，和团队讨论新特性。有时候最好的想法来自于最基层的工程师，这就是我爱这个团队的原因。

TWEET 3: "Xavier，记得你刚招我时说的话吗？"一个早期员工问。当然记得，我说要改变世界。现在看来，我们正在做到。

TWEET 4: 明天是$XVI 2.0发布。但对我来说，最骄傲的不是产品，而是这个充满激情的团队。我们在创造历史。`
            ]
        };
    }

    async getCompletion(systemPrompt, userPrompt, options = {}) {
        console.log('Generating mock response for prompt:', userPrompt);

        // 根据prompt内容选择合适的模拟回复
        let response;
        if (userPrompt.includes('22') || userPrompt.includes('early')) {
            response = this._getRandomResponse('earlyPhase');
        } else if (userPrompt.includes('32') || userPrompt.includes('growth')) {
            response = this._getRandomResponse('growthPhase');
        } else {
            response = this._getDefaultResponse();
        }

        // 模拟API延迟
        await new Promise(resolve => setTimeout(resolve, 1000));

        return response;
    }

    _getRandomResponse(phase) {
        const responses = this.mockResponses[phase];
        return responses[Math.floor(Math.random() * responses.length)];
    }

    _getDefaultResponse() {
        return `TWEET 1: 回顾这些年的技术变迁，深感科技的力量。记得当初为什么选择这条路：为了创造改变。

TWEET 2: 现在的年轻开发者们问我经验，我说：技术栈可以学，但保持热爱和好奇心更重要。

TWEET 3: 在这个行业待了这么久，最大的收获不是财富，而是看到自己的代码改变了人们的生活。

TWEET 4: 明天又要去给一个创业团队做分享。也许这就是传承吧，帮助他们少走些弯路。#techlife #sharing`;
    }
}

module.exports = { AICompletion }; 