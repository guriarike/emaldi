# -*- coding: utf-8 -*-
"""EMALDI ULTIMO----ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1eAQuPSDc2_Kwo8342MB7p83aOheU9pDD

# BEFORE STARTING
"""

!pip install pyspark
!pip install -U -q PyDrive
!apt install openjdk-8-jdk-headless -qq

import os
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-8-openjdk-amd64"

import pyspark
from pyspark.sql import SparkSession
from pyspark import SparkContext, SparkConf
from pyspark.sql.functions import col, sum

#Aqui nose como pero habria que conectarlo con lo de Asier

conf = SparkConf().set("spark.ui.port", "4050")
sc = SparkContext(conf=conf)
spark = SparkSession.builder.getOrCreate()

#sc.stop()

"""# NOW WE GET THE DATASETS AND THEN WE MERGE THEM"""

# Load the datasets into Spark DataFrames
credits_df = spark.read.csv("tmdb_5000_credits.csv", quote = '"',sep = "," ,escape = '"', header=True, inferSchema=True)
credits_df = credits_df.drop('title')
credits_df.printSchema()
movies_df = spark.read.csv("tmdb_5000_movies.csv", quote = '"',sep = "," ,escape = '"', header=True, inferSchema=True, multiLine=True)
movies_df.printSchema()

df = movies_df.join(credits_df, credits_df["movie_id"] == movies_df["id"], "inner")
df = df.drop('id')

df = df.withColumn("profit", col("revenue") - col("budget"))
df.printSchema()
df.show()
df = df.na.drop(subset=['budget'])

df.count()

credits_df.show()
movies_df.show()
df.show()

"""# NOW WE START WITH THE PREPROCESS OF THE MERGED DATASET"""

df = df.withColumn("profit", col("revenue") - col("budget"))
df.printSchema()
df.show()
df = df.na.drop(subset=['budget'])

df.count()

#WE CREATE A TABLE WITH GENRE_ID AND GENRE_NAME

import json
import pandas as pd

genres = []
genre_table = pd.DataFrame()

for movie in df.collect():
  genres = movie['genres']
  genre_data = json.loads(genres)
  new_genre_table = pd.DataFrame(genre_data)
  genre_table = pd.concat([genre_table, new_genre_table]).drop_duplicates()

#WE CREATE A NEW COLUMN WITH A LIST WHICH ONLY CONTAINS GENRE_IDS

from pyspark.sql.functions import udf

def transform_column(column):
    column_data = json.loads(column)
    column_ids = [lista["name"] for lista in column_data]
    return column_ids

transform_column_udf = udf(transform_column)
df = df.withColumn('genres', transform_column_udf('genres'))

df.show()

#WE CREATE A TABLE WITH KEYWORDS_ID AND KEYWORDS_NAME

keywords = []
keywords_table = pd.DataFrame()

for movie in df.collect():
  keywords = movie['keywords']
  keywords_data = json.loads(keywords)
  new_keywords_table = pd.DataFrame(keywords_data)
  keywords_table = pd.concat([keywords_table, new_keywords_table]).drop_duplicates()

#WE CREATE A NEW COLUMN WITH A LIST WHICH ONLY CONTAINS KEYWORDS_IDS

df = df.withColumn('keywords', transform_column_udf('keywords'))

df.show()

#WE CREATE A TABLE WITH PRODUCTION_COMPANIES_ID AND PRODUCTION_COMPANIES_NAME

companies = []
companies_table = pd.DataFrame()

for movie in movies_df.collect():
  companies = movie['production_companies']
  companies_data = json.loads(companies)
  new_companies_table = pd.DataFrame(companies_data)
  companies_table = pd.concat([companies_table, new_companies_table]).drop_duplicates()

#WE CREATE A NEW COLUMN WITH A LIST WHICH ONLY CONTAINS PRODUCTION_COMPANIES_IDS

df = df.withColumn('production_companies', transform_column_udf('production_companies'))

df = df.na.drop(subset=['production_companies'])
df = df.filter(col('production_companies') != '[]')

df.show()

df.count()

#WE CREATE A TABLE WITH PRODUCTION_COUNTRIES_ID AND PRODUCTION_COUNTRIES_NAME

countries = []
countries_table = pd.DataFrame()

for movie in df.collect():
  countries = movie['production_countries']
  countries_data = json.loads(countries)
  new_countries_table = pd.DataFrame(countries_data)
  countries_table = pd.concat([countries_table, new_countries_table]).drop_duplicates()

#WE CREATE A NEW COLUMN WITH A LIST WHICH ONLY CONTAINS PRODUCTION_COUNTRIES_IDS

def transform_column_country(column):
    column_data = json.loads(column)
    column_ids = [lista["iso_3166_1"] for lista in column_data]
    return column_ids

transform_column_country_udf = udf(transform_column_country)
df = df.withColumn('production_countries', transform_column_country_udf('production_countries'))

df.show()

#WE CREATE A TABLE WITH SPOKEN_LANGUAGES_ID AND SPOKEN_LANGUAGES_NAME

languages = []
languages_table = pd.DataFrame()

for movie in df.collect():
  languages = movie['spoken_languages']
  languages_data = json.loads(languages)
  new_languages_table = pd.DataFrame(languages_data)
  languages_table = pd.concat([languages_table, new_languages_table]).drop_duplicates()

#WE CREATE A NEW COLUMN WITH A LIST WHICH ONLY CONTAINS SPOKEN_LANGUAGES_IDS

def transform_column_languages(column):
    column_data = json.loads(column)
    column_ids = [lista["iso_639_1"] for lista in column_data]
    return column_ids

transform_column_languages_udf = udf(transform_column_languages)
df = df.withColumn('spoken_languages', transform_column_languages_udf('spoken_languages'))

df = df.na.drop(subset=['spoken_languages'])
df = df.filter(col('spoken_languages') != '[]')

df.show()

#WE CREATE A NEW COLUMN WITH A LIST WHICH ONLY CONTAINS ACTORS' IDS

df = df.withColumn('cast', transform_column_udf('cast'))

df = df.na.drop(subset=['cast'])
df = df.filter(col('cast') != '[]')

df.show()

df.count()

#WE CREATE A NEW COLUMN WITH A LIST WHICH ONLY CONTAINS THE DIRECTOR

def transform_column_crew(column):
    column_data = json.loads(column)
    column_ids = []
    for lista in column_data:
      if lista["job"]=='Director':
        column_ids.append(lista["name"])
    return column_ids

transform_column_crew_udf = udf(transform_column_crew)
df = df.withColumn('director', transform_column_crew_udf('crew'))

df = df.na.drop(subset=['director'])
df = df.filter(col('director') != '[]')

df.show()

df.count()

"""# 3.1. Top 10 most profitable production companies (0.1p)"""

from pyspark.sql.functions import sum, desc, explode, expr, col, regexp_replace

# Convert the "companies_id" column from array to string
df = df.withColumn("production_companies", expr("concat_ws(',', production_companies)"))

# Remove square brackets and spaces from the "company_id" column
df = df.withColumn("production_companies", regexp_replace(col("production_companies"), "[\\[\\] ]", ""))

# Explode the "companies_id" column to separate each company
exploded_df = df.withColumn("production_companies", explode(expr("split(production_companies, ',')")))


# Calculate the total profit for each company
top_production_companies = exploded_df.groupBy("production_companies") \
    .agg(sum("profit").alias("total_profit")) \
    .orderBy(desc("total_profit")) \
    .limit(10)

top_production_companies.show(truncate=False)

"""# 3.2. Top 10 most profitable actors/actresses (0.1p)"""

from pyspark.sql.functions import explode, split

top_10_actors = df.withColumn("actors", explode(split("cast", ","))) \
    .groupBy("actors") \
    .agg(sum("profit").alias("total_profit")) \
    .orderBy("total_profit", ascending=False) \
    .limit(10)

top_10_actors.show()

"""# 3.3. Top 10 most profitable directors. (0.1p)"""

df = df.withColumn("director", regexp_replace(col("director"), "[\\[\\] ]", ""))

top_10_directors = df.groupBy("director") \
    .agg(sum("profit").alias("total_profit")) \
    .orderBy("total_profit", ascending=False) \
    .limit(10)

top_10_directors.show()

"""# 3.4. Top 10 most profitable genres. (0.1p)"""

from pyspark.sql.functions import col, explode, split, sum, regexp_replace, trim

# Convert the "genres_id" column from array to string
df = df.withColumn("genres", col("genres").cast("string"))

# Split the genres_id string column into an array
df = df.withColumn("genres", split(df.genres, ","))

# Explode the genres_id array column
df_exploded = df.withColumn("genre_id", explode("genres"))

# Clean up the genre_id column by removing duplicates, spaces, [ and ]
df_exploded = df_exploded.withColumn("genre_id", trim(regexp_replace("genre_id", "[\\[\\], ]", "")))

# Calculate the total profit for each genre
top_genres_profit = df_exploded.groupBy("genre_id") \
    .agg(sum("profit").alias("total_profit")) \
    .orderBy("total_profit", ascending=False) \
    .limit(10)

top_genres_profit.show(truncate=False)

df.filter(col("production_companies") == "[]").show()

"""# 3.5. Prediction of the commercial success of a movie"""

from pyspark.sql.functions import col, when
# Here we create the successful variable
df = df.withColumn('successful', when(col('profit') > 0, 1).otherwise(0))
df = df.withColumn("successful", col("successful").cast("double"))
# Here we check how many movies are succesful or not and some stadistics
df.select('profit').describe().show()
df.groupBy('successful').count().show()

"""We can see that there is a huge imbalance and that could affect a lot our results"""

from pyspark.ml.feature import StringIndexer, OneHotEncoder, VectorAssembler


indexerAct = StringIndexer(inputCol='cast', outputCol='actor_indexed', handleInvalid="keep")
encoderAct = OneHotEncoder(inputCol='actor_indexed', outputCol='actor_encoded')

indexerPro = StringIndexer(inputCol='production_companies', outputCol='company_indexed', handleInvalid="keep")
encoderPro = OneHotEncoder(inputCol='company_indexed', outputCol='company_encoded')

indexerDir = StringIndexer(inputCol='director', outputCol='director_indexed', handleInvalid="keep")
encoderDir = OneHotEncoder(inputCol='director_indexed', outputCol='director_encoded')

indexerLan = StringIndexer(inputCol='spoken_languages', outputCol='languages_indexed', handleInvalid="keep")
encoderLan = OneHotEncoder(inputCol='languages_indexed', outputCol='languages_encoded')

assembler = VectorAssembler(
    inputCols=['actor_encoded','company_encoded', 'director_encoded', 'budget', 'languages_encoded'],
    outputCol='features'
)

train, test = df.randomSplit([0.8,0.2], seed=42)

from pyspark.ml.classification import LogisticRegression, RandomForestClassifier, DecisionTreeClassifier
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, OneHotEncoder, VectorAssembler
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator

# Define the classifiers
lr = LogisticRegression(featuresCol='features', labelCol='successful', maxIter=10, regParam=0.3)
rf = RandomForestClassifier(featuresCol='features', labelCol='successful')
dt = DecisionTreeClassifier(featuresCol='features', labelCol='successful')

# Define the pipeline for logistic regression
pipeline_lr = Pipeline(stages=[indexerAct, encoderAct, indexerPro, encoderPro, indexerDir, encoderDir,
                               indexerLan, encoderLan, assembler, lr])

# Define the pipeline for random forest
pipeline_rf = Pipeline(stages=[indexerAct, encoderAct, indexerPro, encoderPro, indexerDir, encoderDir,
                               indexerLan, encoderLan, assembler, rf])

# Define the pipeline for decision tree
pipeline_dt = Pipeline(stages=[indexerAct, encoderAct, indexerPro, encoderPro, indexerDir, encoderDir,
                               indexerLan, encoderLan, assembler, dt])

# Combine the pipelines
pipelines = [pipeline_lr, pipeline_rf, pipeline_dt]

# Define the parameter grid for cross-validation
paramGrid = ParamGridBuilder().build()

# Perform cross-validation for each pipeline
for pipeline in pipelines:
    # Create the cross-validator
    crossval = CrossValidator(estimator=pipeline,
                              estimatorParamMaps=paramGrid,
                              evaluator=BinaryClassificationEvaluator(labelCol='successful'),
                              numFolds=5)
    
    # Fit the models and perform cross-validation
    cvModel = crossval.fit(train)
    predictions = cvModel.transform(test)
    
    # Calculate and print the evaluation metrics
    evaluator = MulticlassClassificationEvaluator(labelCol='successful')
    accuracy = evaluator.evaluate(predictions, {evaluator.metricName: "accuracy"})
    precision = evaluator.evaluate(predictions, {evaluator.metricName: "weightedPrecision"})
    recall = evaluator.evaluate(predictions, {evaluator.metricName: "weightedRecall"})
    f1_score = evaluator.evaluate(predictions, {evaluator.metricName: "f1"})
    
    # Print the results
    model_name = pipeline.getStages()[-1].__class__.__name__
    print(f"Model: {model_name}")
    print(f"Accuracy: {accuracy}")
    print(f"Precision: {precision}")
    print(f"Recall: {recall}")
    print(f"F1-score: {f1_score}")
    print("---------------------------")

df.count()

"""# 3.6. Movie recommendation"""

from pyspark.ml.feature import HashingTF, IDF, Tokenizer
from pyspark.ml.feature import StringIndexer
from pyspark.ml import Pipeline

# Preprocessing
selected_data = df.select("movie_id", "original_title", "overview", "genres", "cast", "crew")
selected_data = selected_data.fillna({'overview': ''})  

# TF-IDF
tokenizer = Tokenizer(inputCol="overview", outputCol="words")
hashingTF = HashingTF(inputCol="words", outputCol="rawFeatures")
idf = IDF(inputCol="rawFeatures", outputCol="features")

pipeline = Pipeline(stages=[tokenizer, hashingTF, idf])
transformed_data = pipeline.fit(selected_data).transform(selected_data)

# Calculate Similarity
indexer = StringIndexer(inputCol="original_title", outputCol="titleIndex")
indexed_data = indexer.fit(transformed_data).transform(transformed_data)

# Select movie for recommendation
selected_movie = indexed_data.filter(indexed_data.original_title == "Avatar").first()

# Calculate cosine similarity
cosine_similarities = indexed_data.rdd.map(lambda x: (x.original_title, float(x.features.dot(selected_movie.features))))
cosine_similarities = cosine_similarities.filter(lambda x: x[0] != selected_movie.original_title)

# Get top 5 similar movies
similar_movies = cosine_similarities.takeOrdered(5, key=lambda x: -x[1])

# Print recommended movies
print("RECOMMENDED MOVIES FOR AVATAR:")
for movie in similar_movies:
    print(movie[0])