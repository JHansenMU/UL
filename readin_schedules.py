# This file reads in the unprocessed student schedules
# Each row has a strm, emplid, course.
# The transformation will be each row has a strm, emplid.

# %%
import pandas as pd
import numpy as np
import csv
from pathlib import Path # this used extensivly to get directories organized

# Display all columns without ellipis
pd.set_option('display.max_columns', None)

# %%
# Define path to current directory, data directory, output directory.
curr_dir = Path.cwd()  # Parent is an attribute no paren, cwd is a method paren needed
print("curr_dir is: ", curr_dir)

# %%
# Define parent of curr dir
Path.home()
main_dir = curr_dir.parent
print("main_dir is: ", main_dir)

# %%
# C:\Users\jhyn9\Documents\UMDW\MH_Faculty_Kyle_runs_IN_5235_5243_5327_5335_5343_5427.xlsx
data_dir = main_dir / "ULdata"
print("data_dir is: ", data_dir)

output_dir = main_dir / "ULout"
print("output_dir is: ", output_dir)


#%%
# -- Dataset will come from this query
# -- Business_Classes_by_term_enroll.sql in UMDW directory

# end 12/23/25 ------------------------------------------------------------------


# %%
# Data files for the five departments and all terms are named with the same prefix
filestring = 'MH_Faculty_Kyle_runs_IN_5235_5243_5327_5335_5343_5427'
file = filestring + '.xlsx'
#%%
#
# List of all column names provided
column_names = [
    'EMPLID', 'SSO_ID', 'UM_EMAIL_ADDR', 'FIRST_NAME', 'LAST_NAME',
    'BUSINESS_TITLE', 'STRM', 'STRM_DESCR', 'CRSE_ID', 'SUBJECT',
    'COURSE', 'CRSE_NAME'
]

# Create a dictionary to set the data type for all columns to string
all_str_dtypes = {col: str for col in column_names}
print(all_str_dtypes)

#%%
# We assume the file is in the current working directory, so 'data_dir /' is removed.
# The correct dtype dictionary is passed to read all specified columns as strings.
df = pd.DataFrame()
df = pd.read_excel(data_dir / 
    file,
    dtype=all_str_dtypes
)
print(df.head())
print(df.info())

#%%


