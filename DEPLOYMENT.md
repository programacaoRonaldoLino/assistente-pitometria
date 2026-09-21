# Publicação do portal

O portal usa uma URL pública, mas não permite consulta anônima. Cada pessoa entra com uma conta Google (ou Microsoft, se configurada) e só consulta depois que o administrador autorizar seu e-mail.

## Secrets obrigatórios

Cadastre estes valores no provedor de hospedagem. Nunca publique o arquivo de secrets no repositório.

- `OPENAI_API_KEY`: chave da API da OpenAI.
- `OPENAI_MODEL`: `gpt-5.6-luna`.
- `OPENAI_VECTOR_STORE_ID`: Vector Store existente; evita criar um novo no primeiro deploy.
- `APP_ADMIN_EMAIL`: e-mail do administrador que pode indexar PDFs, conceder e revogar acesso.
- `APP_DATA_DIR`: caminho de um volume persistente. Ele mantém usuários, cotas, índice local e configuração dos manuais.

## Login

Configure OIDC no provedor de identidade e adicione a URL pública seguida de `/oauth2callback` como URL de retorno. Use as chaves de `[auth]` no exemplo de secrets. Para uso corporativo, prefira Microsoft; para um grupo externo, Google costuma ser mais simples.

## Operação

1. Entre com o e-mail configurado em `APP_ADMIN_EMAIL`.
2. Indexe os PDFs em **Administração → Indexar manuais**.
3. Em **Liberar acesso e cotas**, adicione cada e-mail e o limite diário de respostas com IA.
4. A busca local é gratuita e mostra trechos; somente **Resposta com IA** consome a cota.
5. Quando alguém atingir a cota, escolha a pessoa na administração e use **Liberar extras**.

## Persistência

Hospedagens com disco efêmero não servem para este projeto sem um volume persistente ou banco de dados externo. Sem persistência, permissões, cotas e o índice local são apagados após um novo deploy.
