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

def get_alphien_data(start_date, end_date, target_column):
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
            target_column = 'avg_net_norm'
            get_alphien_data(start_date = start_date, end_date = end_date, target_column = target_column)
    '''
    # Creating proper dataframe using R
    robjects.r('''tickers = getTickersPositions(exchange = "LME",
                                                direction = c("Net","Total"),
                                                account = c("Managed Money","Open Interest"))''')
#    robjects.r('''name = getReferenceBuildingBlock(fieldName = "name",
#                                                   key = "researchTicker",selectionKey = tickers$commo)''')
#    robjects.r('''colnam = tolower(paste0(name[,1],"_",tickers$direction))''')
    robjects.r('''colnam = tolower(paste0(tickers$commo,"_",tickers$direction))''')
    robjects.r('''data = getSecurity(tickers$ticker,extension="Index")''')
    robjects.r('''colnames(data) = colnam''')
    data = robjects.r('''data''')
    # Convert R object to pandas df
    data = m2ar(data)
    date_range = pd.date_range(start_date, end_date)
    return pd.DataFrame(data = {
        'article_date': date_range,
        target_column : np.random.rand(len(date_range))
    })