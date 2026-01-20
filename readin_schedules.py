# This file reads in the unprocessed student schedules
# Each row has a strm, emplid, course.
# The transformation will be each row has a strm, emplid.
# %%
import pandas as pd
import numpy as np
from pathlib import Path

# Display all columns without ellipsis for easier debugging in the console
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

# %%
# 1. SETUP DIRECTORIES
# Define path to current directory, data directory, and output directory
curr_dir = Path.cwd() 
main_dir = curr_dir.parent

# C:\Users\...\Documents\UpperLevel\
data_dir = main_dir / "UpperLevel"
output_dir = main_dir / "ULout"

# Ensure output directory exists
output_dir.mkdir(parents=True, exist_ok=True)

print(f"Data directory: {data_dir}")
print(f"Output directory: {output_dir}")

# %%
# 2. READ IN THE DATA
# Define filename based on the 'FSJtemp' prefix
filestring = 'FSJtemp'
file_path = data_dir / f"{filestring}.xlsx"

# Using ExcelFile can be more efficient for large workbooks
xls = pd.ExcelFile(file_path)

# Load the data. 
# We explicitly set EMPLID and Term codes to 'str' to prevent dropping leading zeros.
# 'keep_default_na=False' ensures missing data stays as empty strings rather than NaN.
df = pd.read_excel(
    xls, 
    dtype={
        'EMPLID': str,
        'STRM': str,
        'TERM': str,
        'ADMIT_TERM': str,
        'CLASS_NBR': str,
        'CATALOG_NBR': str
    },
    keep_default_na=False
)

# %%
# 3. VERIFY DATA LOAD
print("\n--- Data Head ---")
print(df.head())

print("\n--- Data Info ---")
print(df.info())

# Checking unique student count to ensure the 'tot_hrs_life' partition logic is ready
unique_students = df['EMPLID'].nunique()
print(f"\nProcessing records for {unique_students} unique students.")

#%%
import re

# %%
# 1. INITIALIZE VARIABLES AND CLEANING
# Define the reference term for the output
last_term = '5427'

# Clean CATALOG_NBR: Keep only the 4-digit numeric core
# This removes leading underscores, trailing 'W', or other characters
def clean_catalog(val):
    match = re.search(r'(\d{4})', str(val))
    return match.group(1) if match else ''

df['catalog_nbr_clean'] = df['CATALOG_NBR'].apply(clean_catalog)

# Create the CLASS identifier
df['CLASS'] = df['SUBJECT'] + '_' + df['catalog_nbr_clean']

# %%
# 2. CREATE THE BASE DF2 (One row per student)
# We filter for the 'last_term' to get the constant demographics for that point in time
constant_cols = [
    'EMPLID', 'STRM', 'TERM', 'ADMIT_TERM', 'ADMIT_TERM_DESC',
    'UM_CLEVEL_DESCR', 'ACAD_PROG', 'ACAD_PLAN', 'ACAD_SUBPLAN',
    'CUM_GPA', 'TOT_CUMULATIVE', 'TOT_HRS_LIFE'
]

# Filter for the last term and drop duplicates to ensure one row per student
df2 = df[df['STRM'] == last_term][constant_cols].drop_duplicates(subset=['EMPLID']).copy()

# %%
# 3. INITIALIZE COURSE AND ELIGIBILITY COLUMNS
# Defining the list of specific classes and their eligibility suffix
target_classes = [
    'ECONOM_1014_28', 'BUS_AD_1500_28', 'ENGLISH_1000_28',
    'ECONOM_1015_40', 'BUS_AD_2500_40', 'ACCTCY_2036_40',
    'ACCTCY_2037_50', 'ACCTCY_2258_50', 'MANGMT_3000_50', 'MANGMT_3540_50',
    'STAT_2500_60', 'ECONOM_3229_60', 'ECONOM_3251_60', 'MRKTING_3000_60',
    'FINANC_3000_64'
]

# Loop through the target list to create the columns initialized at 0
for cls_col in target_classes:
    # Course completion column (e.g., ECONOM_1014_28)
    df2[cls_col] = 0
    
    # Semester Eligibility column (e.g., ECONOM_1014_28_SEM_ELI)
    eli_col = f"{cls_col}_SEM_ELI"
    df2[eli_col] = 0

# %%
# 4. DISPLAY TO CHECK STRUCTURE
print(f"--- df2 Structure for Term {last_term} ---")
print(f"Total Students: {len(df2)}")
print(f"Total Columns: {len(df2.columns)}")

# Displaying a subset of the new columns to verify initialization
print("\nSample of initialized columns:")
sample_cols = ['EMPLID'] + target_classes[:3] + [f"{target_classes[0]}_SEM_ELI"]
print(df2[sample_cols].head())

#%%
df2.head()

#%%
df.head()

# %% 
# 1. UPDATED MAPPING LOGIC
# We use rsplit('_', 1) to split only at the LAST underscore.
# Example: 'BUS_AD_1500_28' becomes ['BUS_AD_1500', '28']
class_to_col_map = { c.rsplit('_', 1)[0]: c for c in target_classes }

# Verify the map (it should now correctly contain 'BUS_AD_1500')
print("Class Mapping Sample:")
for key in list(class_to_col_map.items())[:5]:
    print(f"  {key[0]} -> {key[1]}")

# %%
# 2. POPULATE COURSE STATUS COLUMNS
print("\nPopulating course status columns...")

# Sort by EMPLID and STRM to process history in chronological order
df_sorted = df.sort_values(by=['EMPLID', 'STRM'], ascending=[True, True])

for index, row in df_sorted.iterrows():
    eid = row['EMPLID']
    current_class = row['CLASS']
    
    # Only process students present in our df2 (last_term cohort)
    if eid in df2['EMPLID'].values:
        
        # Check if the CLASS (e.g., 'BUS_AD_1500') is in our map
        if current_class in class_to_col_map:
            target_col = class_to_col_map[current_class]
            
            # Ensure Grade Points is treated as a float for comparison
            try:
                grade_pts = float(row['GRD_PTS_PER_UNIT'])
            except (ValueError, TypeError):
                continue
            
            # Step 1: Grade Points > 0 -> Status 2 (Completed)
            if grade_pts > 0:
                df2.loc[df2['EMPLID'] == eid, target_col] = 2
                
            # Step 2: Grade Points == 0 -> Status 1 (Attempted)
            # We don't overwrite a 2 (Pass) with a 1 (Fail/Drop)
            elif grade_pts == 0:
                current_val = df2.loc[df2['EMPLID'] == eid, target_col].values[0]
                if current_val != 2:
                    df2.loc[df2['EMPLID'] == eid, target_col] = 1

# %%
# 3. VERIFY RESULTS
print("\n--- df2 Status Check ---")
# Specifically checking a class with multiple underscores in the name
if 'BUS_AD_1500_28' in df2.columns:
    print(f"Status counts for BUS_AD_1500_28:\n{df2['BUS_AD_1500_28'].value_counts()}")

#%%
# 4. VERIFY TRANSFORMATION
print("\n--- df2 Transformation Verification ---")
# Check a few students who are known to have taken target courses
print(df2[['EMPLID', 'ECONOM_1014_28', 'BUS_AD_1500_28', 'ACCTCY_2036_40', 'ACCTCY_2037_50']].head(10))

# Summary of statuses
print("\nStatus counts for ECONOM_1014_28:")
print(df2['ECONOM_1014_28'].value_counts())

#%%










































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
# C:\Users\jhyn9\Documents\UpperLevel\FSJtemp.xlsx
data_dir = main_dir / "UpperLevel"
print("data_dir is: ", data_dir)

output_dir = main_dir / "ULout"
print("output_dir is: ", output_dir)

#%%
# -- Dataset will come from this query

# %%
# Data files for the five departments and all terms are named with the same prefix
filestring = 'FSJtemp'
file = filestring + '.xlsx'
xls = pd.ExcelFile(data_dir/'FSJtemp.xlsx')
df = pd.DataFrame()
df = pd.read_excel(xls, dtype={'EMPLID': str
                               ,'TERM': str
                               ,'STRM': str
                               ,'ADMIT_TERM': str}
                               , keep_default_na=False)
print(df.head())
print(df.info())

#%%


