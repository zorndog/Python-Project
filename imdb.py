import pandas as pd
from collections import Counter
#!pip install pycountry
#!pip install pypopulation
import pycountry
import pypopulation
import numpy as np

def find_movie_regions(title,ratings): #adds region_list column containing regions original movie was produced in
    rated_titles = title[title['titleId'].isin(ratings['titleId'])]
    rated_titles_1 = rated_titles[rated_titles['isOriginalTitle'] == 1]
    rated_titles_0 = rated_titles[rated_titles['isOriginalTitle'] == 0]
    merged = pd.merge(rated_titles_1.loc[:, rated_titles_1.columns != 'region'],rated_titles_0[['title','titleId','region']],'inner',on = ['title','titleId'])
    merged_list = merged.groupby(['titleId','title'])['region'].apply(list).reset_index(name='region_list')
    return(merged_list)


def most_frequent_region(lst): #In case of many regions, set region th most common one, if cannot, put 'International'
    if not lst:
        return None  # Return None for empty lists

    count = Counter(lst)
    most_common = count.most_common()

    # Check if there's a single most frequent region
    if len(most_common) > 1 and most_common[0][1] == most_common[1][1]:
        return 'International'
    return most_common[0][0]


def decide_region(df):
    for i in range(df.shape[0]):
        region_list = df.at[i, 'region_list']  # Access the region_list

        if len(region_list) == 1:
            df.at[i, 'region_list'] = df.at[i, 'region_list'][0]
        else:
            df.at[i, 'region_list'] = most_frequent_region(region_list)
    return (df)

def get_country_name(region_code): #Returns country name based on code in pycountry package
    try:
        return pycountry.countries.get(alpha_2=region_code).name
    except (AttributeError, LookupError):
        return 'International'

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
    return (GDP)


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
    return (df)


def add_votes_CDF(df):
    sorted_votes = df.sort_values(by='numVotes')
    df['CDF_votes'] = sorted_votes['numVotes'].rank(method='average', pct=True)
    return (df)


def add_population_rank(df):
    # Replace 'Unknown' with NaN to handle them properly
    df['Population'] = df['Population'].replace('Unknown', pd.NA)

    # Convert the column to numeric, keeping NaNs
    df['Population'] = pd.to_numeric(df['Population'], errors='coerce')

    # Rank the population in descending order (largest population gets rank 1)
    df['Population_rank'] = df['Population'].rank(method='dense', ascending=False).astype('Int64')

    # Assign rank 100 to 'Unknown' populations
    df['Population_rank'] = df['Population_rank'].fillna(30).astype(int)

    # Replace NaNs back with 'Unknown'
    df['Population'] = df['Population'].fillna('Unknown')

    return df


def add_GDPperCapita_rank(df):
    # Replace 'Unknown' with NaN to handle them properly
    df['GDP/Population'] = df['GDP/Population'].replace('Unknown', pd.NA)

    # Convert the column to numeric, keeping NaNs
    df['GDP/Population'] = pd.to_numeric(df['GDP/Population'], errors='coerce')

    # Rank the GDP/Population in descending order (largest GDP/Population gets rank 1)
    df['GDP_per_Capita_rank'] = df['GDP/Population'].rank(method='dense', ascending=False).astype('Int64')

    # Assign rank 100 to 'Unknown' GDP/Population
    df['GDP_per_Capita_rank'] = df['GDP_per_Capita_rank'].fillna(30).astype(int)

    # Replace NaNs back with 'Unknown'
    df['GDP/Population'] = df['GDP/Population'].fillna('Unknown')

    return df


def add_movie_count_per_country_rank(df):
    sorted_votes = df.sort_values(by='numVotes')
    country_movie_count = sorted_votes['country_name'].value_counts().reset_index()
    country_movie_count.columns = ['country_name', 'movie_count']
    country_movie_count['rank_movie_count'] = country_movie_count['movie_count'].rank(ascending=False,
                                                                                      method='min').astype(int)
    df = df.merge(country_movie_count, left_on='country_name', right_on='country_name', how='left')
    return (df)


def rank_top_movies(df, X):
    # Group by 'Country' and sort each group by 'averageRating' descending
    ranked_df = df.sort_values(by='averageRating', ascending=False).groupby('country_name').head(X)

    # Calculate average rating for top X movies for each country
    avg_ratings = ranked_df.groupby('country_name')['averageRating'].mean()

    # Create DataFrame with results
    result_df = pd.DataFrame({'country_name': avg_ratings.index, f'AvgRating_Top_Movies': avg_ratings.values})

    return result_df


def weighted_ranking(df):
    # Compute the weighted rating using the correct column access method
    df['Weighted_rating'] = (
            df['averageRating'] ** 2 *
            (10 + df['rank_gdp']) ** (1 / 2) *
            df['rank_movie_count'] ** (1 / 2) *
            df['CDF_votes'] *
            df['Population_rank'] ** (1 / 2) *
            df['GDP_per_Capita_rank'] ** (1 / 2)
    )
    return df


def cumulative_weighted_ratings(df):
    # First, calculate the weighted ratings
    df = weighted_ranking(df)

    # Group by country and sum the weighted ratings
    cumulative_df = df.groupby('country_name')['Weighted_rating'].sum().reset_index()

    # Sort the results by cumulative weighted rating in descending order
    cumulative_df = cumulative_df.sort_values(by='Weighted_rating', ascending=False)

    return cumulative_df


def calculate_director_stats(df):
    # Drop rows where directors is '\N'
    df = df[df['directors'] != '\\N']
    # Group by the directors column and filter to include only those with at least 4 movies
    director_counts = df['directors'].value_counts()

    directors_with_at_least_4_movies = director_counts[director_counts >= 20].index
    df = df[df['directors'].isin(directors_with_at_least_4_movies)]

    # Get the top 10 movies for each director based on averageRating
    df['rank'] = df.groupby('directors')['averageRating'].rank("dense", ascending=False)
    top_movies = df[df['rank'] <= 20]

    # Initialize an empty list to collect director statistics
    director_stats_list = []

    # Iterate over each director and calculate mean and variance
    for director, group in top_movies.groupby('directors'):
        mean_rating = np.mean(group['averageRating'])
        var_rating = np.var(group['averageRating'], ddof=0)  # Use ddof=0 for population variance
        mean_rating *= np.mean(group['CDF_votes'])
        var_rating *= np.mean(group['CDF_votes'])
        # Append director statistics as a dictionary to the list
        director_stats_list.append({
            'directors': director,
            'mean_rating': mean_rating,
            'rating_variance': var_rating
        })

    # Create a DataFrame from the list of dictionaries
    director_stats_df = pd.DataFrame(director_stats_list)

    # Replace NaN variance with 6
    director_stats_df['rating_variance'].fillna(6, inplace=True)

    # Calculate the final Rating for each director
    director_stats_df['Rating'] = director_stats_df['mean_rating'] - director_stats_df['rating_variance'] ** (1 / 2)

    return director_stats_df