# RELATÓRIO DE PRECIFICAÇÃO — Core-AI
**Versão:** MVP 1.0 | **Data:** 27/03/2026 | **Moeda:** BRL (R$)

---

## BASE DE CÁLCULO

### Custos Operacionais Mensais Estimados

| Item | Custo Estimado/mês |
|------|-------------------|
| Infraestrutura Railway (API + PostgreSQL) | R$ 100,00 |
| API Gemini 2.5 Flash (estimativa com uso real) | R$ 40,00 |
| Autenticação (Clerk/Auth0 — tier básico) | R$ 70,00 |
| E-mail transacional (Resend tier básico) | R$ 20,00 |
| Pagamentos Stripe (fixo — variável por transação) | R$ 0,00 |
| **Total operacional fixo/mês** | **R$ 230,00** |

> ⚠️ O custo do Gemini é variável. Estimativa baseada em 50 usuários × 10 análises/mês × ~R$0,08/análise = R$40/mês. Escala conforme crescimento.

### Custo por Usuário e por Unidade

| Métrica | Valor |
|---------|-------|
| Custo operacional mensal total | R$ 230,00 |
| Custo por usuário ativo/mês (base: 50 usuários) | R$ 4,60 |
| Custo por análise de exame (Gemini + infra proporcional) | R$ 0,46 |
| Usuários pagantes para break-even (plano Normal) | ~8 usuários |

---

## 🎯 ESTRUTURA DE PLANOS

### 🆓 FREE — Plano de Entrada

| Campo | Detalhe |
|-------|---------|
| **Preço** | Gratuito |
| **Análises incluídas** | 3 análises/mês |
| **Recursos incluídos** | Análise de exames com citações científicas, sugestões de follow-up clínico |
| **Recursos excluídos** | Histórico de pacientes, dashboard, exportação de relatórios, suporte prioritário |
| **Custo estimado por usuário free** | R$ 1,38/mês |
| **Objetivo estratégico** | Aquisição, validação e prova de valor |

**Justificativa:** 3 análises/mês representa uma semana de atendimento leve — suficiente para o nutricionista sentir o valor do co-piloto sem custo zero operacional relevante. O custo de R$1,38/usuário free é apenas 30% do custo médio por usuário, aceitável para um MVP em tração. O limite de 3 cria urgência natural de upgrade para quem atende mais de 1 paciente por semana.

---

### ⚡ ESSENCIAL — Para quem está começando

| Campo | Detalhe |
|-------|---------|
| **Preço** | R$ 39/mês |
| **Análises incluídas** | 15 análises/mês |
| **Recursos incluídos** | Tudo do Free + histórico básico de pacientes (até 15 perfis) |
| **Recursos excluídos** | Dashboard analítico, exportação PDF de relatórios, suporte prioritário |
| **Custo operacional coberto** | R$ 6,90/usuário |
| **Margem estimada** | ~82% sobre o custo variável por usuário |

**Justificativa:** R$39/mês é psicologicamente acessível para um nutricionista autônomo — equivale a menos de 1 consulta particular. Com 15 análises/mês, cobre o perfil de uso médio identificado (6–15/mês). A margem é alta porque o custo variável de Gemini por análise é muito baixo; o que protege a margem é o custo fixo de infraestrutura, já diluído.

---

### 💎 PROFISSIONAL — Para quem escala a clínica

| Campo | Detalhe |
|-------|---------|
| **Preço** | R$ 69/mês |
| **Análises incluídas** | 40 análises/mês |
| **Recursos incluídos** | Tudo do Essencial + dashboard analítico, exportação de relatórios em PDF, histórico ilimitado de pacientes |
| **Recursos excluídos** | Chatbot de suporte dedicado |
| **Custo operacional coberto** | R$ 18,40/usuário (análises Gemini) + fixo |
| **Margem estimada** | ~73% |
| **Diferencial de valor** | Dashboard + exportação de PDF tornam o Core-AI um produto completo de prontuário clínico, não só um analisador |

**Justificativa:** O salto de R$39 → R$69 é justificado por dois recursos de alto valor percebido: o **dashboard** (visão gerencial da clínica) e a **exportação de relatórios em PDF** (entregável profissional para o paciente). Para um nutricionista que atende 20–40 pacientes/mês, R$69 representa menos de R$2 por consulta — custo invisível frente ao ganho de tempo e qualidade.

---

### 🚀 PRO — Para clínicas e alta demanda

| Campo | Detalhe |
|-------|---------|
| **Preço** | R$ 99/mês |
| **Análises incluídas** | 80 análises/mês |
| **Recursos incluídos** | Tudo do Profissional + chatbot de suporte/IA integrado, acesso antecipado a novas features, suporte prioritário |
| **Custo operacional coberto** | R$ 36,80/usuário (análises) + fixo |
| **Margem estimada** | ~63% |
| **Público ideal** | Nutricionistas com alta demanda, clínicas com múltiplos profissionais ou pesquisadores clínicos |
| **Diferencial de valor** | Chatbot de IA integrado ao RAG científico — o nutricionista tira dúvidas clínicas pontuais sem precisar abrir uma análise completa |

**Justificativa:** R$99/mês posiciona o Pro como topo acessível — não é caro, mas claramente premium. O chatbot é o diferencial exclusivo: acesso conversacional direto à base científica do Core-AI, sem precisar processar um exame. Para clínicas com equipe, o custo per capita cai ainda mais. O plano Pro funciona como âncora: faz o Profissional (R$69) parecer "a escolha inteligente".

---

## 📈 PROJEÇÃO DE BREAK-EVEN (Cenário Conservador)

Estimativa para os primeiros 3–6 meses com até 50 usuários:

| Mix de usuários | Receita/mês | Custo/mês | Resultado |
|-----------------|-------------|-----------|-----------|
| 60% Free (30) / 25% Essencial (12) / 10% Prof. (5) / 5% Pro (3) | R$ 1.122 | R$ 270* | **+R$ 852** |
| 70% Free (35) / 20% Essencial (10) / 7% Prof. (3) / 3% Pro (2) | R$ 787 | R$ 255* | **+R$ 532** |
| 80% Free (40) / 15% Essencial (7) / 4% Prof. (2) / 1% Pro (1) | R$ 510 | R$ 245* | **+R$ 265** |

*Custo total inclui infraestrutura fixa + custo variável Gemini proporcional ao uso.

> ✅ **Boa notícia:** Mesmo no cenário mais conservador (80% free), o produto é lucrativo com poucos usuários pagantes. O break-even operacional é atingido com apenas **6–8 usuários no plano Essencial**.

> ⚠️ **Nota MVP:** Esta precificação foi calibrada para priorizar **adoção e tração** sobre margem de lucro. Recomenda-se revisão em 3–6 meses após validação de mercado.

---

## 💡 RECOMENDAÇÕES ESTRATÉGICAS

**1. Teste A/B no limite do Free**
Teste 3 vs. 5 análises/mês no plano gratuito. Um limite maior pode acelerar a adoção inicial e reduzir o churn de nutricionistas que ainda não entendem o valor do produto. Com o custo baixo por análise (~R$0,46), o risco financeiro é mínimo.

**2. Gatilho de upgrade natural**
- **Free → Essencial:** Banner de "você usou 2 de 3 análises este mês" + destaque do histórico de pacientes
- **Essencial → Profissional:** Mostrar prévia bloqueada do dashboard e do botão "Exportar PDF" após cada análise
- **Profissional → Pro:** Acesso trial de 7 dias ao chatbot clínico — quem experimenta tende a não abrir mão

**3. Plano anual com desconto**
Ofereça **2 meses grátis** no pagamento anual (equivale a ~17% de desconto). Melhora o fluxo de caixa e reduz churn. Sugestão: Essencial Anual por R$390/ano (vs. R$468 mensal).

**4. ⚠️ Alerta de custo: escalonamento do Gemini**
O custo do Gemini cresce linearmente com o uso. Se você tiver usuários Pro ativos usando 80 análises/mês cada, o custo de LLM pode subir rapidamente. **Implemente rate limiting por plano desde o início** e monitore o consumo de tokens por sessão. Considere cachear respostas para perguntas clínicas recorrentes (ex: interpretações de biomarcadores comuns).

---

## PREMISSAS E LIMITAÇÕES

- Custo Railway estimado em R$100/mês (ponto médio da faixa R$50–150 informada)
- Custo Gemini estimado com base em ~12k tokens por análise completa (exame + RAG + resposta + follow-up) ao preço do `gemini-2.5-flash`
- Custos de autenticação e e-mail são estimativas de mercado para serviços típicos de MVP
- Stripe não tem custo fixo, mas incide ~2,4% + R$0,60 por transação (não incluído nas margens acima)
- Preços devem ser validados com usuários reais antes de fixação definitiva
- Esta análise é baseada nas informações fornecidas pelo fundador em 27/03/2026