# auth-service

Servicio de autenticación con FastAPI, PostgreSQL, JWT y SQLAlchemy.

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecutar la aplicación

```bash
python main.py
```

o con uvicorn directamente:

```bash
uvicorn main:app --reload
```

## Tests

La aplicación incluye una suite completa de tests con cobertura automática.

### Ejecutar todos los tests

```bash
pytest
```

### Ejecutar tests con cobertura detallada

```bash
pytest --cov=app --cov-report=html
```

### Ejecutar tests de un módulo específico

```bash
pytest tests/test_security.py
pytest tests/test_models.py
pytest tests/test_schemas.py
pytest tests/api/test_auth.py
```

### Ejecutar tests con salida verbose

```bash
pytest -v
```

## Estructura de tests

```
tests/
├── __init__.py
├── conftest.py              # Configuración y fixtures
├── test_security.py         # Tests de funciones de seguridad
├── test_models.py           # Tests de modelos SQLAlchemy
├── test_schemas.py          # Tests de validación Pydantic
├── test_email.py            # Tests de envío de emails
└── api/
    ├── __init__.py
    └── test_auth.py         # Tests de endpoints de autenticación
```

## Coverage

Después de ejecutar los tests con cobertura, se genera un reporte HTML en `htmlcov/index.html`

## Variables de entorno

Crear un archivo `.env` con:

```
DATABASE_URL=postgresql://user_auth:pass_auth@localhost:5432/auth_db
JWT_SECRET=your-secret-key-here
JWT_EXPIRE_MIN=60
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_SSL=True
SMTP_STARTTLS=False
```