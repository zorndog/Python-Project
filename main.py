import argparse
import pandas as pd
from movie_analysis import filter_years, find_movie_regions, decide_region, get_country_name, add_GDP_with_rank, \
    get_population, GDP_per_capita, add_votes_CDF, add_population_rank, add_GDPperCapita_rank, \
    add_movie_count_per_country_rank, cumulative_weighted_ratings, calculate_director_stats, rank_top_movies


def main():
    parser = argparse.ArgumentParser(description="Analyze movie data.")
    parser.add_argument('--title_akas', required=True, help="Path to title.akas.tsv")
    parser.add_argument('--title_crew', required=True, help="Path to title.crew.tsv")
    parser.add_argument('--title_ratings', required=True, help="Path to title.ratings.tsv")
    parser.add_argument('--title_basics', required=True, help="Path to title.basics.tsv")
    parser.add_argument('--GDP', required=True, help="Path to GDPs.csv")
    parser.add_argument('--start_year', type=int, required=True, help="Start year for filtering")
    parser.add_argument('--end_year', type=int, required=True, help="End year for filtering")
    args = parser.parse_args()

    # Load data
    title_akas = pd.read_csv(args.title_akas, sep='\t', low_memory=False)
    title_crew = pd.read_csv(args.title_crew, sep='\t')
    title_ratings = pd.read_csv(args.title_ratings, sep='\t')
    title_basics = pd.read_csv(args.title_basics, sep='\t', low_memory=False)

    # Filter years
    title_filtered, crew_filtered, ratings_filtered, basics_filtered = filter_years(
        title_basics, title_akas, title_crew, title_ratings, args.start_year, args.end_year)

    # Find movie regions
    titles_with_region = find_movie_regions(title_filtered, ratings_filtered)

    # Decide region
    titles_with_region = decide_region(titles_with_region)

    # Get country name
    titles_with_region['country_name'] = titles_with_region['region_list'].apply(get_country_name)
    ratings_filtered = ratings_filtered.rename(columns={'tconst': 'titleId'})
    crew_filtered = crew_filtered.rename(columns={'tconst': 'titleId'})
    # Add GDP with rank
    GDP = add_GDP_with_rank(args.GDP)
    Ratings_df = titles_with_region.merge(GDP, left_on='country_name', right_on='Country/Territory', how='left')
    Ratings_df.fillna({'GDP(US$million)':'Unknown'}, inplace=True)
    Ratings_df.fillna({'rank_gdp':30}, inplace=True)
    Ratings_df = pd.merge(Ratings_df, ratings_filtered, on='titleId')
    Ratings_df = pd.merge(Ratings_df, crew_filtered, on='titleId')
    Ratings_df = Ratings_df.drop(columns=['Country/Territory'])
    Ratings_df = add_votes_CDF(Ratings_df)
    Ratings_df['Population'] = Ratings_df['region_list'].apply(get_population)
    Ratings_df = GDP_per_capita(Ratings_df)
    Ratings_df = add_population_rank(Ratings_df)
    Ratings_df = add_GDPperCapita_rank(Ratings_df)
    Ratings_df = add_movie_count_per_country_rank(Ratings_df)

    print("Ranking krajów ze względu na najwyższą średnią 250 najlepiej ocenianych filmów: ")
    print(rank_top_movies(Ratings_df, 250).sort_values(by='AvgRating_Top_Movies', ascending=False))
    cumulative_ratings_df = cumulative_weighted_ratings(Ratings_df)
    print("Ranking krajów ze względu na najlepszy score ważony: ")
    print(cumulative_ratings_df.head(50))
    director_stats_df = calculate_director_stats(Ratings_df)
    print("Ranking reżyserów ze względu na średnią i wariancję ocenionych filmów: ")
    print(director_stats_df.sort_values(by='Rating', ascending=False).head(15))

if __name__ == "__main__":
    main()
