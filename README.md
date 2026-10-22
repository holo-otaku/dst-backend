# DST backend

This is a project that uses the Python Flask framework and includes functionality for performing database migration.

## Pre-requisites

1. [uv](https://docs.astral.sh/uv/)
2. [odbc driver](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver15)

## Install Dependencies via uv

In the project directory, run:

```bash
uv sync
```

This creates `.venv/` in the project directory, using the Python version in `.python-version` (uv downloads it if missing), and installs the dependencies from `uv.lock`, including the `dev` group. Run commands inside it with `uv run`, e.g. `uv run pytest`.

On Apple Silicon macOS, pyodbc has no prebuilt wheel and is built from source. If `import pyodbc` fails with `symbol not found ... '_SQLAllocHandle'`, rebuild it against Homebrew's unixODBC:

```bash
brew install unixodbc
P=$(brew --prefix unixodbc)
CPPFLAGS="-I$P/include" LDFLAGS="-L$P/lib" uv pip install --python .venv --reinstall --no-cache --no-binary pyodbc pyodbc==5.2.0
```

## Run required services with docker-compose

In the project directory, run the following command to start the required services:

```bash
docker-compose up -d
```

This will start the following services:

1. MySQL
2. phpmyadmin

## Configure Database Connection

Copy the `config.py.example` file in the project directory to `config.py` and modify the database connection information in the `config.py` file.

## Run the Application

In the project directory, run the following command to start the application:

```bash
flask run
```

_Note: Make sure the virtual environment is activated before running the application._

## Database Migration

After installing the project's dependencies, you can perform database migration to create database tables or update table structures:

1. In the project directory, run the following command to initialize the database:

```bash
flask db init
```

This will create a `migrations` folder in the project directory to store migration-related files.

2. Create a new database migration:

```bash
flask db migrate
```

3. Create migration tables:

```bash
flask db upgrade
```

This will automatically detect the model classes in the project and generate a new database migration file.

## Default Admin Account

Upon starting the application, a default admin account is created. You can use the following credentials to log in as an administrator:

- Username: admin
- Password: admin

Please make sure to change the default password after logging in for the first time.

## API Document

After starting the application, you can access the Swagger API documentation at the following URL:

```
http://127.0.0.1:5001/api/docs/
```

The Swagger API documentation provides detailed information about the available endpoints, request/response structures, and parameters for interacting with the API. It serves as a helpful resource for developers to understand and utilize the API effectively.

Please refer to the Swagger API documentation for more information on how to interact with the API endpoints and perform various operations within your application.
