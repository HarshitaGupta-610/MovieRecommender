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
    - Exception handling
    - Logging
    - Basic OOP
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
        except (json.JSONDecodeError, OSError) as e:
            self.log_error(f"Error loading JSON from {path}: {e}")
            return default

    def save_json_list(self, path, data_list):
        """Save list as JSON safely."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data_list, f, indent=2, ensure_ascii=False)
        except OSError as e:
            self.log_error(f"Error writing to {path}: {e}")

    def log_error(self, message: str):
        """Append errors into log.txt."""
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[ERROR {stamp}] {message}\n"
        try:
            with open("log.txt", "a", encoding="utf-8") as f:
                f.write(line)
        except:
            pass


# --------------------------------------------------------------
#                    Movie Recommender
# --------------------------------------------------------------

class MovieRecommender(BaseRecommender):
    """
    Demonstrates:
    - Inheritance
    - Lists, dicts, sets, tuples
    - Type checking
    - Loop filtering
    - Sorting
    - Random sampling
    - Recursion
    - Regex
    - File read/write history
    - Scoring logic using math
    """

    def __init__(self, json_file, history_file="history.json", ratings_file="ratings.json"):
        super().__init__(json_file)
        self.history_file = history_file
        self.ratings_file = ratings_file

        # Load all movies
        self.movies = self.load_json_list(self.data_file, default=[])
        if not isinstance(self.movies, list):
            self.movies = []

    # ------------------ Utility Helpers ------------------

    @staticmethod
    def _normalize_string(text: str) -> str:
        """Basic text normalization."""
        if not isinstance(text, str):
            return ""
        return text.strip().lower()

    def _matches_type(self, movie: dict, movie_type: str) -> bool:
        """Check if a movie matches the selected type."""
        mt = self._normalize_string(movie_type)

        rating = movie.get("rating", 7.0)
        popularity = movie.get("popularity", 5)
        year = movie.get("year", 2010)
        duration = movie.get("duration_minutes", 120)

        if mt == "top rated":
            return rating >= 8.0
        elif mt == "popular":
            return popularity >= 8
        elif mt == "underrated":
            return rating >= 7.0 and popularity <= 6
        elif mt == "new release":
            return year >= 2020
        elif mt == "classic":
            return year <= 2005
        elif mt.startswith("short movie"):
            return duration < 120

        return True

    def _score_movie(self, movie: dict) -> float:
        """Weighted scoring."""
        rating = movie.get("rating", 7.0)
        popularity = movie.get("popularity", 5)

        base = 0.6 * rating + 0.4 * popularity
        random_bonus = random.uniform(0, 1)

        score = math.fsum([base, random_bonus])
        return round(score, 2)

    # ------------------ Filtering Logic ------------------

    def _filter_movies(self, *genres, **constraints):
        """
        Filter movies using:
        - variable args (*genres)
        - keyword args (**constraints)
        """
        industry = self._normalize_string(constraints.get("industry", ""))
        movie_type = constraints.get("movie_type", None)
        normalized_genres = [self._normalize_string(g) for g in genres]

        results = []

        for movie in self.movies:
            m_ind = self._normalize_string(movie.get("industry", ""))
            m_genres = [self._normalize_string(g) for g in movie.get("genres", [])]

            if industry and industry != m_ind:
                continue

            if normalized_genres:
                match_all = all(g in m_genres for g in normalized_genres)
                if not match_all:
                    continue

            if movie_type and not self._matches_type(movie, movie_type):
                continue

            movie_copy = movie.copy()
            movie_copy["score"] = self._score_movie(movie)
            results.append(movie_copy)

        return results

    # ---------------------- Recursion ----------------------

    def _recursive_genre_search(self, movies, target_genre, index=0):
        """If strict filtering fails, fallback recursive genre matching."""
        if index >= len(movies):
            return []

        rest = self._recursive_genre_search(movies, target_genre, index + 1)
        movie = movies[index]

        genres = [self._normalize_string(g) for g in movie.get("genres", [])]
        if self._normalize_string(target_genre) in genres:
            return [movie] + rest

        return rest

    # ---------------------- Main Recommend ----------------------

    def recommend(self, industry: str, genre: str, movie_type: str, top_n: int = 5):
        """Main recommendation flow."""

        norm_ind = self._normalize_string(industry)
        norm_gen = self._normalize_string(genre)

        # Step 1: strict
        candidates = self._filter_movies(norm_gen, industry=norm_ind, movie_type=movie_type)

        # Step 2: relax movie_type
        if not candidates:
            candidates = self._filter_movies(norm_gen, industry=norm_ind)

        # Step 3: recursion fallback
        if not candidates:
            rec = self._recursive_genre_search(self.movies, norm_gen)
            candidates = [
                {**m, "score": self._score_movie(m)} for m in rec
            ]

        # Step 4: fallback to everything
        if not candidates:
            candidates = [
                {**m, "score": self._score_movie(m)} for m in self.movies
            ]

        # Sort by score
        candidates.sort(key=lambda m: m.get("score", 0), reverse=True)

        # Pick top results randomly from top 10
        pool = candidates[:10]
        selected = random.sample(pool, top_n) if len(pool) > top_n else pool

        # Instead of returning only titles → return full movie objects
        self._log_history_full(norm_ind, norm_gen, movie_type, selected)

        return selected

    # ------------------------- History -------------------------

    def _log_history_full(self, industry, genre, movie_type, selected_movies):
        """Save full movie objects into history.json."""
        timestamp = datetime.now().isoformat(timespec="seconds")

        entry = {
            "timestamp": timestamp,
            "industry": industry,
            "genre": genre,
            "movie_type": movie_type,
            "recommended": selected_movies   # full movie dicts
        }

        history = self.load_json_list(self.history_file, default=[])
        history.append(entry)
        self.save_json_list(self.history_file, history)

        # Popularity update
        titles_selected = {m["title"] for m in selected_movies}
        for movie in self.movies:
            if movie.get("title") in titles_selected:
                movie["popularity"] = movie.get("popularity", 5) + 1

        self.save_json_list(self.data_file, self.movies)

    # ----------------------- Ratings -----------------------

    def rate_movie(self, title: str, stars: int):
        """Store user rating."""
        if stars < 1 or stars > 5:
            return False

        entry = {
            "title": title.strip(),
            "stars": stars,
            "time": datetime.now().isoformat(timespec="seconds")
        }

        ratings = self.load_json_list(self.ratings_file, default=[])
        ratings.append(entry)
        self.save_json_list(self.ratings_file, ratings)

        return True

    # ------------------- Extra Features -------------------

    def count_movies_by_genre(self):
        """Count how many movies exist per genre."""
        counts = {}
        for movie in self.movies:
            for g in movie.get("genres", []):
                g = self._normalize_string(g)
                counts[g] = counts.get(g, 0) + 1
        return counts

    def find_romantic_titles(self):
        """Regex-based romantic movie finder."""
        romantic = []
        pattern = re.compile(r"(love|heart|romance|diary|valentine)", re.IGNORECASE)

        for movie in self.movies:
            if pattern.search(movie.get("title", "")):
                romantic.append(movie["title"])

        return romantic
