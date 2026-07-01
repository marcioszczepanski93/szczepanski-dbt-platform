{#
  Sobrescreve o naming padrao do dbt, que prefixaria o schema alvo
  (ex.: public_staging). Aqui usamos o +schema declarado no dbt_project.yml
  como nome literal (staging, intermediate, marts), deixando os schemas limpos
  e previsiveis — casando com os schemas do warehouse.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
