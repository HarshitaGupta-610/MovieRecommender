import json
import os
import random
import math
import re
from datetime import datetime


class BaseRecommender:
    """
    Base class demonstrating:
    - File I/O
    - JSON handling
    - OOP inheritance
    - Logging & exception handling
    """

    def __init__(self, data_file: str):
        self.data_file = data_file

    # ---------- File Handling ----------

    def load_json_list(self, path, default=None):
        """Load JSON list safely."""
        if default is None:
            default = []

        if not os.path.exists(path):
            return default

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else default
        except:
            self.log_error(f"Error loading {path}")
            return default

    def save_json_list(self, path, data_list):
        """Save list safely."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data_list, f, indent=2, ensure_ascii=False)
        except:
            self.log_error(f"Error writing to {path}")

    def log_error(self, msg):
        """Simple file logger."""
        line = f"[{datetime.now().isoformat()}] {msg}\n"
        try:
            with open("log.txt", "a", encoding="utf-8") as f:
                f.write(line)
        except:
            pass


# -------------------------------------------------------------------
#                     MOVIE RECOMMENDER ENGINE
# -------------------------------------------------------------------

class MovieRecommender(BaseRecommender):
    """
    Demonstrates:
    - Inheritance
    - Normalization
    - Filtering with loops
    - *args & **kwargs
    - Weighted scoring
    - Recursion fallback
    - JSON history updates
    """

    def __init__(self, json_file, history_file="history.json", ratings_file="ratings.json"):
        super().__init__(json_file)
        self.history_file = history_file
        self.ratings_file = ratings_file

        self.movies = self.load_json_list(json_file, default=[])

    # ------------------ Helpers ------------------

    def _normalize(self, text):
        return text.strip().lower() if isinstance(text, str) else ""

    def _matches_type(self, movie, movie_type):
        mt = self._normalize(movie_type)

        rating = movie.get("rating", 7)
        pop = movie.get("popularity", 5)
        year = movie.get("year", 2010)
        duration = movie.get("duration_minutes", 120)

        if mt == "top rated":
            return rating >= 8.0
        if mt == "popular":
            return pop >= 8
        if mt == "underrated":
            return rating >= 7.0 and pop <= 6
        if mt == "new release":
            return year >= 2020
        if mt == "classic":
            return year <= 2005
        if mt.startswith("short movie"):
            return duration < 120

        return True

    def _score(self, movie):
        """Weighted score."""
        rating = movie.get("rating", 7)
        pop = movie.get("popularity", 5)
        bonus = random.uniform(0, 1)
        return round(math.fsum([0.6 * rating + 0.4 * pop, bonus]), 2)

    # ------------------ Filters ------------------

    def _filter_movies(self, *genres, **kw):
        industry = self._normalize(kw.get("industry", ""))
        movie_type = kw.get("movie_type", None)

        genres = [self._normalize(g) for g in genres]
        results = []

        for movie in self.movies:
            m_ind = self._normalize(movie.get("industry", ""))
            m_genres = [self._normalize(g) for g in movie.get("genres", [])]

            if industry and industry != m_ind:
                continue

            if genres and not all(g in m_genres for g in genres):
                continue

            if movie_type and not self._matches_type(movie, movie_type):
                continue

            m = movie.copy()
            m["score"] = self._score(movie)
            results.append(m)

        return results

    # ------------------ Recursion Fallback ------------------

    def _recursive_genre_search(self, movies, target, index=0):
        if index >= len(movies):
            return []

        rest = self._recursive_genre_search(movies, target, index + 1)

        movie = movies[index]
        genres = [self._normalize(g) for g in movie.get("genres", [])]

        if self._normalize(target) in genres:
            return [movie] + rest
        return rest

    # ------------------ Main Public API ------------------

    def recommend(self, industry, genre, movie_type, top_n=5):
        """Return FULL MOVIE OBJECTS (not just titles)."""

        industry_n = self._normalize(industry)
        genre_n = self._normalize(genre)

        # step 1 strict
        candidates = self._filter_movies(genre_n, industry=industry_n, movie_type=movie_type)

        # step 2 relax movie type
        if not candidates:
            candidates = self._filter_movies(genre_n, industry=industry_n)

        # step 3 recursion fallback
        if not candidates:
            rec = self._recursive_genre_search(self.movies, genre_n)
            candidates = [{**m, "score": self._score(m)} for m in rec]

        # step 4 fallback to all
        if not candidates:
            candidates = [{**m, "score": self._score(m)} for m in self.movies]

        # sort by score
        candidates.sort(key=lambda m: m["score"], reverse=True)

        pool = candidates[:10]
        selected = random.sample(pool, top_n) if len(pool) > top_n else pool

        # ⭐ return full movie objects
        self._log_history(industry_n, genre_n, movie_type, selected)
        return selected

    # ------------------ History ------------------

    def _log_history(self, industry, genre, movie_type, movies):
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "industry": industry,
            "genre": genre,
            "movie_type": movie_type,
            "recommended": movies
        }

        history = self.load_json_list(self.history_file, default=[])
        history.append(entry)
        self.save_json_list(self.history_file, history)

        # auto-increment popularity
        selected_titles = {m["title"] for m in movies}
        for movie in self.movies:
            if movie["title"] in selected_titles:
                movie["popularity"] = movie.get("popularity", 5) + 1

        self.save_json_list(self.data_file, self.movies)

    # ------------------ Ratings ------------------

    def rate_movie(self, title, stars):
        if stars not in [1, 2, 3, 4, 5]:
            return False

        entry = {
            "title": title,
            "stars": stars,
            "time": datetime.now().isoformat(timespec="seconds")
        }

        data = self.load_json_list(self.ratings_file, default=[])
        data.append(entry)
        self.save_json_list(self.ratings_file, data)
        return True

    # ------------------ Extras ------------------

    def count_movies_by_genre(self):
        counts = {}
        for movie in self.movies:
            for g in movie.get("genres", []):
                g = self._normalize(g)
                counts[g] = counts.get(g, 0) + 1
        return counts

    def find_romantic_titles(self):
        romantic = []
        pattern = re.compile(r"(love|heart|romance|valentine)", re.IGNORECASE)
        for movie in self.movies:
            if pattern.search(movie["title"]):
                romantic.append(movie["title"])
        return romantic

