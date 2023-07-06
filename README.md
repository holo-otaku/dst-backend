# DST backend

This is a project that uses the Python Flask framework and includes functionality for performing database migration.

## Pre-requisites

1. [pipenv](https://pipenv.pypa.io/en/latest/)
2. [odbc driver](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver15)

## Install Dependencies via pipenv

In the project directory, you can create a Python virtual environment using the following steps:

1. Open a terminal or command prompt.

2. Navigate to the project directory:

```bash
cd /path/to/your/project
```

3. Install package via pipenv:

```bash
pipenv install
```

This will create a virtual environment in the user's home directory.

It depends on the operating system, see [pipenv doc](https://pipenv.pypa.io/en/latest/virtualenv/#custom-virtual-environment-location) for more details.

Also, it will install all the dependencies listed in the `Pipfile` file in the project directory.

4. Activate the virtual environment:

```bash
pipenv shell
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
