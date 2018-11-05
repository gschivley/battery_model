import numpy as np
import pandas as pd
from pyomo.environ import *


def model_to_df(model, first_hour, last_hour):
    """
    Create a dataframe with hourly charge, discharge, state of charge, and
    price columns from a pyomo model. Only uses data from between the first
    (inclusive) and last (exclusive) hours.
    
    Parameters
    ----------
    model : pyomo model
        Model that has been solved

    first_hour : int
        First hour of data to keep
    last_hour: int
        The final hour of data to keep
    
    Returns
    -------
    dataframe
        
    """
    # Need to increase the first & last hour by 1 because of pyomo indexing 
    # and add 1 to the value of last model hour because of the range
    # second model hour by 1
    hours = range(model.T[first_hour + 1], model.T[last_hour + 1] + 1)
    Ein = [value(model.Ein[i]) for i in hours]
    Eout = [value(model.Eout[i]) for i in hours]
    lbmp = [model.P.extract_values()[None][i] for i in hours]
    charge_state = [value(model.S[i]) for i in hours]

    df_dict = dict(
        hour=hours,
        Ein=Ein,
        Eout=Eout,
        lbmp=lbmp,
        charge_state=charge_state
    )

    df = pd.DataFrame(df_dict)

    return df

def optimize_year(df, first_model_hour=0, last_model_hour=8759):
    """
    Optimize the charge/discharge behavior of a battery storage unit over a
    full year. Assume perfect foresight of electricity prices. The battery
    has a discharge constraint equal to its storage capacity and round-trip
    efficiency of 85%.
    
    Parameters
    ----------
    df : dataframe
        dataframe with columns of hourly LBMP and the hour of the year
    first_model_hour : int, optional
        Set the first hour of the year to be considered in the optimization
        (the default is 0)
    last_model_hour : int, optional
        Set the last hour of the year to be considered in the optimization (the
        default is 8759)
    
    Returns
    -------
    dataframe
        hourly state of charge, charge/discharge behavior, lbmp, and time stamp
    """

    #Filter the data
    df = df.loc[first_model_hour:last_model_hour, :]

    model = ConcreteModel()

    # Define model parameters
    model.T = Set(doc='hour of year', initialize=df.hour.tolist(), ordered=True)
    model.Rmax = Param(initialize=100,
                       doc='Max rate of power flow (kW) in or out')
    model.Smax = Param(initialize=200, doc='Max storage (kWh)')
    model.Dmax = Param(initialize=200, doc='Max discharge in 24 hour period')
    model.P = Param(initialize=df.lbmp.tolist(), doc='LBMP for each hour')
    eta = 0.85 # Round trip storage efficiency

    # Charge, discharge, and state of charge
    # Could use bounds for the first 2 instead of constraints
    model.Ein = Var(model.T, domain=NonNegativeReals)
    model.Eout = Var(model.T, domain=NonNegativeReals)
    model.S = Var(model.T, bounds=(0, model.Smax))


    #Set all constraints
    def storage_state(model, t):
        'Storage changes with flows in/out and efficiency losses'
        # Set first hour state of charge to half of max
        if t == model.T.first():
            return model.S[t] == model.Smax / 2
        else:
            return (model.S[t] == (model.S[t-1] 
                                + (model.Ein[t-1] * np.sqrt(eta)) 
                                - (model.Eout[t-1] / np.sqrt(eta))))

    model.charge_state = Constraint(model.T, rule=storage_state)

    def discharge_constraint(model, t):
        "Maximum dischage within a single hour"
        return model.Eout[t] <= model.Rmax

    model.discharge = Constraint(model.T, rule=discharge_constraint)

    def charge_constraint(model, t):
        "Maximum charge within a single hour"
        return model.Ein[t] <= model.Rmax

    model.charge = Constraint(model.T, rule=charge_constraint)

    # Without a constraint the model would discharge in the final hour
    # even when SOC was 0.
    def positive_charge(model, t):
        'Limit discharge to the amount of charge in battery, including losses'
        return model.Eout[t] <= model.S[t] / np.sqrt(eta)
    model.positive_charge = Constraint(model.T, rule=positive_charge)

    def discharge_limit(model, t):
        "Limit on discharge within a 24 hour period"
        max_t = model.T.last()

        # Check all t until the last 24 hours
        # No need to check with < 24 hours remaining because the constraint is
        # already in place for a larger number of hours
        if t < max_t - 24:
            return sum(model.Eout[i] for i in range(t, t+24)) <= model.Dmax
        else:
            return Constraint.Skip

    model.limit_out = Constraint(model.T, rule=discharge_limit)

    # Define the battery income, expenses, and profit
    income = sum(df.loc[t, 'lbmp'] * model.Eout[t] for t in model.T)
    expenses = sum(df.loc[t, 'lbmp'] * model.Ein[t] for t in model.T)
    profit = income - expenses
    model.objective = Objective(expr=profit, sense=maximize)

    # Solve the model
    solver = SolverFactory('glpk')
    solver.solve(model)

    results_df = model_to_df(model, first_hour=first_model_hour,
                             last_hour=last_model_hour)
    results_df['time_stamp'] = df.loc[:, 'time_stamp']

    return results_df
