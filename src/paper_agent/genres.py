from __future__ import annotations

from dataclasses import dataclass

from paper_agent.models import Genre


@dataclass(frozen=True)
class GenreSection:
    title: str
    ratio: float
    purpose: str


GENRE_PROFILES: dict[Genre, tuple[GenreSection, ...]] = {
    Genre.GENERAL_ESSAY: (
        GenreSection("引言", 0.12, "交代问题背景、范围、分析性问题和中心论点"),
        GenreSection("概念与背景", 0.18, "界定核心概念并建立讨论所需背景"),
        GenreSection("主要论证", 0.38, "以分论点、证据和推理支持中心论点"),
        GenreSection("反方观点与回应", 0.17, "呈现合理反对意见、限制条件及回应"),
        GenreSection("结论", 0.15, "综合回答问题、说明意义并避免引入新论据"),
    ),
    Genre.LITERATURE_REVIEW: (
        GenreSection("引言与综述范围", 0.12, "定义问题、范围、纳入标准和组织方式"),
        GenreSection("主题与观点综合", 0.42, "跨来源比较主题、立场、方法、共识与分歧"),
        GenreSection("方法与证据评价", 0.22, "评价主要研究路径、证据强度和局限"),
        GenreSection("研究空白与趋势", 0.14, "基于已有综合识别空白、争议和发展方向"),
        GenreSection("结论", 0.10, "回答综述问题并总结知识状态"),
    ),
    Genre.SURVEY_REPORT: (
        GenreSection("背景与目标", 0.12, "说明调研问题、对象和用途"),
        GenreSection("方法", 0.18, "如实说明样本、工具、过程和分析方法"),
        GenreSection("结果", 0.25, "报告真实数据及观察，不混入无根据解释"),
        GenreSection("讨论", 0.25, "解释结果、联系资料并说明限制"),
        GenreSection("建议", 0.10, "提出可由结果与讨论推出的建议"),
        GenreSection("结论", 0.10, "概括核心发现并回应调研目标"),
    ),
    Genre.UNDERGRAD_THESIS: (
        GenreSection("引言", 0.10, "建立背景、问题、意义、范围与全文结构"),
        GenreSection("文献综述与理论基础", 0.22, "综合已有研究并建立分析框架"),
        GenreSection("研究设计或材料", 0.15, "如实说明研究路径、材料、方法与限制"),
        GenreSection("分析与结果", 0.28, "系统呈现分析过程、证据和结果"),
        GenreSection("讨论", 0.15, "解释结果、回应研究问题并联系已有研究"),
        GenreSection("结论", 0.10, "总结贡献、局限和后续方向"),
    ),
}


def profile_for(genre: Genre) -> tuple[GenreSection, ...]:
    return GENRE_PROFILES[genre]


def rhetorical_moves_for(genre: Genre, title: str) -> list[str]:
    """Return section-level communicative moves used as planning and audit criteria."""
    common = {
        "引言": ["建立研究或讨论语境", "明确问题与范围", "提出中心判断", "预告全文结构"],
        "结论": ["直接回答研究问题", "综合主要发现", "说明适用边界", "不引入新证据"],
        "方法": ["交代材料或样本", "说明过程与分析方法", "说明局限与可复核条件"],
        "结果": ["区分事实呈现与解释", "按问题组织发现", "用可定位证据支持陈述"],
        "讨论": ["解释发现的意义", "联系已有观点", "处理替代解释", "说明局限"],
    }
    for marker, moves in common.items():
        if marker in title:
            return moves
    if genre == Genre.LITERATURE_REVIEW:
        return ["跨来源归类观点", "比较共识与分歧", "评价证据与方法", "形成综合判断"]
    if genre == Genre.SURVEY_REPORT:
        return ["回应调研目标", "引用真实数据", "解释而不夸大", "连接建议与发现"]
    if genre == Genre.UNDERGRAD_THESIS:
        return ["提出分论点", "呈现材料", "解释证据与论点的关系", "说明边界"]
    return ["提出分论点", "呈现相关证据", "完成论证担保", "回应反例或限制"]
