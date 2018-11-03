from pathlib import Path

import pandas as pd


def read_filter_lbmp(path):
    """
    Read one csv file with pandas. Convert the Time Stamp field to pandas
    datetime format. Filter out non-NYC nodes and only keep required columns.
    Change column names to snake case for easier access.
    
    Parameters
    ----------
    path : str or other object for read_csv filepath parameter
        Path to csv file with LBMP data
    
    Returns
    -------
    DataFrame
        df with 3 columns (time stamp, name of node, LBMP)
    """

    
    df = pd.read_csv(path, parse_dates=['Time Stamp'])
    df = df.loc[df.Name == 'N.Y.C.', ['Time Stamp', 'Name', 'LBMP ($/MWHr)']]
    df.columns = ['time_stamp', 'name', 'lbmp']
    return df

