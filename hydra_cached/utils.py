import functools
import json
import logging
from typing import Optional, List, Dict, Callable, Iterable, Union, Any, Set

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def call_on_self(self, function_name, **kwargs):
    """
    Simple wrapper to make generic functions etc. work with hydra.instantiate().

    :param self: the object to call the function at
    :param function_name: the name of the function
    :param kwargs: keyword argument passed to the function
    :return: the result of the function call
    """
    func = getattr(self, function_name)
    return func(**kwargs)


def dl_to_ld(dl: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """
    Convert a dict containing lists to a list of dicts. 
    """
    return [dict(zip(dl, t)) for t in zip(*dl.values())]


def ld_to_dl(ld: List[Dict[str, Any]], as_numpy: bool = False, as_json_string: bool = False) \
        -> Dict[str, List[Any]]:
    """
    Convert a list of dicts to a dict containing lists. Optionally, convert the result to 
    numpy or json. 
    """
    if as_numpy:
        assert not as_json_string, f'either as_numpy or as_json_string allowed to be True'
        func = lambda x: np.array(x, dtype=object)
    elif as_json_string:
        assert not as_numpy, f'either as_numpy or as_json_string allowed to be True'
        func = lambda x: json.dumps(x)
    else:
        func = lambda x: x
    return {k: [func(dic[k]) for dic in ld] for k in ld[0]}


def maybe_select_column_from_dataframe(as_iloc: Optional[Set[str]] = None, **decorator_kwargs):
    """
    Function decorator that allows to provide a pd.DataFrame and a column name if just a ps.Series is required.  

    Example:

    # Assume
    df = pd.DataFrame([{"a": 1, "b": 2, "c": 3}, {"a": 5, "b": 6, "c": 7}])
    # and
    @maybe_select_column_from_dataframe(data="input_column")
    def dummy(data: pd.Series):
        return data.max()

    # Then, the following command
    dummy(data=df, input_column="a")
    # will just work and return the max of column "a":
    # 5

    # Using as_iloc:
    # Assume
    @maybe_select_column_from_dataframe(data="input_column_idx", as_iloc={"input_column_idx"})
    def dummy(data: pd.Series):
        return data.max()

    # Then, the following command
    dummy(data=df, input_column_idx=0)
    # will just work and return the max of the first column:
    # 5


    :param decorator_kwargs: the decorator parameters are mappings that define which function parameter (key) may be
        also provided as pd.DataFrames by selecting the respective column provided by newly added parameter (value).
    :param as_iloc: a set containing a subset of the parameter names (values) of decorator_kwargs. Values that are set
        when calling the wrapped function will be interpreted as (positional) column indices instead of column names.
    :return: the modified function
    """
    as_iloc = as_iloc or {}
    for x in as_iloc:
        assert x in decorator_kwargs.values(), \
            f'only parameter names defined in the decorator can be added to "as_iloc"'

    def maybe_select_column_from_dataframe_decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            assert len(args) == 0, \
                f'positional arguments are not allowed in functions wrapped with maybe_select_column_from_dataframe ' \
                f'decorator'
            assert "as_iloc" not in kwargs, \
                f'"as_iloc" is not allowed as keyword argument in functions wrapped with ' \
                f'maybe_select_column_from_dataframe'
            for obj_parameter in list(decorator_kwargs):
                col_name_parameter = decorator_kwargs[obj_parameter]
                if col_name_parameter in kwargs:
                    col = kwargs.pop(col_name_parameter)
                    obj = kwargs.pop(obj_parameter)
                    assert isinstance(obj, pd.DataFrame), \
                        f'if {col_name_parameter} is provided, the object "{obj_parameter}" has to be a pd.DataFrame, ' \
                        f'but it is of type: {type(obj)}'
                    if col_name_parameter in as_iloc:
                        assert isinstance(col, int), \
                            f'when adding {col_name_parameter} to as_iloc, the column identifier has to be an int, ' \
                            f'but it is of type "{type(col)}" for {col_name_parameter}={col}'
                        kwargs[obj_parameter] = obj.iloc[:, col]
                    else:
                        kwargs[obj_parameter] = obj[col]
                else:
                    obj = kwargs[obj_parameter]
                    assert isinstance(obj, pd.Series), \
                        f'if {col_name_parameter} is not provided, the object "{obj_parameter}" has to be a pd.Series, ' \
                        f'but it is of type: {type(obj)}'
            return func(**kwargs)
        return wrapper
    return maybe_select_column_from_dataframe_decorator


def maybe_rename_result(rename_parameter):
    """
    A function decorator that allows to rename the result of the function, if a parameter `rename_parameter` is provided.

    Example:
    # Assume
    s = pd.Series([1,2,3])
    # and
    @maybe_rename_result("result_column_name")
    def dummy(data: pd.Series):
        return data

    # Then, the following command
    dummy(data=s, result_column_name="result")
    # will just work and return:
    # 0    1
    # 1    2
    # 2    3
    # Name: result, dtype: int64

    :param rename_parameter: name of the parameter that will be used to rename the result, if present
    :return: the wrapped function
    """
    def maybe_rename_result_decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result_name = None
            if rename_parameter in kwargs:
                result_name = kwargs.pop(rename_parameter)
            res = func(*args, **kwargs)
            if result_name is not None:
                res = res.rename(result_name)
            return res
        return wrapper
    return maybe_rename_result_decorator
