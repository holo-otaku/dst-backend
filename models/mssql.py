import pyodbc


def Connect(connection_string):
    conn = pyodbc.connect(connection_string, timeout=3)

    return conn
