# Desafio Técnico - Pessoa Desenvolvedora Python (Pleno)

Obrigado pelo interesse na vaga!

Antes de começar, um ponto importante: **este desafio tem um teto de 24 horas**.

Não esperamos uma solução completa nem perfeita. Queremos entender como você toma decisões técnicas diante de um problema real e de um tempo limitado. Se algo não couber nessas 24 horas, documente no README a abordagem que seguiria com mais tempo.

> Entregar menos, com boas decisões e justificativas, vale mais do que entregar tudo de forma superficial.

------------------------------------------------------------------------

# Contexto

Seu objetivo é implementar o núcleo responsável por movimentações financeiras entre usuários, garantindo a consistência dos saldos mesmo diante de falhas em dependências externas.

Este desafio foi pensado para avaliar decisões de engenharia, modelagem e qualidade de código, e não a quantidade de funcionalidades implementadas.

------------------------------------------------------------------------

# Ambiente e stack

Para conseguirmos comparar as entregas de forma justa, a stack é fixa:

-   Python 3.12+
-   FastAPI
-   PostgreSQL
-   Docker / Docker Compose

Bibliotecas de apoio (ORM, cliente HTTP, gerenciador de dependências e
framework de testes) ficam a seu critério. Explique brevemente suas
escolhas no README.

Evite geradores automáticos de CRUD ou scaffolding excessivo. Queremos entender como você estrutura uma aplicação.

------------------------------------------------------------------------

# Regras de negócio

Existem dois tipos de usuário:

-   Usuário comum
-   Lojista

Ambos possuem uma carteira com saldo.

Cada usuário possui:

-   Nome completo
-   CPF/CNPJ
-   E-mail
-   Senha

CPF/CNPJ e e-mail devem ser únicos.

As regras da transferência são:

-   Usuários comuns podem transferir para usuários comuns e lojistas.
-   Lojistas apenas recebem transferências.
-   O pagador deve possuir saldo suficiente antes da transferência.
-   A transferência deve garantir consistência dos saldos. Em caso de falha durante a operação, o sistema não pode deixar dinheiro "no meio do caminho".

------------------------------------------------------------------------

# Integrações

Antes de concluir uma transferência, consulte o autorizador externo:

GET https://util.devi.tools/api/v2/authorize

Após uma transferência concluída, o beneficiário deve ser notificado
utilizando:

POST https://util.devi.tools/api/v1/notify

Considere que serviços externos representam dependências de terceiros e podem falhar de diferentes maneiras. A forma como você escolhe lidar com essas falhas faz parte da avaliação. Sempre que julgar necessário, documente suas decisões no README.

------------------------------------------------------------------------

# API

Implemente obrigatoriamente o seguinte contrato:

``` http
POST /transfer

{
  "value": 100.0,
  "payer": 4,
  "payee": 15
}
```

Caso queira propor contratos adicionais, fique à vontade, desde que este
permaneça funcionando.

------------------------------------------------------------------------

# O que esperamos encontrar

-   POST /transfer funcionando
-   Regras de negócio implementadas
-   Tratamento consistente da transferência
-   Integração com autorizador
-   Notificação do beneficiário
-   docker compose up funcionando sem passos manuais
-   Migrations executadas automaticamente
-   Seed com alguns usuários
-   Pelo menos um teste unitário e um teste de integração
-   README documentando as principais decisões

------------------------------------------------------------------------

# Fora de escopo

Não implemente:

-   Autenticação
-   CRUD completo de usuários
-   Frontend
-   Broker de mensageria
-   Microsserviços
-   CQRS/Event Sourcing
-   Pipeline de CI

Caso considere algum desses itens importante para produção, apenas
documente.

------------------------------------------------------------------------

# Qualidade

Esperamos código idiomático e legível.

Como referência:

-   ruff format
-   pytest

Disponibilize comandos para execução no README ou Makefile.

------------------------------------------------------------------------

# README

Esperamos encontrar:

-   arquitetura escolhida
-   principais decisões
-   trade-offs
-   limitações
-   uso de IA
-   como executar
-   como rodar os testes
-   o que faria com mais tempo

Não esperamos documentação extensa, apenas suficiente para entendermos
seu raciocínio.

------------------------------------------------------------------------

# Uso de IA

É permitido e esperado.

Queremos apenas que você informe:

1.  Em quais partes a IA auxiliou.
2.  Quais decisões finais foram suas.

Não esperamos um histórico de prompts.

Você será avaliado pela capacidade de compreender e defender sua
solução.

------------------------------------------------------------------------
# Entrega

Envie:

1.  Link do repositório público.
2.  Vídeo ou áudio de até 5 minutos apresentando sua solução e explicando:
    -   decisão mais difícil;
    -   principais trade-offs;
    -   o que faria diferente com mais tempo.


------------------------------------------------------------------------
# O que será avaliado

| Dimensão                                                            | Peso |
| ------------------------------------------------------------------- | ---- |
| Correção da solução: Consistência dos saldos, concorrência e falhas | 30%  |
| Modelagem: Clareza do domínio e separação de responsabilidades      | 25%  |
| Testes: Cobertura das regras críticas                               | 20%  |
| Comunicação: README, nomes, commits                                 | 15%  |
| Operabilidade: Facilidade para executar e observar a aplicação      | 10%  |

Uma solução excelente não é necessariamente a que possui mais funcionalidades. Valorizamos boas decisões de arquitetura, código claro, testes relevantes e capacidade de justificar escolhas e limitações.

Boa sorte!
