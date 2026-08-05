# Desafio Appmax — API de Transferências

Desafio técnico (Pessoa Desenvolvedora Python Pleno, teto de 24h). Enunciado completo em `Desafio.md` — ele é a fonte de verdade; este arquivo resume as decisões tomadas.

## Stack (fixa pelo enunciado)

- Python 3.12+, FastAPI, PostgreSQL, Docker / Docker Compose
- Escolhas nossas: SQLAlchemy 2 (síncrono) + psycopg 3, Alembic, httpx, pydantic-settings, pytest, ruff

## Pesos da avaliação (guiam a prioridade)

1. 30% — consistência de saldos, concorrência, falhas
2. 25% — modelagem e separação de responsabilidades
3. 20% — testes das regras críticas
4. 15% — comunicação (README, nomes, commits pequenos e descritivos)
5. 10% — operabilidade (`docker compose up` sem passos manuais, logs, /health)

## Decisões de arquitetura (acordadas)

- Monólito modular em camadas: `api/` (rotas + schemas), `application/` (use case de transferência), `domain/` (regras, entidades, exceções), `infrastructure/` (SQLAlchemy, repositórios, clientes HTTP externos).
- Dinheiro: `Decimal` na aplicação, `NUMERIC(18,2)` no Postgres. Nunca float.
- Fluxo da transferência:
  1. Validações de entrada (valor > 0, payer != payee, ambos existem, payer não é lojista, pré-checagem de saldo)
  2. Consultar autorizador externo (ANTES de abrir transação com locks — não segurar lock esperando rede)
  3. Transação única: `SELECT ... FOR UPDATE` nas duas carteiras em ordem determinística (menor user_id primeiro), revalidar saldo após o lock, debitar, creditar, criar transfer, commit
  4. Notificar DEPOIS do commit; falha na notificação não reverte a transferência (marca `notification_status = failed` e loga)
- Clientes HTTP externos: timeout explícito, tratamento de connection error/timeout/status inesperado/corpo inválido, exceções próprias do domínio.
- Autorizador indisponível ou negando => transferência não acontece, nada muda no banco.

## Comportamento real dos serviços externos (verificado em 2026-08-05)

- Authorize: 200 + `{"status":"success","data":{"authorization":true}}` OU 403 + `{"status":"fail","data":{"authorization":false}}` (nega aleatoriamente). Latência ~1s.
- Notify: 204 sem corpo OU 504 + `{"status":"error",...}` (falha aleatória, ~1/3). Latência ~0.8s.
- Cliente do authorize distingue 3 resultados: autorizado / negado (403 é resposta de negócio, não erro!) / indisponível (timeout, 5xx, corpo inválido). Corpo é fonte de verdade. SEM retry.
- Notify: síncrono pós-commit, 1 retry (total 2 tentativas), falha final => notification_status=failed + log, resposta segue 201.
- Timeout de 5s em ambos.

## Regras de negócio

- Usuário comum transfere para comum ou lojista; lojista NUNCA é pagador.
- CPF/CNPJ e e-mail únicos. Usuário tem senha (armazenar hash), mas SEM autenticação/login.
- Contrato obrigatório: `POST /transfer` com `{"value": 100.0, "payer": 4, "payee": 15}` — deve continuar funcionando mesmo se adicionarmos coisas.

## Fora de escopo (explícito no enunciado — NÃO implementar)

Autenticação/JWT, CRUD de usuários, frontend, broker de mensageria, microsserviços, CQRS/Event Sourcing, pipeline de CI. Se relevante para produção, apenas documentar no README (ex.: transactional outbox para notificação confiável).

## Operacional

- `docker compose up` deve: subir Postgres com healthcheck → `alembic upgrade head` → seed idempotente → uvicorn. Zero passos manuais.
- Teste de integração de concorrência usa Postgres real (nunca SQLite — comportamento de `FOR UPDATE` difere).
- Teste crítico: saldo 100, duas transferências concorrentes de 80 → exatamente uma conclui, saldo final 20, soma dos saldos preservada.
- Commits pequenos e descritivos desde o início (comunicação vale 15%).

## Códigos HTTP (decididos)

- 201 sucesso; 404 payer/payee inexistente; 422 valor inválido, payer == payee ou lojista como pagador (regra de negócio sobre a requisição); 403 SOMENTE autorização negada pelo autorizador; 409 saldo insuficiente; 503 autorizador indisponível/timeout.
- Corpo de erro padronizado: `{"code": "...", "message": "..."}` (ex.: MERCHANT_CANNOT_TRANSFER, INSUFFICIENT_BALANCE).
- Falha na notificação NÃO altera a resposta (segue 201).

## Decisões em aberto (discutir antes de implementar)

- Idempotency-Key: só se sobrar tempo depois do núcleo + testes; caso contrário, documentar como melhoria

## Contexto do candidato

O candidato (Lucas) precisa entender e defender cada decisão em um vídeo de 5 min. Ao implementar: explicar o porquê das escolhas, não esconder lógica em abstrações, preferir código simples e explicável a código sofisticado.
