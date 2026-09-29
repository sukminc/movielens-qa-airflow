import streamlit as st

from main import (
    BASE_DIR,
    load_genres,
    load_movie_genres,
    load_movie_titles,
    load_rating_stats,
    rank_movies,
    validate_movie_ids,
)

@st.cache_data
def load_app_data():
    """Load and prepare the movie data for the interface."""
    data_dir = BASE_DIR / "data" / "ml-100k"

    movie_stats = load_rating_stats(data_dir / "u.data")
    ranked_movies = rank_movies(movie_stats)
    movie_titles = load_movie_titles(data_dir / "u.item")
    validate_movie_ids(movie_stats, movie_titles)
    genres = load_genres(data_dir / "u.genre")
    movie_genres = load_movie_genres(data_dir / "u.item", genres)

    top_movie_ids = [movie_id for movie_id, stats in ranked_movies[:10]]

    return movie_stats, movie_titles, movie_genres, top_movie_ids

st.title("MovieLens Explorer")
st.write("Choose a movie to explore its ratings and genres.")

try:
    movie_stats, movie_titles, movie_genres, top_movie_ids = load_app_data()
except FileNotFoundError:
    st.error(
        "MovieLens dataset files are missing. Download and extract "
        "MovieLens 100K into data/ml-100k, then rerun the app."
    )
    st.stop()
except ValueError as error:
    st.error(f"Could not load the dataset: {error}")
    st.stop()

selected_movie_id = st.selectbox(
    "Choose a movie",
    options=top_movie_ids,
    format_func=lambda movie_id: movie_titles[movie_id],
)

selected_stats = movie_stats[selected_movie_id]

count_column, average_column = st.columns(2)

count_column.metric(
    "Number of ratings",
    selected_stats["count"],
)

average_column.metric(
    "Average score",
    f"{selected_stats['average']:.2f} / 5",
)

st.subheader("Genres")
st.write(", ".join(movie_genres[selected_movie_id]))