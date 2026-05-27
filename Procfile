web: gunicorn --workers 2 --bind 0.0.0.0:$PORT "ic_agent.server:create_app()"
bot: python -m ic_agent.bot
