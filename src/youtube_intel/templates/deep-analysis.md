---
{{ frontmatter }}
---
<!-- youtube-intel:managed:start:v1 -->
# {{ title }}

{% for section in sections %}## {{ section.title }}

{% for claim in section.claims %}- {{ claim.text }} ({{ claim.citations }})
{% if claim.uncertain %}  {{ language_notice }}
{% endif %}{% endfor %}
{% endfor %}## {{ evidence_title }}

{% for item in evidence %}- {{ item.id }} {{ item.timing }}: {{ item.excerpt }}
{% endfor %}
<!-- youtube-intel:managed:end:v1 -->
<!-- youtube-intel:user:start:v1 -->
## {{ user_title }}

<!-- youtube-intel:user:end:v1 -->
