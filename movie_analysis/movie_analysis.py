import pandas as pd
from collections import Counter
import pycountry
import pypopulation
import numpy as np

#Filter the data so it contains only the data from the specified time frame
def filter_years(basics_unfiltered, title_unfiltered, crew_unfiltered, ratings_unfiltered, start_year, end_year):
    basics_unfiltered['startYear'] = pd.to_numeric(basics_unfiltered['startYear'], errors='coerce')
    basics_filtered = basics_unfiltered[(basics_unfiltered['startYear'].notna()) &
                             (basics_unfiltered['startYear'] >= start_year) &
                             (basics_unfiltered['startYear'] <= end_year)]
    valid_title_ids = basics_filtered['tconst'].unique()
    title_filtered = title_unfiltered[title_unfiltered['titleId'].isin(valid_title_ids)].copy()
    crew_filtered = crew_unfiltered[crew_unfiltered['tconst'].isin(valid_title_ids)].copy()
    ratings_filtered = ratings_unfiltered[ratings_unfiltered['tconst'].isin(valid_title_ids)].copy()
    return title_filtered, crew_filtered, ratings_filtered, basics_filtered

#Find what country movie is from (by original title, may contain more than one region)
def find_movie_regions(title, ratings):
    ratings = ratings.rename(columns={'tconst': 'titleId'})
    rated_titles = title[title['titleId'].isin(ratings['titleId'])]
    rated_titles_1 = rated_titles[rated_titles['isOriginalTitle'] == 1]
    rated_titles_0 = rated_titles[rated_titles['isOriginalTitle'] == 0]
    merged = pd.merge(
        rated_titles_1.loc[:, rated_titles_1.columns != 'region'],
        rated_titles_0[['title', 'titleId', 'region']],
        'inner',
        on=['title', 'titleId']
    )
    merged_list = merged.groupby(['titleId', 'title'])['region'].apply(list).reset_index(name='region_list')
    return merged_list

#Specify the country movie was made in. If more than one region is included, take the most frequent.
# In case a tie, input 'International'.
def decide_region(df):
    for i in range(df.shape[0]):
        region_list = df.at[i, 'region_list']
        if len(region_list) == 1:
            df.at[i, 'region_list'] = df.at[i, 'region_list'][0]
        else:
            df.at[i, 'region_list'] = most_frequent_region(region_list)
    return df

def most_frequent_region(lst):
    if not lst:
        return None
    count = Counter(lst)
    most_common = count.most_common()
    if len(most_common) > 1 and most_common[0][1] == most_common[1][1]:
        return 'International'
    return most_common[0][0]

def get_country_name(region_code):
    try:
        return pycountry.countries.get(alpha_2=region_code).name
    except (AttributeError, LookupError):
        return 'International'

#Rank countries by GDP
def add_GDP_with_rank(GDPs_file):
    try:
        GDP = pd.read_csv(GDPs_file, encoding='utf-8')
    except UnicodeDecodeError:
        try:
            GDP = pd.read_csv(GDPs_file, encoding='ISO-8859-1')
        except UnicodeDecodeError:
            GDP = pd.read_csv(GDPs_file, encoding='latin1', errors='replace')
    GDP['GDP(US$million)'] = GDP['GDP(US$million)'].str.replace(',', '').astype(float)
    GDP['rank_gdp'] = GDP.index + 1
    GDP = GDP.drop(columns=['Rank'])
    return GDP

def get_population(region_code):
    try:
        population = pypopulation.get_population(region_code)
        return population if population is not None else 'Unknown'
    except Exception as e:
        return 'Unknown'

def GDP_per_capita(df):
    df['GDP/Population'] = df.apply(
        lambda row: row['GDP(US$million)'] / row['Population']
        if row['GDP(US$million)'] != 'Unknown' and row['Population'] != 'Unknown'
        else 'Unknown', axis=1)
    return df

# Adds a metric based on how many people voted for the movie (more votes - higher rating)
def add_votes_CDF(df):
    sorted_votes = df.sort_values(by='numVotes')
    df['CDF_votes'] = sorted_votes['numVotes'].rank(method='average', pct=True)
    return df

#Add rank based on population of producing country. Rank 1 - most populated
def add_population_rank(df):
    df['Population'] = df['Population'].replace('Unknown', pd.NA)
    df['Population'] = pd.to_numeric(df['Population'], errors='coerce')
    df['Population_rank'] = df['Population'].rank(method='dense', ascending=False).astype('Int64')
    df['Population_rank'] = df['Population_rank'].fillna(30).astype(int)
    df['Population'] = df['Population'].fillna('Unknown')
    return df

#Add rank based on GDPperCapita. Rank 1 - highest GDPperCapita
def add_GDPperCapita_rank(df):
    df['GDP/Population'] = df['GDP/Population'].replace('Unknown', pd.NA)
    df['GDP/Population'] = pd.to_numeric(df['GDP/Population'], errors='coerce')
    df['GDP_per_Capita_rank'] = df['GDP/Population'].rank(method='dense', ascending=False).astype('Int64')
    df['GDP_per_Capita_rank'] = df['GDP_per_Capita_rank'].fillna(30).astype(int)
    df['GDP/Population'] = df['GDP/Population'].fillna('Unknown')
    return df

#adds a ranking of countries based on the number of movies they have.
def add_movie_count_per_country_rank(df):
    sorted_votes = df.sort_values(by='numVotes')
    country_movie_count = sorted_votes['country_name'].value_counts().reset_index()
    country_movie_count.columns = ['country_name', 'movie_count']
    country_movie_count['rank_movie_count'] = country_movie_count['movie_count'].rank(ascending=False, method='min').astype(int)
    df = df.merge(country_movie_count, left_on='country_name', right_on='country_name', how='left')
    return df

# Ranks top X movies of each country based only on the average votes
def rank_top_movies(df, X):
    ranked_df = df.sort_values(by='averageRating', ascending=False).groupby('country_name').head(X)
    avg_ratings = ranked_df.groupby('country_name')['averageRating'].mean(
    result_df = pd.DataFrame({'country_name': avg_ratings.index, f'AvgRating_Top_Movies': avg_ratings.values})
    return result_df

#Definition of ranking for a given movie
def weighted_ranking(df):
    df['Weighted_rating'] = (
        df['averageRating']**2 *
        (10 + df['rank_gdp'])**(1/2) *
        df['rank_movie_count']**(1/2) *
        df['CDF_votes'] *
        df['Population_rank']**(1/2) *
        df['GDP_per_Capita_rank']**(1/2)
    )
    return df

def cumulative_weighted_ratings(df):
    df = weighted_ranking(df)
    cumulative_df = df.groupby('country_name')['Weighted_rating'].sum().reset_index() #by country
    cumulative_df = cumulative_df.sort_values(by='Weighted_rating', ascending=False) #sort so the highest rating is first
    return cumulative_df

def calculate_director_stats(df): #Rating of directors based on the mean and variance of ratings of top movies(at least 20)
    df = df[df['directors'] != '\\N']
    director_counts = df['directors'].value_counts()
    directors_with_at_least_20_movies = director_counts[director_counts >= 20].index
    df = df[df['directors'].isin(directors_with_at_least_20_movies)]
    df['rank'] = df.groupby('directors')['averageRating'].rank("dense", ascending=False)
    top_movies = df[df['rank'] <= 20]
    director_stats_list = []
    for director, group in top_movies.groupby('directors'):
        mean_rating = np.mean(group['averageRating'])
        var_rating = np.var(group['averageRating'], ddof=0)
        mean_rating *= np.mean(group['CDF_votes'])
        var_rating *= np.mean(group['CDF_votes'])
        director_stats_list.append({
            'directors': director,
            'mean_rating': mean_rating,
            'rating_variance': var_rating
        })
    director_stats_df = pd.DataFrame(director_stats_list)
    director_stats_df.fillna({'rating_variance':6}, inplace=True)
    director_stats_df['Rating'] = director_stats_df['mean_rating'] - director_stats_df['rating_variance']**(1/2)
    return director_stats_df


