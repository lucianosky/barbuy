# Barbuy — Claude Code CLI

## Contexto do projeto

**Barbuy** é uma calculadora solar de precisão nomeada em homenagem à astrônoma brasileira **Beatriz Barbuy** (IAG/USP).

Calcula nascer do sol, pôr do sol e duração do dia com precisão de milissegundos — a maioria dos sites web fornece apenas precisão de minutos.

**Repo:** `lucianosky/barbuy` (público)
**Local:** `/Users/sky/Documents/Sky/barbuy`
**Hospedagem:** Streamlit Cloud

---

## Stack

```
Python 3.10
Streamlit        interface web
astral           cálculos solares (sunrise, sunset, duração) — precisão de microssegundos via VSOP87
geopy            geocoding cidade → lat/lon (Nominatim/OpenStreetMap)
timezonefinder   fuso horário a partir de lat/lon
pandas           tabela com Styler para coloração por célula
plotly           gráficos interativos
```

---

## Fonte original

`solstice.py` — script Python anterior de Luciano que inspirou o projeto.
Calcula sunrise/sunset em torno do solstício de inverno para uma cidade hardcoded.
Preservado no repo como referência. **Não alterar.**

---

## Fluxo da aplicação

1. Usuário digita nome da cidade (português, livre)
2. geopy/Nominatim faz geocoding → lat/lon + fuso horário via timezonefinder
3. Usuário escolhe janela: 10 / 20 / 30 dias ao redor de cada evento
4. astral calcula para cada dia:
   - Sunrise (nascer do sol) — precisão de milissegundos
   - Sunset (pôr do sol) — precisão de milissegundos
   - Duração do dia
   - Δs em relação ao nascer mais tardio do período
   - Δs em relação ao pôr mais cedo do período
   - Δs em relação ao dia mais curto do período
5. Exibe gráfico anual + 4 seções de evento + mini gráficos dos solstícios

---

## Estrutura da página

### Cabeçalho — duas colunas lado a lado

**Coluna esquerda:**
- Título e descrição
- Input de cidade
- Seletor de janela (10/20/30 dias)

**Coluna direita** (aparece após geocoding):
- Nome completo da cidade, lat/lon, fuso horário
- Para cada evento do ano (ordem calendário):
  - **Solstícios:** data do dia mais curto/longo, nascer mais tardio/cedo, pôr mais cedo/tardio
  - **Equinócios:** data do dia imediatamente acima de 12h e imediatamente abaixo de 12h

### Gráfico anual — "Curvas dos deltas"
- 3 curvas de delta ao longo dos 365 dias do ano atual
- Δ nascer tardio (amarelo), Δ pôr cedo (laranja-escuro), Δ duração curto (rosa)
- Marcadores: círculo nos mínimos (δ≈0), losango nos máximos
- Vlines coloridas marcando os 4 eventos astronômicos

### Mini gráficos dos solstícios — lado a lado
- Dois gráficos horizontais: solstício de inverno e solstício de verão
- Janela fixa de ±15 dias
- Mesmas 3 curvas de delta com marcadores min/max

### 4 seções de evento — ordem calendário
- Equinócio de março → Solstício de junho → Equinócio de setembro → Solstício de dezembro
- Cada seção: tabela de precisão com ±janela dias
- **Coloring nas tabelas:**
  - Solstícios: amarelo = nascer mais tardio/cedo, laranja = pôr mais cedo/tardio, rosa = dia mais curto/longo
  - Equinócios: verde pastel = dia imediatamente acima de 12h, lavanda = dia imediatamente abaixo de 12h
  - Azul = data do evento

---

## Convenções técnicas importantes

### Precisão de milissegundos
`time_to_td()` deve incluir `microseconds=t.microsecond` — sem isso os deltas de nascer/pôr mostram `.000` sempre.

### Colunas aninhadas — PROIBIDO
`st.columns()` dentro de `with col:` trava o Streamlit. Nunca usar colunas aninhadas.

### Cache
- `@st.cache_data` em `geocode_city` e `calculate_solar_rows`
- Cache key de `calculate_solar_rows`: (lat, lon, tz_name, date_start, date_end)
- Janela da coluna direita: ±15 dias fixos (diferente da janela selecionável do usuário)

### Hemisfério
- Latitude < 0 = hemisfério sul
- Sul: junho = inverno, dezembro = verão
- Norte: junho = verão, dezembro = inverno
- Labels de evento ajustados automaticamente

### Datas dos eventos (aproximadas)
- 20 março — equinócio
- 21 junho — solstício
- 22 setembro — equinócio
- 21 dezembro — solstício

### Python local
- `pip3` instala no Python 3.10, `python3` aponta para 3.13
- Sempre rodar com: `python3.10 -m streamlit run app.py`

---

## Estrutura de arquivos

```
barbuy/
├── app.py            ← aplicação Streamlit principal
├── solstice.py       ← fonte original preservado (referência)
├── requirements.txt  ← dependências para Streamlit Cloud
└── CLAUDE.md
```

---

## Deploy

- **Local:** `python3.10 -m streamlit run app.py`
- **Produção:** Streamlit Cloud — conectar repo `lucianosky/barbuy`, branch `main`, arquivo `app.py`

---

## Regras

- Interface em português
- Precisão de milissegundos em todos os horários
- Fuso horário sempre da cidade selecionada (via timezonefinder)
- Não alterar `solstice.py` — é o fonte original preservado
- Não usar colunas aninhadas (Streamlit não suporta)
