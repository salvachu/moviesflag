from flask import Flask, render_template, request, jsonify
import requests
import json
import asyncio
import aiohttp
import sqlite3

app = Flask(__name__)
apikey = "eda31927"

# Inicializar la base de datos SQLite
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

    # Crear tabla MovieCountry (relación muchos a muchos)
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

init_db()  # Inicializa la base de datos al iniciar la aplicación

async def get_country_flag_async(session, country_name):
    url = f"https://restcountries.com/v3.1/name/{country_name}?fullText=true"
    async with session.get(url) as response:
        if response.status == 200:
            country_data = await response.json()
            if country_data:
                return country_data[0].get("flags", {}).get("svg", None)
    print(f"Failed to retrieve flag for country: {country_name}")
    return None

def searchfilms(search_text, page=1):
    url = f"https://www.omdbapi.com/?s={search_text}&page={page}&apikey={apikey}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to retrieve search results.")
        return None

def getmoviedetails(movie):
    url = f"https://www.omdbapi.com/?i={movie['imdbID']}&apikey={apikey}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to retrieve movie details.")
        return None

def get_cached_movie(movie_id):
    conn = sqlite3.connect("movies_cache.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Movie.title, Movie.year, Country.name, Country.flag
        FROM Movie
        JOIN MovieCountry ON Movie.id = MovieCountry.movie_id
        JOIN Country ON MovieCountry.country_name = Country.name
        WHERE Movie.id = ?
    """, (movie_id,))
    result = cursor.fetchall()
    conn.close()

    if result:
        # Reconstruir datos desde la base de datos
        countries = [{"name": row[2], "flag": row[3]} for row in result]
        return {
            "title": result[0][0],
            "year": result[0][1],
            "countries": countries
        }
    return None

async def merge_data_with_flags(filter, page=1):
    filmssearch = searchfilms(filter, page)
    moviesdetailswithflags = []
    if filmssearch and "Search" in filmssearch:
        async with aiohttp.ClientSession() as session:
            for movie in filmssearch["Search"]:
                cached_movie = get_cached_movie(movie["imdbID"])
                if cached_movie:
                    moviesdetailswithflags.append(cached_movie)
                    continue

                moviedetails = getmoviedetails(movie)
                countries_names = moviedetails["Country"].split(",")
                countries = []
                
                # Crear tareas asíncronas para cada país
                tasks = [get_country_flag_async(session, country.strip()) for country in countries_names]
                flags = await asyncio.gather(*tasks)
                
                # Guardar datos en SQLite
                conn = sqlite3.connect("movies_cache.db")
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO Movie (id, title, year) VALUES (?, ?, ?)",
                               (movie["imdbID"], moviedetails["Title"], moviedetails["Year"]))
                for i, country in enumerate(countries_names):
                    cursor.execute("INSERT OR IGNORE INTO Country (name, flag) VALUES (?, ?)",
                                   (country.strip(), flags[i]))
                    cursor.execute("INSERT OR IGNORE INTO MovieCountry (movie_id, country_name) VALUES (?, ?)",
                                   (movie["imdbID"], country.strip()))
                conn.commit()
                conn.close()

                # Construir la respuesta
                countries = [{"name": country.strip(), "flag": flags[i]} for i, country in enumerate(countries_names)]
                moviewithflags = {
                    "title": moviedetails["Title"],
                    "year": moviedetails["Year"],
                    "countries": countries
                }
                moviesdetailswithflags.append(moviewithflags)
    else:
        print("No se encontraron resultados para esta búsqueda.")
    return moviesdetailswithflags

@app.route("/")
async def index():
    filter = request.args.get("filter", "").upper()
    page = int(request.args.get("page", 1))  # Obtener la página de la URL
    movies = await merge_data_with_flags(filter, page)
    return render_template("index.html", movies=movies, filter=filter, page=page)

@app.route("/api/movies")
async def api_movies():
    filter = request.args.get("filter", "")
    page = int(request.args.get("page", 1))
    movies = await merge_data_with_flags(filter, page)
    return jsonify(movies)

if __name__ == "__main__":
    app.run(debug=True)
