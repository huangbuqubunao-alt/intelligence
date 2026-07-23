<!-- youtube-intel:weekly:v1 -->
# {{ iso_year }} 年第 {{ iso_week }} 周周报

- 时区：{{ timezone }}
- 高价值视频：{{ item_count }} 条

## Top 视频

{% if items %}{% for item in items %}### {{ loop.index }}. [[{{ item.note_path }}|{{ item.title }}]]

- 评分：{{ item.score }}
- 推荐理由：{{ item.reason }}
- 一句话总结：{{ item.summary }}

{% endfor %}{% else %}本周没有符合条件的高价值视频。
{% endif %}
## 重复关键词

{% if keywords %}{% for item in keywords %}- {{ item.keyword }}（{{ item.count }}）
{% endfor %}{% else %}- 无
{% endif %}
## 持续关注方向

{% if directions %}{% for direction in directions %}- {{ direction }}
{% endfor %}{% else %}- 本周暂无可持续关注方向。
{% endif %}
