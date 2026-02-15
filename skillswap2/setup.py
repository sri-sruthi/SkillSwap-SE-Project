from setuptools import setup, find_packages

setup(
    name="skillswap",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "psycopg2-binary",
        "python-jose[cryptography]",
        "passlib[bcrypt]",
        "bcrypt==4.0.1",
        "python-multipart",
        "pydantic[email]",  # Changed this line - added [email]
        "python-dotenv",
        "alembic",
        "numpy",
        "scikit-learn",
    ],
)
