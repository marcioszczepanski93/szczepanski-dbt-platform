{#
  Converte uma taxa diaria (% a.d.) em taxa anualizada equivalente (% a.a.),
  compondo por 252 dias uteis: (1 + r/100)^252 - 1, em pontos percentuais.
  Usada para tornar a SELIC diaria (serie 11) comparavel a Meta SELIC (% a.a.).
  Nunca comparar frequencias diferentes sem conversao explicita.
#}
{% macro anualizar_taxa_diaria(coluna, dias_uteis=252) -%}
    round(
        ((power(1 + {{ coluna }} / 100.0, {{ dias_uteis }}) - 1) * 100)::numeric,
        2
    )
{%- endmacro %}
