|Hostname|
|:--|
{% for device in queryset %}
{% if device.status %}
|{{ device.name }}|
{% endif %}
{% endfor %}
