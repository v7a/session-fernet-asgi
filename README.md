# ASGI session middleware
Provides an encrypted and signed session that is stored as a [Fernet](https://github.com/fernet/spec) token on the client.

## Contributing
Before committing, run the following and check if it succeeds:
```sh
pip install --user -r requirements-dev.txt && \
black wtforms_field_factory.py && \
pylint wtforms_field_factory.py && \
pytest && \
coverage report --fail-under=100
```
