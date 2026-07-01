{#
  Variacao percentual de uma coluna vs N periodos atras (lag), ordenada por `ordem`.
  - offset=1  -> MoM (mes vs mes anterior)
  - offset=12 -> YoY (mes vs mesmo mes do ano anterior)
  `particao` e opcional: para uma serie unica no formato largo (uma linha por mes),
  deixe none; para formato longo com varias series, passe a coluna de particao.
#}
{% macro variacao_percentual(coluna, ordem, offset=1, particao=none) -%}
    {%- set over_clause -%}
        over (
            {% if particao is not none %}partition by {{ particao }} {% endif %}order by {{ ordem }}
        )
    {%- endset -%}
    round(
        (
            ({{ coluna }} - lag({{ coluna }}, {{ offset }}) {{ over_clause }})
            / nullif(lag({{ coluna }}, {{ offset }}) {{ over_clause }}, 0)
        ) * 100,
        2
    )
{%- endmacro %}
