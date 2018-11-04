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

def read_all_nyc(data_path):
    """
    Reads and combines individual LBMP data files.
    
    Parameters
    ----------
    data_path : Path object
        This is a pathlib Path object pointing to the LBMP data folder with
        .csv files.
    
    Returns
    -------
    DataFrame
        df with 4 columns (time stamp, name of node, LBMP, hour of year)
    """

    fnames = data_path.glob('**/*.csv')
    dfs = [read_filter_lbmp(name) for name in fnames]
    df = pd.concat(dfs)
    df.sort_values('time_stamp', inplace=True)
    df.reset_index(inplace=True, drop=True)
    df['hour'] = df.index

    return df
