from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from copilot.integration.skills import SkillRegistry

from copilot.models import InferredGoal, SkillChain

# Keyword → goal mapping for fallback inference
_GOAL_KEYWORDS: dict[str, tuple[str, str, list[str]]] = {
    # goal_name: (description_prefix, risk_level, keyword_list)
    "diagnose_performance": (
        "诊断",
        "medium",
        ["慢", "卡", "延迟", "性能", "慢查询", "响应慢", "cpu高", "内存高"],
    ),
    "cost_optimization": (
        "成本优化",
        "low",
        ["省", "成本", "账单", "费用", "计费", "节省", "费用高"],
    ),
    "inspection": (
        "巡检",
        "low",
        ["告警", "报警", "异常", "告警列表", "最近告警"],
    ),
    "proactive_inspection": (
        "主动巡检",
        "low",
        ["检查", "巡检", "看看", "查看", "检查一下", "巡检一下"],
    ),
    "resource_management": (
        "资源管理",
        "medium",
        ["创建", "删除", "启动", "停止", "重启", "扩容", "缩容"],
    ),
}


def _skill_chain_for_goal(
    goal: str, skill_registry: SkillRegistry | None
) -> list[SkillChain]:
    """Map a goal to candidate SkillChain objects."""
    chain_map: dict[str, list[str]] = {
        "diagnose_performance": [
            "qcloud-cvm-ops",
            "qcloud-monitor-ops",
            "qcloud-redis-ops",
        ],
        "cost_optimization": [
            "qcloud-finops-ops",
            "qcloud-cvm-ops",
        ],
        "inspection": [
            "qcloud-monitor-ops",
            "qcloud-cvm-ops",
        ],
        "proactive_inspection": [
            "qcloud-proactive-inspection",
            "qcloud-monitor-ops",
            "qcloud-cvm-ops",
        ],
        "resource_management": [
            "qcloud-cvm-ops",
            "qcloud-vpc-ops",
        ],
    }

    duration_map: dict[str, str] = {
        "diagnose_performance": "约 2 分钟",
        "cost_optimization": "约 1 分钟",
        "inspection": "约 1 分钟",
        "proactive_inspection": "约 3-5 分钟",
        "resource_management": "约 1 分钟",
    }

    desc_map: dict[str, str] = {
        "diagnose_performance": "快速诊断 (CVM + Monitor)",
        "cost_optimization": "成本分析与优化 (FinOps + CVM)",
        "inspection": "告警检查 (Monitor + CVM)",
        "proactive_inspection": "主动巡检 (Inspection + Monitor + CVM)",
        "resource_management": "资源操作 (CVM + VPC)",
    }

    # Build chains — when skill_registry is available, validate skills exist
    skills_list = chain_map.get(goal, [])
    if skill_registry is not None:
        known = getattr(skill_registry, "_known_skills", set())
        skills_list = [s for s in skills_list if s in known]

    chains: list[SkillChain] = []
    # Primary chain
    chains.append(
        SkillChain(
            skills=skills_list,
            description=desc_map.get(goal, goal),
            estimated_duration=duration_map.get(goal, "约 1 分钟"),
            risk="low",
            reads_only=True,
        )
    )

    # Alternative chains with slight variations
    if goal == "diagnose_performance":
        chains.append(
            SkillChain(
                skills=["qcloud-monitor-ops", "qcloud-cvm-ops"],
                description="Monitor 优先诊断 (Monitor + CVM)",
                estimated_duration="约 2 分钟",
                risk="low",
                reads_only=True,
            )
        )
    elif goal == "inspection":
        chains.append(
            SkillChain(
                skills=["qcloud-cvm-ops", "qcloud-monitor-ops"],
                description="CVM 优先巡检 (CVM + Monitor)",
                estimated_duration="约 1 分钟",
                risk="low",
                reads_only=True,
            )
        )

    return chains


@dataclass
class GoalInference:
    """Infer user goal from fuzzy natural language queries.

    This layer sits above the Classifier. When Classifier confidence < threshold,
    GoalInference uses an LLM to generate candidate goals + skill chains.
    """

    skill_registry: SkillRegistry | None = None
    llm_config: dict | None = None

    # Confidence threshold below which GoalInference is triggered
    CONFIDENCE_THRESHOLD: float = 0.6
    # Confidence below which clarifying questions are generated
    QUESTIONS_THRESHOLD: float = 0.7

    def infer(self, query: str, context: dict | None = None) -> InferredGoal:
        """Infer goal from fuzzy query.

        Process:
        1. If LLM config available: call LLM to generate candidate goals
        2. Map goal descriptions to skills via SkillRegistry
        3. Evaluate risk of each candidate chain
        4. Generate clarifying_questions if confidence < 0.7

        Returns InferredGoal with 2+ candidate_chains.
        Falls back to keyword matching if no LLM config.
        """
        ctx = context or {}

        if self.llm_config:
            return self._llm_infer(query, ctx)

        return self._keyword_infer(query, ctx)

    def _llm_infer(self, query: str, context: dict) -> InferredGoal:
        """Use LLM to generate goal + candidates (requires LLM config)."""
        # LLM inference path — construct prompt and call LLM
        prompt = (
            f"用户输入: {query}\n"
            f"上下文: {context}\n\n"
            "请推断用户意图 goal（如 diagnose_performance, cost_optimization 等），"
            "生成 2-3 个候选 SkillChain，每个 chain 包含 skills（技能名列表）、"
            "description（描述）、estimated_duration（预计时长）、risk（low/medium/high）、"
            "reads_only（是否只读操作）。\n"
            "返回 JSON 格式："
            '{"goal": "...", "description": "...", "confidence": 0.0-1.0, '
            '"candidate_chains": [...], "risk_level": "...", "clarifying_questions": [...]}'
        )

        # Call LLM via configured client
        import json

        try:
            client = self.llm_config.get("client")
            model = self.llm_config.get("model", "default")
            if client is None:
                raise ValueError("LLM client not configured")

            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            content = response.choices[0].message.content or "{}"

            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                raw = json.loads(content[start:end])
            else:
                raw = json.loads(content)
            chains = [
                SkillChain(
                    skills=c.get("skills", []),
                    description=c.get("description", ""),
                    estimated_duration=c.get("estimated_duration", "约 1 分钟"),
                    risk=c.get("risk", "low"),
                    reads_only=c.get("reads_only", True),
                )
                for c in raw.get("candidate_chains", [])
            ]
            # Mark destructive chains as high risk
            for c in chains:
                if not c.reads_only:
                    c.risk = "high"
            inferred = InferredGoal(
                goal=raw.get("goal", "unknown"),
                description=raw.get("description", ""),
                confidence=raw.get("confidence", 0.5),
                candidate_chains=chains,
                risk_level=raw.get("risk_level", "medium"),
                clarifying_questions=raw.get("clarifying_questions", []),
            )
        except Exception:  # noqa: BLE001 — fallback to keyword on any LLM/parse error
            # Fall back to keyword inference on any LLM error
            return self._keyword_infer(query, context)

        if inferred.confidence < self.QUESTIONS_THRESHOLD:
            inferred.clarifying_questions = self._generate_clarifying_questions(
                inferred, query
            )

        return inferred

    def _keyword_infer(self, query: str, context: dict) -> InferredGoal:
        """Fallback: keyword-based goal inference without LLM.

        Maps query keywords to skill chains:
        - "慢" / "卡" / "慢" → diagnose_performance chain
        - "省" / "成本" / "账单" → cost_optimization chain
        - "告警" / "报警" / "异常" → inspection chain
        - "检查" / "巡检" / "看看" → proactive_inspection chain
        """
        text = query.lower()

        matched_goal = None
        matched_desc = ""
        matched_risk = "low"
        max_hits = 0

        for goal, (desc_prefix, risk, keywords) in _GOAL_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in text)
            if hits > max_hits:
                max_hits = hits
                matched_goal = goal
                matched_desc = desc_prefix
                matched_risk = risk

        if matched_goal is None:
            matched_goal = "proactive_inspection"
            matched_desc = "主动巡检"
            matched_risk = "low"
            max_hits = 1

        confidence = min(0.5 + max_hits * 0.15, 0.9)

        chains = _skill_chain_for_goal(matched_goal, self.skill_registry)

        # Evaluate risk per chain
        for c in chains:
            c.risk = self._evaluate_risk(c)

        risk_level = "high" if any(c.risk == "high" for c in chains) else matched_risk

        inferred = InferredGoal(
            goal=matched_goal,
            description=f"{matched_desc} ({query[:20]}...)",
            confidence=confidence,
            candidate_chains=chains,
            risk_level=risk_level,
            clarifying_questions=[],
        )

        if confidence < self.QUESTIONS_THRESHOLD:
            inferred.clarifying_questions = self._generate_clarifying_questions(
                inferred, query
            )

        return inferred

    def _evaluate_risk(self, chain: SkillChain) -> str:
        """Return risk for a skill chain.

        If reads_only is False (destructive chain), mark as high risk.
        Otherwise return the chain's own risk assessment.
        """
        if not chain.reads_only:
            return "high"
        return chain.risk

    def _generate_clarifying_questions(
        self, goal: InferredGoal, query: str
    ) -> list[str]:
        """Generate questions to disambiguate when confidence < 0.7."""
        questions: list[str] = []

        if goal.goal in ("diagnose_performance", "proactive_inspection"):
            if "哪些" not in query and "哪个" not in query:
                questions.append("请问您想诊断哪台机器或哪个实例？")
            if "指标" not in query and "监控" not in query:
                questions.append("您关注哪些指标？例如 CPU、内存、网络或磁盘？")

        if goal.goal == "cost_optimization" and "哪个" not in query and "哪些" not in query:
            questions.append("请问您想分析哪个产品或项目的费用？")

        if goal.goal == "inspection" and "时间" not in query and "最近" not in query:
            questions.append("您想查看哪个时间范围的告警？")

        # Ensure we always return at least one question
        if not questions:
            questions.append("请问您具体想解决什么问题？")

        return questions
