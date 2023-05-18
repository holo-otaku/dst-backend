# DST backend

This is a project that uses the Python Flask framework and includes functionality for performing database migration.

## Creating a Python Virtual Environment

In the project directory, you can create a Python virtual environment using the following steps:

1. Open a terminal or command prompt.

2. Navigate to the project directory:

```
cd /path/to/your/project
```

3. Create a Python virtual environment:

```
python -m venv venv
```

This will create a virtual environment named `venv` in the project directory.

4. Activate the virtual environment:

- On Windows:

  ```
  venv\Scripts\activate
  ```

- On macOS or Linux:

  ```
  source venv/bin/activate
  ```

After activating the virtual environment, you will see the command prompt prefix change to `(venv)`, indicating that the virtual environment has been successfully activated.

## Installing Dependencies

After activating the virtual environment, you can install the project's dependencies using the following steps:

1. Make sure the virtual environment is active.

2. Install the dependencies from the `requirements.txt` file:

```
pip install -r requirements.txt
```

This will install all the dependencies listed in the `requirements.txt` file in the project directory.

## Database Migration

After installing the project's dependencies, you can perform database migration to create database tables or update table structures:

1. In the project directory, run the following command to initialize the database:

```
flask db init
```

This will create a `migrations` folder in the project directory to store migration-related files.

2. Create a new database migration:

```
flask db migrate
```

3. Create migration tables:

```
flask db upgrade
```
This will automatically detect the model classes in the project and generate a new database migration file.

## Docker

1. Build the Docker images:

```
docker-compose build
```

2. Start the Docker containers:

```
docker-compose up -d
```

3. Attach to the shell of the application container:

```
docker-compose exec <service_name> sh
```

4. Inside the container, run the database migrations:

```
flask db upgrade
```