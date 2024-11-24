# Crypto Monitor Bot

Bot para monitoramento de atividades de trading em tempo real.

## Configuração

1. Configure as variáveis de ambiente:
   - TELEGRAM_TOKEN: Token do seu bot do Telegram
   - TELEGRAM_CHAT_ID: ID do chat onde as mensagens serão enviadas

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Rodando localmente

```bash
python main.py
```

## Deploy

Este projeto está configurado para deploy no Render.com. 
Para fazer o deploy:

1. Fork este repositório
2. Crie uma conta no Render.com
3. Crie um novo Web Service
4. Conecte com seu repositório
5. Configure as variáveis de ambiente
6. Deploy!

## Estrutura dos arquivos

- `main.py`: Código principal do bot
- `requirements.txt`: Dependências do projeto
- `Dockerfile`: Configuração do container
- `.gitignore`: Arquivos ignorados pelo git