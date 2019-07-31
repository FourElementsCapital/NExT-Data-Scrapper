from bs4 import BeautifulSoup
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, select, Float, Date, Time, join, exists
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy import desc, func
from sqlalchemy.sql import and_, or_
from sqlalchemy import create_engine
import os
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, select, Float, Date, Time, join, exists
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy import desc, func
from sqlalchemy.sql import and_
import spacy
from spacy.matcher import PhraseMatcher
from timeit import default_timer as timer
import arrow
from nltk.stem import SnowballStemmer
import pandas as pd
import utils
import model
from datetime import date
import numpy as np

s = utils.SpacyHelper()
db = utils.DatabaseHelper()


def extract_full_text_and_meta():
    sql_st = select([db.news]).where(
        and_(
            db.news.c.source.like('Mining%'),
            db.news.c.full_text == None
        )
    )
    articles = db.connection.execute(sql_st)
    db.set_mining_com_data(articles)


def calculate_sentiment_scores():
    sql_st = select([db.news]).where(
        and_(
            db.news.c.source.like('Mining%'),
            db.news.c.full_text != "",
            db.news.c.article_length == None
        )
    )
    articles = db.connection.execute(sql_st)
    print("Calculate Sentiment for {} articles".format(articles.rowcount))
    for i, a in enumerate(articles):
        if i % 100 == 0:
            print("Calculating Sentiment: {}/{}".format(i, articles.rowcount))
        p, n, u, l = s.get_article_sentiment(a.full_text)
        up = db.news.update().values(
            positive_count=len(p),
            negative_count=len(n),
            uncertain_count=len(u),
            article_length=l
        ).where(db.news.c.id == a.id)
        db.connection.execute(up)


def calculate_author_bias(start_date, end_date):
    print("Calculating Author Bias")
    sql_st = select([
        db.news.c.author,
        func.avg(db.news.c.positive_count).label('p_count'),
        func.avg(db.news.c.negative_count).label('n_count'),
        func.avg(db.news.c.uncertain_count).label('u_count'),
        func.avg(db.news.c.article_length).label('avg_len'),
        func.count(db.news.c.id).label('article_count')
    ]).where(
        and_(
            db.news.c.source.like('Mining%'),
            db.news.c.article_length != 0,
            db.news.c.article_length != None,
            db.news.c.article_timestamp >= start_date,
            db.news.c.article_timestamp <= end_date,
        )
    ).group_by(
        db.news.c.author
    )
    ## You can print 'sql_st' if you want to see the generated raw sql statement
    res = db.connection.execute(sql_st).fetchall()
    authors = pd.DataFrame(res, columns=[
        'author_name',
        'avg_pos',
        'avg_neg',
        'avg_uncertain',
        'avg_len',
        'article_count'
    ])
    authors = authors.dropna()
    authors['norm_pos'] = authors.avg_pos / authors.avg_len
    authors['norm_neg'] = authors.avg_neg / authors.avg_len
    authors['norm_uncertain'] = authors.avg_uncertain / authors.avg_len

    authors['positive_bias'] = authors['avg_pos'] - authors['avg_neg']
    authors['norm_positive_bias'] = authors.norm_pos - authors.norm_neg
    return authors


def convert_to_date(row):
    row['article_date'] = row['article_timestamp'].date()
    return row


def get_articles(start_date, end_date):

    """
    :param start_date:
    :param end_date:
    :return: Dataframe of articles within the relevant range
    """

    print("Processing Articles")
    sql_st = select([
        db.news.c.id,
        db.news.c.article_timestamp,
        db.news.c.author,
        db.news.c.positive_count,
        db.news.c.negative_count,
        db.news.c.uncertain_count,
        db.news.c.article_length,
        db.news.c.source,
    ]).where(
        and_(
            db.news.c.source.like('Mining%'),
            db.news.c.article_length != 0,
            db.news.c.article_length != None,
            db.news.c.article_timestamp != None,
            db.news.c.article_timestamp >= start_date,
            db.news.c.article_timestamp <= end_date,
        )
    )
    articles = pd.read_sql(sql_st, db.connection, parse_dates=['article_timestamp'])
    articles = articles.apply(convert_to_date, axis=1)
    articles = articles.sort_values('article_date')
    articles = articles.reset_index()
    articles['p_count_norm'] = articles['positive_count'] / articles['article_length']
    articles['n_count_norm'] = articles['negative_count'] / articles['article_length']
    articles['u_count_norm'] = articles['uncertain_count'] / articles['article_length']

    return articles

def train_model(authors, articles, positions, target_column, delta_days):
    print("Starting Training for {}, Delta {}".format(target_column, delta_days))
    best_score = 0
    best_result = None
    for max_b in range(5, 10):
        for min_b in range(-10, -5):
            for x_cols in [['negative'], ['negative', 'positive'], ['negative', 'uncertain'],
                      ['negative', 'positive', 'uncertain']]:
                try:
                    s = model.SentimentModel(authors, articles, positions, target_column, delta_days)
                    s.filter_by_authors(
                        max_positive_bias=max_b,
                        min_positive_bias=min_b
                    ).generate_daily_summaries().process_data()
                    s.lr_cv_split(x_cols)
                    score = s.result['score']
                    if score > best_score:
                        best_score = score
                        best_result = s.result['score']
                        best_params = [max_b, min_b, x_cols]
                    print('values', max_b, min_b, score, x_cols)
                except Exception as e:
                    print("Exception", e)
    return best_result

def get_alphien_data(start_date, end_date, target_column):
    date_range = pd.date_range(start_date, end_date)
    return pd.DataFrame(data = {
        'article_date': date_range,
        target_column : np.random.rand(len(date_range))
    })


def main():
    start_date = date(2014, 7, 28)
    end_date = date(2018, 2, 23)
    target_column = 'avg_net_norm'

    extract_full_text_and_meta()
    calculate_sentiment_scores()

    authors = calculate_author_bias(start_date, end_date)
    articles = get_articles(start_date, end_date)
    positions = get_alphien_data(start_date, end_date, target_column)

    # delta 1 model
    del1_result = train_model(authors, articles, positions, target_column, 1)

    # delta 3 model
    del3_result = train_model(authors, articles, positions, target_column, 3)

    # delta 1 model
    del3_result = train_model(authors, articles, positions, target_column, 5)


if __name__ == "__main__":
    main()
