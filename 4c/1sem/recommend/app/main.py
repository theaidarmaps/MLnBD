import pandas as pd
import pickle
from fastapi import FastAPI, HTTPException
from pandas import DataFrame
from pydantic import BaseModel
from ast import literal_eval
from warnings import filterwarnings
import numpy as np
from starlette.status import *

filterwarnings('ignore')

app = FastAPI()

with open('../tfidf_vectorizer.pkl', 'rb') as f:
    tf = pickle.load(f)
with open('../nn_model.pkl', 'rb') as f:
    nn_model = pickle.load(f)
with open('../nn_model_cf.pkl', 'rb') as f:
    nn_model_cf = pickle.load(f)

with open('../user_ids.pkl', 'rb') as f:
    valid_user_ids = pickle.load(f)

movies = pd.read_csv('../movies_metadata.csv', low_memory=False)
ratings = pd.read_csv('../ratings_small.csv', low_memory=False)
keywords = pd.read_csv('../keywords.csv', low_memory=False)

movies['id'] = pd.to_numeric(movies['id'], errors='coerce')
movies = movies.dropna(subset=['id'])
movies['id'] = movies['id'].astype('int')

movies = movies[['id', 'original_title', 'production_companies', 'release_date',
                 'genres', 'overview', 'vote_average', 'vote_count']].copy()


def convert_to_list(df, column: str):
    df[column] = df[column].fillna('[]').apply(literal_eval).apply(
        lambda x: [i['name'] for i in x] if isinstance(x, list) else [])


def convert_list_to_str(df, column: str):
    df[column] = df[column].apply(lambda x: ','.join(x) if isinstance(x, list) else str(x))


def save(df: DataFrame, path: str):
    df.to_csv(path, index=False)


convert_to_list(movies, 'genres')
convert_to_list(movies, 'production_companies')
convert_to_list(keywords, 'keywords')

df_ = movies.merge(keywords[['id', 'keywords']], on='id', how='left')


def weighted_rating(x):
    v = x['vote_count']
    R = x['vote_average']
    m = df_['vote_count'].quantile(0.8)
    C = df_['vote_average'].mean()
    return (v / (v + m) * R) + (m / (m + v) * C)


df_['weighted_rating'] = movies.apply(weighted_rating, axis=1)

s = df_.apply(lambda x: pd.Series(x['genres']), axis=1).stack().reset_index(level=1, drop=True)
s.name = 'genre'
gen_md = df_.drop('genres', axis=1).join(s)


def recommend_by_genre(genre: str):
    df1 = gen_md[gen_md['genre'] == genre]

    vote_counts = df1[df1['vote_count'].notnull()]['vote_count'].astype('int')
    vote_averages = df1[df1['vote_average'].notnull()]['vote_average'].astype('int')
    C = vote_averages.mean()
    m = vote_counts.quantile(0.85)

    qualified = df1[(df1['vote_count'] >= m) & (df1['vote_count'].notnull()) & (df1['vote_average'].notnull())][
        ['original_title', 'vote_count', 'vote_average']]
    qualified['vote_count'] = qualified['vote_count'].astype('int')
    qualified['vote_average'] = qualified['vote_average'].astype('int')

    qualified['wr'] = qualified.apply(
        lambda x: (x['vote_count'] / (x['vote_count'] + m) * x['vote_average']) + (m / (m + x['vote_count']) * C),
        axis=1)
    qualified = qualified.sort_values('wr', ascending=False).head(250)

    return qualified


titles = df_['original_title']
title_indices = pd.Series(df_.index, index=df_['original_title'])


def recommend_by_name(name: str):
    df1 = df_.copy()
    convert_list_to_str(df1, 'genres')
    convert_list_to_str(df1, 'keywords')
    df1['total'] = df1['genres'] + ' ' + df1['keywords'] + ' ' + df1['overview']
    df1['total'] = df1['total'].fillna('')

    idx = title_indices[name]
    movie_total = df1.loc[idx, 'total']
    movie_vector = tf.transform([movie_total])
    distances, indices = nn_model.kneighbors(movie_vector, n_neighbors=11)
    movie_indices = indices[0][1:]
    return df1['original_title'].iloc[movie_indices].tolist()


def recommend_by_collaborative_filtering(user_id: str, n: int = 10):
    ratings_matrix = ratings.pivot(index='userId', columns='movieId', values='rating').fillna(0)
    movies_matrix = ratings_matrix.T

    user_ratings = ratings_matrix.loc[int(user_id)]
    high_rated_movies = user_ratings[user_ratings >= 4].index

    scores = {}

    for movie_id in high_rated_movies:
        if movie_id in movies_matrix.index:
            movie_idx = movies_matrix.index.get_loc(movie_id)
            distances, indices = nn_model_cf.kneighbors(movies_matrix.iloc[movie_idx].values.reshape(1, -1),
                                                        n_neighbors=21)
            sim_movies = [movies_matrix.index[i] for i in indices.flatten()[1:]]
            sim_distances = distances.flatten()[1:]

            for sim_movie, dist in zip(sim_movies, sim_distances):
                if sim_movie not in user_ratings.index or user_ratings[sim_movie] == 0:
                    similarity = 1 - dist
                    if sim_movie not in scores:
                        scores[sim_movie] = 0
                    scores[sim_movie] += similarity

    top_movies = sorted(scores, key=scores.get, reverse=True)[:n]

    top_titles = df_[df_['id'].isin(top_movies)]['original_title'].head(10).tolist()

    return top_titles


def personal_recommend(user_id: str, n: int = 10):
    if not all(isinstance(x, list) for x in df_['genres'].head(100)):
        print("Исправляем формат genres...")
        df_['genres'] = df_['genres'].apply(lambda x: x if isinstance(x, list) else [])
        gen_md['genre'] = gen_md['genre'].fillna('')

    user_ratings = ratings[ratings['userId'] == user_id]
    high_rated_movies = user_ratings[user_ratings['rating'] >= 4]['movieId'].tolist()

    if user_id not in valid_user_ids:
        if not high_rated_movies:
            # Если нет оценок, возвращаем топ-10 по взвешенному рейтингу
            return df_.sort_values('weighted_rating', ascending=False)['original_title'].head(n).tolist()

        # Контентная фильтрация на основе высоко оцененных фильмов
        recommendations = set()
        for movie_id in high_rated_movies:
            if movie_id in df_['id'].values:
                movie_title = df_[df_['id'] == movie_id]['original_title'].iloc[0]
                # Используем функцию recommend_by_name для контентной фильтрации
                recs = recommend_by_name(movie_title)
                recommendations.update(recs[:n // len(high_rated_movies) + 1])

        return list(recommendations)[:n]

    if not high_rated_movies:
        return df_.sort_values('weighted_rating', ascending=False)['original_title'].head(n).tolist()

    # Собираем жанры из высоко оцененных фильмов
    high_rated_movie_ids = df_[df_['id'].isin(high_rated_movies)]['id']
    user_genres = gen_md[gen_md['id'].isin(high_rated_movie_ids)]['genre'].unique()

    filtered_ratings = ratings[ratings['userId'].isin(valid_user_ids)]
    ratings_matrix = filtered_ratings.pivot(index='userId', columns='movieId', values='rating').fillna(0)
    movies_matrix = ratings_matrix.T
    scores = {}

    for movie_id in high_rated_movies:
        if movie_id in movies_matrix.index:
            movie_idx = movies_matrix.index.get_loc(movie_id)
            distances, indices = nn_model_cf.kneighbors(movies_matrix.iloc[movie_idx].values.reshape(1, -1),
                                                        n_neighbors=21)
            sim_movies = [movies_matrix.index[i] for i in indices.flatten()[1:]]
            sim_distances = distances.flatten()[1:]

            for sim_movie, dist in zip(sim_movies, sim_distances):
                if sim_movie not in user_ratings['movieId'].values:
                    similarity = 1 - dist
                    if sim_movie not in scores:
                        scores[sim_movie] = 0
                    scores[sim_movie] += similarity

    # Фильтруем кандидатов по жанрам
    candidate_movies = df_[df_['id'].isin(scores.keys())].copy()
    candidate_movies['score'] = candidate_movies['id'].map(scores)
    candidate_movies = candidate_movies[
        candidate_movies['genres'].apply(lambda x: any(genre in x for genre in user_genres))]

    # Вычисляем комбинированный рейтинг
    candidate_movies['combined_score'] = candidate_movies['weighted_rating'] * 0.7 + candidate_movies['score'] * 0.3
    top_movies = candidate_movies.sort_values('combined_score', ascending=False)
    return top_movies['original_title'].head(n).tolist()


class TitleRequest(BaseModel):
    title: str


class GenreRequest(BaseModel):
    genre: str


@app.get('/get_movie_id')
def get_movie_id(movie: str):
    return int(movies[movies['original_title'] == movie]['id'].iloc[0].astype(int))


@app.get('/all_movies')
def all_movies():
    movie_list = movies[['original_title', 'release_date']].replace(np.nan, None).to_dict('records')
    return {'movies': movie_list}


@app.get('/all_movie_titles')
def all_movie_titles():
    return movies['original_title'].tolist()


@app.get('/top10')
async def top10():
    return df_.sort_values('weighted_rating', ascending=False)['original_title'].head(10).tolist()


@app.get('/recommend/genre')
async def genre_recommendation(genre: str):
    return recommend_by_genre(genre)['original_title'].head(10).tolist()


@app.get('/recommend/title')
async def title_recommendation(title: str):
    return recommend_by_name(title)


@app.get('/recommend/collaborative')
async def collaborative_recommendation(user_id: str):
    return recommend_by_collaborative_filtering(user_id)

@app.get('/recommend/personal')
async def personal_recommendation(user_id: str):
    # if user_id not in ratings['userId']:
    #     raise HTTPException(status_code=404, detail='Пользователь не найден')
    return personal_recommend(user_id)


@app.post('/set_rating')
async def set_rating(user_id: str, movie_id: int, rating: float):
    global ratings
    if movie_id not in movies['id']:
        raise HTTPException(status_code=404, detail='Фильм не найден')

    existing_rating = ratings[(ratings['userId'] == user_id) & (ratings['movieId'] == movie_id)]

    if not existing_rating.empty:
        ratings.loc[(ratings['userId'] == user_id) & (ratings['movieId'] == movie_id), 'rating'] = rating
        ratings.loc[(ratings['userId'] == user_id) & (ratings['movieId'] == movie_id), 'timestamp'] = 0
    else:
        new_row = {'userId': user_id, 'movieId': movie_id, 'rating': rating, 'timestamp': 0}
        ratings.loc[len(ratings)] = new_row

    save(ratings, '../ratings_small.csv')

    return HTTP_200_OK


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
#uvicorn main:app --reload
