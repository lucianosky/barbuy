# Barbuy — Claude Code CLI

## Contexto do projeto

**Barbuy** é uma calculadora solar de precisão nomeada em homenagem à astrônoma brasileira **Beatriz Barbuy** (IAG/USP).

Calcula nascer do sol, pôr do sol e duração do dia com precisão de segundos — a maioria dos sites web fornece apenas precisão de minutos.

**Repo:** `lucianosky/barbuy` (público)
**Local:** `/Users/sky/Documents/Sky/barbuy`
**Hospedagem:** Streamlit Cloud

---

## Stack

```
Python 3.x
Streamlit     interface web
astral        cálculos solares (sunrise, sunset, duração)
geopy         geocoding cidade → lat/lon (Nominatim/OpenStreetMap)
```

---

## Fonte original

`solstice.py` — script Python anterior de Luciano que inspirou o projeto.
Calcula sunrise/sunset em torno do solstício de inverno para uma cidade hardcoded.
Preservado no repo como referência.

---

## Fluxo da aplicação

1. Usuário digita nome da cidade (português, livre)
2. geopy/Nominatim faz geocoding → exibe latitude e longitude
3. Usuário escolhe data (date picker, default = hoje)
4. Usuário escolhe período: 10 / 30 / 60 dias (dropdown)
   - Período = X dias antes + data escolhida + X dias depois
5. astral calcula para cada dia do período:
   - Sunrise (nascer do sol) — precisão de segundos
   - Sunset (pôr do sol) — precisão de segundos
   - Duração do dia
   - Δs em relação ao nascer mais tardio do período
   - Δs em relação ao pôr mais cedo do período
   - Δs em relação ao dia mais curto do período
6. Exibe tabela formatada com todos os dias

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

- **Local:** `streamlit run app.py`
- **Produção:** Streamlit Cloud — conectar repo `lucianosky/barbuy`, branch `main`, arquivo `app.py`

---

## Regras

- Interface em português
- Precisão de segundos em todos os horários
- Fuso horário sempre da cidade selecionada (via geopy)
- Não alterar `solstice.py` — é o fonte original preservado
