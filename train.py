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
from datetime import date, timedelta
import numpy as np
import rpy2.robjects as robjects
robjects.r('.source4Efunction()')
from rpy2.robjects.packages import importr
rbase = importr('base')
rzoo = importr('zoo')

s = utils.SpacyHelper()
db = utils.DatabaseHelper()

metals =['zinc', 'lead', 'nickel', 'copper', 'aluminium', 'tin']

mapper = {
    'COTMBMML': 'aluminium_long',
    'COTMBMMN': 'aluminium_net',
    'COTMBMMS': 'aluminium_short',
    'COTMBOIN': 'aluminium_total',
    'COTMCMML': 'copper_long',
    'COTMCMMN': 'copper_net',
    'COTMCMMS': 'copper_short',
    'COTMCOIN': 'copper_total',
    'COTMHMML': 'nickel_long',
    'COTMHMMN': 'nickel_net',
    'COTMHMMS': 'nickel_short',
    'COTMHOIN': 'nickel_total',
    'COTMPMML': 'lead_long',
    'COTMPMMN': 'lead_net',
    'COTMPMMS': 'lead_short',
    'COTMPOIN': 'lead_total',
    'COTMQMML': 'tin_long',
    'COTMQMMN': 'tin_net',
    'COTMQMMS': 'tin_short',
    'COTMQOIN': 'tin_total',
    'COTMRMML': 'zinc_long',
    'COTMRMMN': 'zinc_net',
    'COTMRMMS': 'zinc_short',
    'COTMROIN': 'zinc_total'}


def extract_full_text_and_meta():
    """
    Extract text, author and other metadata from all recently add articles
    """
    sql_st = select([db.news]).where(
        and_(
            db.news.c.source.like('Mining%'),
            db.news.c.full_text == None
        )
    )
    articles = db.connection.execute(sql_st)
    db.set_mining_com_data(articles)


def calculate_sentiment_scores():
    """
    Calculate sentiment scores for articles that were newly added
    """
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
    """
    Calculate average sentiment of articles written by authors
    :param start_date of articles to process
    :param end_date of articles to process
    :return: dataframe of authors with average sentiment scores
    """
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
    """
    Extracts date portion from datetime timestamp for each article
    :param row: row to extract date from datetime
    :return: row with date
    """
    row['article_date'] = row['article_timestamp'].date()
    return row


def get_articles(start_date, end_date):
    """
    :param start_date
    :param end_date
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
    """
    :param authors: dataframe of authors with aggregate sentiment scores
    :param articles: dataframe of articles with sentiment scores
    :param positions: dataframe of positions
    :param target_column: name of column being predicted
    :param delta_days: days in the future to make prediction for
    :return:
    """
    print("Starting Training for {}, Delta {}".format(target_column, delta_days))
    best_f1_score = 0
    best_result = None
    best_params = None
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
                    f1_score = s.result['f1_score']
                    if f1_score > best_f1_score:
                        best_f1_score = f1_score
                        best_result = s.result
                        best_params = [max_b, min_b, x_cols]
                except Exception as e:
                    print(e)
                    pass
    return best_result, best_params


def m2ar(matrix,lag = False):
    '''
        convert from rmatrix to pandas DataFrame (4E server only)
        Input
        matrix(rmatrix)		: rmatrix that holds data with index of date
        lag(bool)			: Boolean to decide whether lagging is required 
        Output
        time_series(df)		: Pandas DataFrame
    '''
    arr = np.array(matrix)
    '''Get index'''
    idx = rbase.as_character(rzoo.index(matrix))
    '''Convert to pandas dataframe'''
    if not lag:
        time_series = pd.DataFrame(arr,index=idx)
    else:
        time_series = pd.DataFrame(arr[:-1],index = idx[1:])
    '''Assign proper column names'''
    time_series.columns = matrix.colnames
    return time_series

def get_alphien_data(start_date = None, end_date = None):
    '''
        Get positioning data from alphien
        Input
        start_date(date)		: start date
        end_date(date)			: end date
        target_column(str)      : 
        Output
        time_series(df)		: Pandas DataFrame
        Example
        start_date = date(2014, 7, 28)
        end_date = date(2018, 2, 23)
        get_alphien_data(start_date = start_date, end_date = end_date)
    '''
    # Creating proper dataframe using R
    if start_date is None:
        start_date = 'NULL'
    else:
        start_date = '"'+str(start_date)+'"'
    if end_date is None:
        end_date = 'NULL'
    else:
        end_date = '"'+str(end_date)+'"'
    robjects.r('''tickers = getTickersPositions(exchange = "LME",
                                                direction = c("Net","Total"),
                                                account = c("Managed Money","Open Interest"))''')
    robjects.r('''data = getSecurity(tickers$ticker,extension="Index",
                                     start='''+start_date+''',end='''+end_date+''',
                                     )''')
    data = robjects.r('''data''')
    # Convert R object to pandas df
    data = m2ar(data)
    data.index.name = 'article_date'
    data.reset_index(level=0,inplace=True)
    return data



def process_alphien_data(alphien_data):
    """
    :param alphien_data: raw data about the net and total positions for the 6 base metals
    :return: processed dataframe containing 'avg_net_norm', the target column of interest
    """
    alphien_data = alphien_data.rename(columns = mapper)
    for metal in metals:
        alphien_data['{}_net_norm'.format(metal)] = alphien_data['{}_net'.format(metal)] / alphien_data['{}_total'.format(metal)]
    alphien_data['avg_net_norm'] = alphien_data.loc[:, 'zinc_net_norm': 'tin_net_norm'].mean(axis=1)
    return alphien_data


def main():
    start_date = date(2014, 7, 28)
    end_date = date(2018, 2, 23)
    target_column = 'avg_net_norm'

    extract_full_text_and_meta()
    calculate_sentiment_scores()

    authors = calculate_author_bias(start_date, end_date)
    articles = get_articles(start_date, end_date)
    alphien_data = get_alphien_data(start_date, end_date)
    positions = process_alphien_data(alphien_data)

    results = {}
    # delta 1 model
    del1, del1_best_params = train_model(authors, articles, positions, target_column, 1)
    print("Delta 1 Results - Accuracy: {}, F1 Score: {}".format(del1['accuracy'], del1['f1_score']), )
    results['del1'] = del1['predictions']

    # delta 3 model
    del3, del3_best_params = train_model(authors, articles, positions, target_column, 3)
    print("Delta 3 Results - Accuracy: {}, F1 Score: {}".format(del3['accuracy'], del3['f1_score']), )
    results['del3'] = del3['predictions']

    # delta 5 model
    del5, del5_best_params = train_model(authors, articles, positions, target_column, 5)
    print("Delta 5 Results - Accuracy: {}, F1 Score: {}".format(del5['accuracy'], del5['f1_score']), )
    results['del5'] = del5['predictions']

    date_range = pd.date_range(
        end_date - timedelta(days=len(del1['predictions']) - 1),
        end_date
    )
    results['date'] = date_range

    predictions = pd.DataFrame(data=results)
    return predictions



if __name__ == "__main__":
    main()
