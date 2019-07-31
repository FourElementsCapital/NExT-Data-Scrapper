import pandas as pd
import numpy as np
import sklearn
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split, GridSearchCV
import matplotlib.pyplot as plt
from matplotlib.pyplot import subplot
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, confusion_matrix
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.exceptions import UndefinedMetricWarning

class SentimentModel:
    def __init__(self, authors, articles, positions, target_column, delta_days):
        self.authors = authors
        positions.article_date = pd.to_datetime(positions.article_date)
        articles.article_date = pd.to_datetime(articles.article_date)
        self.articles = articles
        self.positions = positions
        self.target_column = target_column
        self.delta_days = delta_days

    def process_one_day(self, k, data):
        res = {'article_date': k}
        res['positive'] = data.p_count_norm.mean()
        res['negative'] = data.n_count_norm.mean()
        res['uncertain'] = data.u_count_norm.mean()
        res['avg_article_len'] = data.article_length.mean()
        res['article_count'] = len(data)
        return res

    def generate_daily_summaries(self):
        days = []
        grouped_data = self.filtered_articles.groupby('article_date')
        for k, v in grouped_data.groups.items():
            data = grouped_data.get_group(k)
            days.append(self.process_one_day(k, data))
        dd = pd.DataFrame(days)
        dd = dd.sort_values('article_date')
        dd = dd.reset_index()
        self.data = self.positions.merge(dd, on='article_date')
        return self

    def filter_by_authors(self, max_positive_bias=None, min_positive_bias=None):
        # produce a smaller subset of articles based on selected authors
        # authors avg_net is avg_pos - avg_neg
        self.filtered_authors = self.authors.copy(deep=True)
        if max_positive_bias:
            self.filtered_authors = self.filtered_authors[self.filtered_authors['positive_bias'] < max_positive_bias]
        if min_positive_bias:
            self.filtered_authors = self.filtered_authors[self.filtered_authors['positive_bias'] > min_positive_bias]

        if not hasattr(self, 'filtered_authors'):
            self.filtered_authors = self.authors

        # only select articles frm list of articles
        self.filtered_articles = self.articles[self.articles.author.isin(self.filtered_authors.author_name)]
        return self

    def process_data(self, classes=2):
        self.calculate_deltas(self.target_column)
        if classes == 2:
            self.data = self.data.apply(self.delta_direction2, args=(self.target_column,), axis=1)
        elif classes == 3:
            self.data = self.data.apply(self.delta_direction3, args=(self.target_column,), axis=1)
        else:
            raise NotImplementedError

    def calculate_deltas(self, col_name):
        # calculates changes between today and previous 1,3 and 5 days for target column
        self.data['{}_del1'.format(col_name)] = self.data[col_name].diff(-1) * -1
        self.data['{}_del3'.format(col_name)] = self.data[col_name].diff(-3) * -1
        self.data['{}_del5'.format(col_name)] = self.data[col_name].diff(-5) * -1
        self.data = self.data.dropna()
        return self

    def delta_direction2(self, row, col_name):
        # converts changes into categories, 1 for positive change and -1 for negative change
        row['{}_del1_dir'.format(col_name)] = 1 if row['{}_del1'.format(col_name)] > 0 else -1
        row['{}_del3_dir'.format(col_name)] = 1 if row['{}_del3'.format(col_name)] > 0 else -1
        row['{}_del5_dir'.format(col_name)] = 1 if row['{}_del5'.format(col_name)] > 0 else -1
        return row

    def delta_direction3(self, row, col_name):
        col_names = ['{}_del1'.format(col_name), '{}_del3'.format(col_name), '{}_del5'.format(col_name)]
        for c in col_names:
            val = 0
            if row[c] > 0.005:
                val = 1
            elif row[c] < -0.005:
                val = -1
            else:
                val = 0
            row[c + '_dir'] = val
        return row

    def lr_cv_split(self, x_cols):
        y_col = "{}_del{}_dir".format(self.target_column, self.delta_days)
        df = self.data
        df = df.dropna(subset=[y_col])
        X = df[x_cols]
        y = df[y_col]

        # Use 70% of data for training
        ts = int(len(df) / 10 * 7)
        X_train = X.iloc[:ts]
        X_test = X.iloc[ts:]
        y_train = y.iloc[:ts]
        y_test = y.iloc[ts:]

        pca_lr_parameters = {
            'pca__n_components': [None, 0.95, 0.9, 0.85, 0.8],
            'lr__C': [2 ** -7, 2 ** -6, 2 ** -5, 2 ** -4, 2 ** -3, 2 ** -2, 2 ** -1, 1,
                      2, 2 ** 2, 2 ** 3, 2 ** 4, 2 ** 5, 2 ** 6, 2 ** 7]
        }

        lr = LogisticRegression(solver='lbfgs')

        pca = PCA()
        pca_lr_pipeline = Pipeline([('scale', StandardScaler()), ('pca', pca), ('lr', lr)])
        clf = GridSearchCV(pca_lr_pipeline, pca_lr_parameters, cv=5, iid=False, n_jobs=-1, return_train_score=True,
                           scoring='f1')
        clf.fit(X_train, y_train);

        result = {
            'name': '{}-{}'.format(y_col, x_cols),
            'x_cols': x_cols,
            'clf': clf,
            'predictions': clf.predict(X_test),
            'X_test': X_test,
            'y_test': y_test
        }
        self.result = result
        # self.result['score'] = max(self.result['clf'].cv_results_['mean_test_score'])
        self.result['score'] = f1_score(self.result['y_test'], self.result['clf'].predict(self.result['X_test']))
        return self