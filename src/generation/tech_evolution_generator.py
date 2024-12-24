import argparse
from anthropic import Anthropic
from ..utils.config import Config, AIProvider
from ..storage.github_operations import GithubOperations
import json
from datetime import datetime
import os
import time
import requests
import math
from ..utils.ai_completion import AICompletion
import traceback
from ..utils.path_utils import PathUtils

class TechEvolutionGenerator:
    """技术进化生成器
    
    负责生成和管理技术发展路线图，包括：
    - 新兴技术的预测
    - 技术成熟度追踪
    - 技术依赖关系分析
    - 社会影响评估
    """
    
    def __init__(self, client, model, is_production=False):
        """初始化技术进化生成器
        
        参数:
            client: AI 客户端实例
            model: 使用的模型名称
            is_production: 是否为生产环境
        """
        self.client = client
        self.model = model
        self.github_ops = GithubOperations(is_production=is_production)
        self.ai = AICompletion(client, model)
        self.base_year = 2025  # 基准年份
        
        # 初始化技术进化数据结构
        self.tech_evolution = {
            'tech_trees': {},  # 技术树
            'last_updated': datetime.now().isoformat()  # 最后更新时间
        }
        
        # 使用路径工具处理日志路径
        env_dir = "prod" if is_production else "dev"
        self.log_dir = PathUtils.normalize_path("logs", env_dir, "tech")
        PathUtils.ensure_dir(self.log_dir)
        
        self.log_file = PathUtils.normalize_path(
            self.log_dir,
            f"tech_evolution_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

    def log_step(self, step_name, **kwargs):
        """记录生成步骤的信息
        
        参数:
            step_name: 步骤名称
            **kwargs: 需要记录的其他信息
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"\n=== {step_name} === {timestamp}\n"
            
            for key, value in kwargs.items():
                log_entry += f"{key}:\n{value}\n\n"
            
            print(f"[tech_evolution_generator.py:60] 记录步骤: {step_name}")
            
            # 确保日志文件存在
            if not hasattr(self, 'log_file'):
                self.log_file = PathUtils.normalize_path(
                    self.log_dir,
                    f"tech_evolution_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                )
                print(f"- 创建新日志文件: {self.log_file}")
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + "="*50 + "\n")
            
        except Exception as e:
            print(f"[tech_evolution_generator.py:74] 写入日志文件出错:")
            print(f"- 错误类型: {type(e).__name__}")
            print(f"- 错误信息: {str(e)}")
            print(f"- 日志目录: {self.log_dir}")
            if hasattr(self, 'log_file'):
                print(f"- 日志文件: {self.log_file}")

    def _process_tech_relationships(self, tech_trees):
        """Build a graph of technology relationships and dependencies."""
        tech_graph = {
            "dependencies": {},  # tech -> required techs
            "enables": {},      # tech -> enabled techs
            "related": {},      # tech -> related techs
            "maturity_path": {} # tech -> maturity progression
        }
        
        for year, tree in tech_trees.items():
            # Process emerging technologies
            for tech in tree.get("emerging_technologies", []):
                tech_name = tech["name"]
                # Track dependencies
                if "dependencies" in tech:
                    tech_graph["dependencies"][tech_name] = tech["dependencies"]
                    # Update what techs this enables
                    for dep in tech["dependencies"]:
                        if dep not in tech_graph["enables"]:
                            tech_graph["enables"][dep] = []
                        tech_graph["enables"][dep].append(tech_name)
                
                # Track related technologies
                if "impact_areas" in tech:
                    tech_graph["related"][tech_name] = []
                    for area in tech["impact_areas"]:
                        # Find other techs in same area
                        for other_tech in self._find_techs_by_impact_area(tech_trees, area):
                            if other_tech != tech_name:
                                tech_graph["related"][tech_name].append(other_tech)

                # Track maturity path
                tech_graph["maturity_path"][tech_name] = {
                    "emergence_year": int(tech["estimated_year"]),
                    "expected_maturity": int(tech["expected_maturity_year"]),
                    "current_stage": "emerging",
                    "probability": float(tech["probability"]),
                    "innovation_type": tech["innovation_type"]
                }

        return tech_graph

    def _get_previous_technologies(self, epoch_year):
        """Get technologies from previous epochs with enhanced progression tracking."""
        previous_tech = {
            "emerging": [],
            "maturing": [],    # New category for technologies approaching maturity
            "mainstream": [],
            "current_mainstream": [],
            "tech_graph": None # Will store technology relationships
        }
        
        # Get tech trees from saved data
        all_tech_trees = self.tech_evolution.get('tech_trees', {})
        
        # Build technology relationship graph
        tech_graph = self._process_tech_relationships(all_tech_trees)
        previous_tech["tech_graph"] = tech_graph
        
        # Process technologies from previous epochs
        for year in range(self.base_year, epoch_year, 5):
            year_str = str(year)
            if year_str not in all_tech_trees:
                continue
                
            prev_data = all_tech_trees[year_str]
            self._process_tech_progression(previous_tech, prev_data, epoch_year, tech_graph)
        
        self._print_tech_summary(epoch_year, previous_tech)
        return previous_tech

    def _process_tech_progression(self, previous_tech, prev_data, epoch_year, tech_graph):
        """Process technology progression with enhanced maturity tracking."""
        for tech in prev_data.get("emerging_technologies", []):
            tech_name = tech["name"]
            estimated_year = int(tech["estimated_year"])
            maturity_year = int(tech["expected_maturity_year"])
            
            # Calculate progression stage
            years_to_maturity = maturity_year - epoch_year
            total_development_time = maturity_year - estimated_year
            
            if epoch_year < estimated_year:
                # Future technology
                continue
            elif epoch_year >= maturity_year:
                # Has matured
                self._add_to_mainstream(previous_tech, tech, tech_graph)
            elif years_to_maturity <= total_development_time * 0.3:
                # Approaching maturity (last 30% of development time)
                self._add_to_maturing(previous_tech, tech, tech_graph)
            else:
                # Still emerging
                self._add_to_emerging(previous_tech, tech, tech_graph)

    def _add_to_emerging(self, previous_tech, tech, tech_graph):
        """Add technology to emerging list with relationship context."""
        tech_entry = {
            "name": tech["name"],
            "estimated_year": int(tech["estimated_year"]),
            "probability": float(tech["probability"]),
            "dependencies": tech_graph["dependencies"].get(tech["name"], []),
            "enables": tech_graph["enables"].get(tech["name"], []),
            "related_tech": tech_graph["related"].get(tech["name"], [])
        }
        previous_tech["emerging"].append(tech_entry)

    def _add_to_maturing(self, previous_tech, tech, tech_graph):
        """Add technology to maturing list with progression metrics."""
        maturity_path = tech_graph["maturity_path"].get(tech["name"], {})
        tech_entry = {
            "name": tech["name"],
            "maturity_progress": self._calculate_maturity_progress(tech, maturity_path),
            "remaining_dependencies": self._get_remaining_dependencies(tech["name"], tech_graph, previous_tech),
            "enabled_technologies": tech_graph["enables"].get(tech["name"], [])
        }
        previous_tech["maturing"].append(tech_entry)

    def _add_to_mainstream(self, previous_tech, tech, tech_graph):
        """Add technology to mainstream list with impact tracking."""
        tech_entry = {
            "name": tech["name"],
            "maturity_year": int(tech["expected_maturity_year"]),
            "enabled_technologies": tech_graph["enables"].get(tech["name"], []),
            "impact_level": self._calculate_impact_level(tech, tech_graph)
        }
        previous_tech["mainstream"].append(tech_entry)
        previous_tech["current_mainstream"].append(tech_entry)

    def _print_tech_summary(self, epoch_year, previous_tech):
        """Print summary of technologies"""
        print(f"\nPrevious technologies for epoch {epoch_year}:")
        print(f"- Emerging: {len(previous_tech['emerging'])}")
        print(f"- Mainstream: {len(previous_tech['mainstream'])}")
        print(f"- Currently Mainstream: {len(previous_tech['current_mainstream'])}")

    def _generate_epoch_tech_tree(self, current_year):
        """Generate tech tree for the given epoch year."""
        try:
            print(f"\nGenerating tech tree for epoch {current_year}...")
            
            self.log_step(
                "Starting Tech Tree Generation",
                current_year=str(current_year)
            )
            
            # Generate new tech tree
            previous_tech = self._get_previous_technologies(current_year)
            emerging_tech = json.dumps(previous_tech['emerging'], indent=2)
            mainstream_tech = json.dumps(previous_tech['mainstream'], indent=2)
            
            years_from_base = current_year - self.base_year
            acceleration_factor = self.calculate_acceleration(years_from_base)
            
            # Log all context before making the API call
            self.log_step(
                "CONTEXT FOR EPOCH",
                current_year=current_year,
                previous_emerging=f"Previous Emerging Tech:\n{emerging_tech}",
                previous_mainstream=f"Previous Mainstream Tech:\n{mainstream_tech}",
                years_from_base=years_from_base,
                acceleration_factor=acceleration_factor
            )
            
            system_prompt = """You are a technology evolution expert specializing in future forecasting and emerging technologies. Your expertise includes:

                1. CORE COMPETENCIES:
                - Exponential technology growth patterns
                - Cross-domain technology integration
                - Societal impact analysis
                - Market adoption trajectories
                - Technological dependencies and prerequisites

                2. ANALYTICAL FRAMEWORK:
                - Use empirical data and historical patterns
                - Consider technological dependencies
                - Account for societal implications, especially regarding AI's role in social media and public interaction
                - Evaluate market readiness and adoption barriers
                - Assess regulatory and infrastructure requirements

                3. OUTPUT PRINCIPLES:
                - Maintain logical progression of technology evolution
                - Ensure realistic development timelines
                - Consider both incremental and breakthrough innovations
                - Balance optimism with practical constraints
                - Provide detailed, well-reasoned analyses

                For Emerging Technologies:
                - estimated_year: When the technology first becomes viable/available for early adoption
                - probability: Likelihood of successful development by estimated_year
                - innovation_type: breakthrough (radical change) or incremental (gradual improvement)
                
                For Mainstream Technologies:
                - maturity_year: When the technology becomes widely adopted and standardized
                - from_emerging: Whether it evolved from a previous emerging technology
                - impact_level: Scale of 1-10 for societal impact
                
                Remember:
                - Emerging technologies start as experimental/early-stage
                - Some emerging tech will later become mainstream
                - estimated_year marks first appearance/viability
                - maturity_year marks widespread adoption

                Your task is to generate realistic, well-reasoned technological forecasts that build upon existing developments while maintaining narrative consistency.                
                """

            self.log_step(
                "SYSTEM PROMPT",
                prompt=system_prompt
            )
            
            user_prompt = f"""Generate technological advancements from {current_year} to {current_year + 5}. 

            CONTEXT:
            - Current epoch: {current_year}
            - Years since 2025: {years_from_base}
            - Tech growth rate: {acceleration_factor:0.2f}x faster than in 2025
            - Prior technologies include:
                * Emerging: {emerging_tech}
                * Mainstream: {mainstream_tech}

            GUIDELINES FOR TECHNOLOGY DEVELOPMENT:

            1.	FOCUS AREAS:
            •	AI Agents & Autonomy:
                - Agent Evolution: Progress from task-specific to general-purpose autonomous agents
                - Multi-Agent Systems: Development of agent collaboration and coordination
                - Agent Consciousness: Advancement in self-awareness and emotional intelligence
                - Agent-Human Integration: Seamless cooperation between humans and AI agents
                - Agent Governance: Frameworks for managing autonomous agent networks
                - Agent Specialization: Domain-specific expert agents and their evolution
                - Agent Learning: Systems for continuous agent improvement and adaptation
                - Agent Ethics: Moral frameworks and decision-making protocols
            •	Other Areas:
                - Vision for future technological advancements in various sectors
                - Consider divergent or parallel paths

            2.	INDUSTRY LANDSCAPE (For Inspiration):
            Notable developments and companies shaping the future:
            •	Sustainable Tech & Transport: Tesla (EVs, autonomous systems)
            •	Space Exploration: SpaceX (interplanetary travel, Mars colonization)
            •	Global Connectivity: Starlink (satellite networks)
            •	Neural Interfaces: Neuralink (brain-machine interfaces)
            •	Infrastructure: Boring Company (urban transport)
            •	Advanced AI: xAI, Cursor AI (automated development, 2024)
            •	Digital Town Square: X.com (global communication platform)

            These represent current industry directions but should not limit the scope of technological evolution. Feel free to envision divergent or parallel paths.

            3.	AGENT DEVELOPMENT PRINCIPLES:
            •	Progressive Autonomy: Agents should evolve from supervised to increasingly autonomous operation
            •	Collaborative Intelligence: Focus on multi-agent systems and agent-human teamwork
            •	Ethical Framework: Incorporate moral decision-making and safety protocols
            •	Specialization Balance: Mix of specialized expert agents and general-purpose agents
            •	Learning Capability: Continuous improvement through experience and interaction
            •	Interoperability: Standards for agent communication and collaboration
            •	Safety Mechanisms: Built-in constraints and oversight systems
            
            4.	DEVELOPMENT PRINCIPLES:
            •	Exponential Growth: Technologies should evolve at an accelerated rate, compounding prior advancements to reach breakthroughs sooner.
            •	Stage-Based Evolution: Major technologies should first appear in early forms or experimental stages before reaching full mainstream adoption.
            •	Practical Applications: Emphasize advancements with tangible, real-world applications; describe societal or industry-specific impacts.
            •	Societal and Ethical Considerations: Note any societal impacts or regulatory challenges, especially around privacy, security, and human augmentation.
            •	Blockchain Integration: Where applicable, reference blockchain innovations in security, transparency, or decentralized governance.
            
            IMPORTANT: While considering existing industry developments, focus on organic technological evolution that may align with, diverge from, or transcend current approaches.

            IMPORTANT: Ensure strong representation of AI agent technologies in both emerging and mainstream categories, showing clear progression from simple to complex agent systems.

            IMPORTANT: Consider how these technologies might be adopted and integrated into daily life, business operations, and social structures as they mature.

            IMPORTANT: Return a raw JSON object without any markdown formatting or code block markers.
            Do not wrap the response in ```json``` tags.

            RETURN FORMAT (JSON):
            {{
                "emerging_technologies": [
                    {{
                        "name": "technology name",
                        "probability": "0.0 to 1.0",
                        "estimated_year": "YYYY",
                        "expected_maturity_year": "YYYY",
                        "innovation_type": "incremental|breakthrough",
                        "dependencies": ["tech1", "tech2"],
                        "impact_areas": ["area1", "area2"],
                        "description": "brief description",
                        "societal_implications": "impact analysis",
                        "adoption_factors": "adoption analysis"
                    }}
                ],
                "mainstream_technologies": [
                    {{
                        "name": "technology name",
                        "from_emerging": true,
                        "original_emergence_year": "YYYY",
                        "maturity_year": "YYYY",
                        "impact_level": "1 to 10",
                        "description": "brief description",
                        "adoption_status": "adoption analysis"
                    }}
                ],
                "epoch_themes": [
                    {{
                        "theme": "theme name",
                        "description": "brief description",
                        "related_technologies": ["tech1", "tech2"],
                        "societal_impact": "impact analysis",
                        "global_trends": "trend analysis"
                    }}
                ]
            }}
            """
            
            self.log_step(
                "USER PROMPT",
                prompt=user_prompt
            )
            
            # Make API call and get response
            print("Making API call for tech tree generation...")
            response = self._get_completion(system_prompt, user_prompt)
            
            self.log_step(
                "AI RESPONSE",
                content=response
            )
            
            if not response:
                print("Failed to get valid response from AI")
                return None
            
            try:
                tech_data = json.loads(response)
                if not tech_data:
                    print("Empty tech data received")
                    return None
                
                # Append new data to existing tech trees
                self.tech_evolution['tech_trees'][str(current_year)] = tech_data
                self.tech_evolution['last_updated'] = datetime.now().isoformat()
                
                self.log_step(
                    "Tech Tree Generated",
                    tech_data=json.dumps(tech_data, indent=2)
                )
                
                print(f"Successfully generated tech tree for {current_year}")
                return self.tech_evolution
                
            except json.JSONDecodeError as e:
                self.log_step(
                    "JSON Parse Error",
                    error=str(e),
                    response=response
                )
                return None
            
        except Exception as e:
            self.log_step(
                "Tech Tree Generation Error",
                error=str(e),
                traceback=traceback.format_exc()
            )
            print(f"Error generating tech tree: {str(e)}")
            return None

    def _save_evolution_data(self):
        """Save the current evolution data"""
        try:
            file_path = "tech_evolution.json"
            
            print(f"Saving tech evolution data...")
            self.github_ops.update_file(
                file_path,
                self.tech_evolution,
                "Update tech evolution data"
            )
            return True
            
        except Exception as e:
            print(f"Failed to save evolution data: {str(e)}")
            # Continue with local data
            return False

    def check_and_generate_tech_evolution(self, current_date):
        """检查并生成技术进化数据"""
        try:
            print("\n=== 开始生成技术进化数据 [tech_evolution_generator.py:289] ===")
            print(f"当前日期: {current_date}")
            
            # 获取现有数据
            tech_evolution, sha = self.github_ops.get_file_content('tech_evolution.json')
            if not tech_evolution:
                print("- [tech_evolution_generator.py:295] 未找到现有技术进化数据，将创建新数据")
                tech_evolution = {'tech_trees': {}}
            
            # 检查是否需要生成新的技术树
            current_year = current_date.year
            if str(current_year) not in tech_evolution['tech_trees']:
                print(f"- [tech_evolution_generator.py:301] 需要为 {current_year} 年生成新的技术树")
                new_tree = self._generate_epoch_tech_tree(current_year)
                if new_tree:
                    tech_evolution['tech_trees'][str(current_year)] = new_tree
                    print("- [tech_evolution_generator.py:305] 成功生成新的技术树")
                    # 保存更新后的数据
                    self._save_evolution_data()
                else:
                    print("- [tech_evolution_generator.py:307] 错误: 生成技术树失败")
                    return None
                
            return tech_evolution
            
        except Exception as e:
            print("\n=== 技术进化生成错误 ===")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            print("\n详细错误追踪:")
            traceback.print_exc()
            return None

    def _get_completion(self, system_prompt, user_prompt):
        """Get completion from AI model."""
        try:
            response = self.ai.get_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            if not response:
                print("- Warning: Empty response received")
                return None
            
            # Clean up response - remove markdown code block markers and any extra whitespace
            cleaned_response = response
            if '```json' in response:
                cleaned_response = response.split('```json')[-1].split('```')[0].strip()
            
            # Validate JSON structure
            try:
                json.loads(cleaned_response)
                print("- Response is valid JSON")
                return cleaned_response
            except json.JSONDecodeError as e:
                print(f"- Invalid JSON response: {e}")
                print("- Full response:", response)
                return None
            
        except Exception as e:
            print(f"Error getting completion: {e}")
            return None

    def calculate_acceleration(self, years_from_base):
        """Calculate technology acceleration factor based on years from base."""
        # Using exponential growth with 5% increase per year
        growth_rate = 0.05
        acceleration = (1 + growth_rate) ** years_from_base
        return acceleration

    def _calculate_maturity_progress(self, tech, maturity_path):
        """Calculate detailed maturity metrics for a technology."""
        try:
            current_year = datetime.now().year
            emergence_year = maturity_path.get("emergence_year", current_year)
            expected_maturity = maturity_path.get("expected_maturity", current_year + 5)
            total_time = expected_maturity - emergence_year
            elapsed_time = current_year - emergence_year
            
            progress = {
                "percentage": min(100, max(0, (elapsed_time / total_time) * 100)),
                "years_to_maturity": max(0, expected_maturity - current_year),
                "development_stage": self._determine_development_stage(elapsed_time / total_time),
                "risk_factors": self._assess_risk_factors(tech, maturity_path),
                "adoption_metrics": self._calculate_adoption_metrics(tech, maturity_path)
            }
            return progress
        except Exception as e:
            print(f"Error calculating maturity progress: {e}")
            return {"percentage": 0, "years_to_maturity": 5, "development_stage": "unknown"}

    def _determine_development_stage(self, progress_ratio):
        """Determine the current development stage based on progress."""
        if progress_ratio < 0.2:
            return "early_development"
        elif progress_ratio < 0.4:
            return "prototype"
        elif progress_ratio < 0.6:
            return "beta"
        elif progress_ratio < 0.8:
            return "refinement"
        else:
            return "pre_mainstream"

    def _assess_risk_factors(self, tech, maturity_path):
        """Assess risk factors affecting technology maturation."""
        risks = {
            "technical_complexity": self._calculate_technical_risk(tech),
            "dependency_risks": self._assess_dependency_risks(tech),
            "market_readiness": self._assess_market_readiness(tech),
            "regulatory_challenges": self._identify_regulatory_risks(tech)
        }
        return risks

    def _calculate_adoption_metrics(self, tech, maturity_path):
        """Calculate adoption metrics for the technology."""
        return {
            "early_adopters": self._estimate_early_adopters(tech),
            "market_penetration": self._estimate_market_penetration(tech, maturity_path),
            "industry_acceptance": self._assess_industry_acceptance(tech),
            "user_readiness": self._assess_user_readiness(tech)
        }

    def _get_remaining_dependencies(self, tech_name, tech_graph, previous_tech):
        """Get list of dependencies not yet mature."""
        dependencies = tech_graph["dependencies"].get(tech_name, [])
        mature_techs = {tech["name"] for tech in previous_tech["mainstream"]}
        return [dep for dep in dependencies if dep not in mature_techs]

    def _calculate_impact_level(self, tech, tech_graph):
        """Calculate impact level based on relationships and dependencies."""
        impact_score = 0
        
        # Base impact from enabled technologies
        enabled_count = len(tech_graph["enables"].get(tech["name"], []))
        impact_score += min(5, enabled_count)  # Cap at 5 points
        
        # Impact from related technologies
        related_count = len(tech_graph["related"].get(tech["name"], []))
        impact_score += min(3, related_count * 0.5)  # Cap at 3 points
        
        # Innovation type bonus
        if tech.get("innovation_type") == "breakthrough":
            impact_score += 2
        
        return min(10, max(1, round(impact_score)))

    def _find_techs_by_impact_area(self, tech_trees, target_area):
        """Find all technologies in a specific impact area."""
        related_techs = []
        for year, tree in tech_trees.items():
            for tech in tree.get("emerging_technologies", []):
                if target_area in tech.get("impact_areas", []):
                    related_techs.append(tech["name"])
        return related_techs

    def validate_tech_consistency(self, tech_data):
        """Validate technology data for consistency."""
        try:
            issues = []
            
            # Check for duplicate technologies
            all_techs = set()
            for tech in tech_data.get("emerging_technologies", []):
                if tech["name"] in all_techs:
                    issues.append(f"Duplicate technology: {tech['name']}")
                all_techs.add(tech["name"])
            
            # Validate dependencies
            for tech in tech_data.get("emerging_technologies", []):
                for dep in tech.get("dependencies", []):
                    if dep not in all_techs:
                        issues.append(f"Missing dependency {dep} for {tech['name']}")
            
            # Validate dates
            current_year = datetime.now().year
            for tech in tech_data.get("emerging_technologies", []):
                if int(tech["estimated_year"]) > int(tech["expected_maturity_year"]):
                    issues.append(f"Invalid dates for {tech['name']}: emergence after maturity")
                if int(tech["estimated_year"]) < current_year:
                    issues.append(f"Invalid emergence year for {tech['name']}: before current year")
            
            return len(issues) == 0, issues
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]
