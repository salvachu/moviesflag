from flask import Flask, render_template, request, jsonify
import requests
import json
import asyncio
import aiohttp

app = Flask(__name__)
apikey = "eda31927"

# Diccionario de caché en memoria
cache = {}

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
    # Verificar si la búsqueda ya está en caché
    cache_key = f"{search_text}_{page}"
    if cache_key in cache:
        return cache[cache_key]

    url = f"https://www.omdbapi.com/?s={search_text}&page={page}&apikey={apikey}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # Almacenar en caché el resultado de la búsqueda
        cache[cache_key] = data
        return data
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

async def merge_data_with_flags(filter, page=1):
    filmssearch = searchfilms(filter, page)
    moviesdetailswithflags = []
    if filmssearch and "Search" in filmssearch:
        async with aiohttp.ClientSession() as session:
            for movie in filmssearch["Search"]:
                moviedetails = getmoviedetails(movie)
                countries_names = moviedetails["Country"].split(",")
                countries = []
                
                # Crear tareas asíncronas para cada país
                tasks = [get_country_flag_async(session, country.strip()) for country in countries_names]
                flags = await asyncio.gather(*tasks)
                
                # Asignar banderas a los países
                for i, country in enumerate(countries_names):
                    countrywithflag = {
                        "name": country.strip(),
                        "flag": flags[i]
                    }
                    countries.append(countrywithflag)
                
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
