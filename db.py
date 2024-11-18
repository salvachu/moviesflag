import sqlite3

def init_db():
    conn = sqlite3.connect("movies_cache.db")
    cursor = conn.cursor()

    # Crear tabla Movie
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Movie (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            year TEXT NOT NULL
        )
    """)

    # Crear tabla Country
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Country (
            name TEXT PRIMARY KEY,
            flag TEXT
        )
    """)

    # Crear tabla MovieCountry (relación)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS MovieCountry (
            movie_id TEXT,
            country_name TEXT,
            PRIMARY KEY (movie_id, country_name),
            FOREIGN KEY (movie_id) REFERENCES Movie(id),
            FOREIGN KEY (country_name) REFERENCES Country(name)
        )
    """)

    conn.commit()
    conn.close()
