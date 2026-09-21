# Assistente técnico de Pitometria e Macromedição

Portal de consulta a manuais técnicos. O administrador indexa os PDFs e
controla quais pessoas podem consultar. Usuários autorizados podem fazer uma
busca local gratuita ou uma resposta elaborada por IA, sujeita a limite diário.

## Recursos

- Login com conta Google (configurado por OIDC).
- Área exclusiva do administrador para enviar e indexar manuais em PDF.
- Busca local sem custo por consulta.
- Respostas por IA com citações das fontes e controle de cota por usuário.
- Permissões e cotas persistidas em SQLite.

## Execução local

1. Crie e ative um ambiente virtual com Python 3.10 ou superior.
2. Instale as dependências: `pip install -r requirements.txt`.
3. Copie `.streamlit/secrets.example.toml` para
   `.streamlit/secrets.toml` e preencha as credenciais OAuth do Google.
4. Defina o e-mail do administrador em `APP_ADMIN_EMAIL`.
5. Execute: `streamlit run app.py`.

Para respostas com IA, configure também a variável `OPENAI_API_KEY`. A chave
e o identificador do Vector Store são definidos pela tela administrativa e
ficam fora do Git.

## Publicação

O guia completo para publicar no Render, incluindo volume persistente,
variáveis de ambiente e configuração do login Google, está em
[DEPLOYMENT.md](DEPLOYMENT.md).

## Dados sensíveis

Manuais, bancos locais, credenciais OAuth, chave da OpenAI e configuração do
Vector Store não são versionados. Nunca envie esses arquivos para o GitHub.
