---
{{ frontmatter }}
---
<!-- youtube-intel:managed:start:v1 -->
# {{ title }}

## 一句话总结

{{ analysis.summary }}

## 本地评分

- 分数：{{ score }}
- 理由：{{ scoring_reason }}
- 主题：{% for topic in topics %}{{ topic }}{% if not loop.last %}、{% endif %}{% endfor %}

{% if analysis.skipped %}## 深度分析状态

- 原因：{{ analysis.skip_reason }}
- 说明：{{ analysis.skip_message }}

{% endif %}## 核心观点

{% for item in analysis.core_points %}- {{ item }}
{% endfor %}
## 关键事实

{% for item in analysis.key_facts %}- {{ item }}
{% endfor %}
## 产品机会

{% for item in analysis.product_opportunities %}- {{ item }}
{% endfor %}
## 商业机会

{% for item in analysis.business_opportunities %}- {{ item }}
{% endfor %}
## 可落地方向

{% for item in analysis.actionable_directions %}- {{ item }}
{% endfor %}
## 待验证假设

{% for item in analysis.hypotheses_to_validate %}- {{ item }}
{% endfor %}
## 行动建议

{% for item in analysis.action_recommendations %}- {{ item }}
{% endfor %}
## 风险

{% for item in analysis.risks %}- {{ item }}
{% endfor %}
## 证据

{% for item in analysis.evidence %}- {{ item }}
{% endfor %}
## 标签

{% for item in analysis.keywords %}- {{ item }}
{% endfor %}
<!-- youtube-intel:managed:end:v1 -->
<!-- youtube-intel:user:start:v1 -->
## 我的思考

<!-- youtube-intel:user:end:v1 -->
