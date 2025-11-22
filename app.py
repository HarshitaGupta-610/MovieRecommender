from flask import Flask, render_template, request
from recommender import MovieRecommender

app = Flask(__name__)

# Load the recommender with your movies.json
reco = MovieRecommender("movies.json")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/selections", methods=["POST", "GET"])
def selections():
    if request.method == "GET":
        return render_template("selections.html")
    return render_template("selections.html")

@app.route("/results", methods=["POST"])
def results():
    industry = request.form.get("industry")
    genre = request.form.get("genre")
    movie_type = request.form.get("movie_type")

    # Get FULL MOVIE OBJECTS, not just titles
    movies = reco.recommend(industry, genre, movie_type, top_n=5)

    # Send full movies to template
    return render_template(
        "results.html",
        movies=movies,
        industry=industry,
        genre=genre,
        movie_type=movie_type
    )

if __name__ == "__main__":
    app.run(debug=True)
