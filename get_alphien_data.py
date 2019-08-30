import rpy2.robjects as robjects
import numpy as np
import pandas as pd
from datetime import date
robjects.r('.sourceQlib()')
from rpy2.robjects.packages import importr
rbase = importr('base')
rzoo = importr('zoo')


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
    return data