import model
import warnings
import pandas as pd
from sklearn.exceptions import UndefinedMetricWarning
warnings.filterwarnings("ignore", category=UndefinedMetricWarning)
pd.set_option('display.max_colwidth', -1)

def train_model(authors, articles, positions, target_column, delta_days):
    warnings.filterwarnings("ignore", category=UndefinedMetricWarning)
    """
    :param authors: dataframe of authors with aggregate sentiment scores
    :param articles: dataframe of articles with sentiment scores
    :param positions: dataframe of positions
    :param target_column: name of column being predicted
    :param delta_days: days in the future to make prediction for
    :return:
    Example
    result, best_params = train_model(authors, articles, positions, 'avg_net_norm', 3)
    print(result['accuracy'])

    """
    print("Starting Training for {}, Delta {}".format(target_column, delta_days))
    best_mts = 0
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
                    mts = s.result['mean_test_score']
                    accuracy = s.result['accuracy']
                    if mts > best_mts:
                        best_mts = mts
                        best_result = s.result
                        best_params = [max_b, min_b, x_cols]
                except Exception as e:
                    print('Exception', e)
    return best_result, best_params