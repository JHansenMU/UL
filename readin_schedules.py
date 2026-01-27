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
filestring = 'FSJtemp_readin'
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
print(f"Total rows in df: {len(df)}")
# %%
# 3. VERIFY DATA LOAD
print("\n--- Data Head ---")
print(df.head())

print("\n--- Data Tail ---")
print(df.tail(7))

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

#%%
df.tail(7)

# %% 
# 1. UPDATED MAPPING LOGIC
# We use rsplit('_', 1) to split only at the LAST underscore.
# Example: 'BUS_AD_1500_28' becomes ['BUS_AD_1500', '28']
class_to_col_map = { c.rsplit('_', 1)[0]: c for c in target_classes }

# Verify the map (it should now correctly contain 'BUS_AD_1500')
print("Class Mapping Sample:")
for key in list(class_to_col_map.items())[:15]:
    print(f"  {key[0]} -> {key[1]}")

# %%
# 2. POPULATE COURSE STATUS COLUMNS
print("\nPopulating course status columns...")

# Sort by EMPLID and STRM to process history in chronological order
df_sorted = df.sort_values(by=['EMPLID', 'STRM'], ascending=[True, True])

print(f"Total rows in df: {len(df)}")
print(f"Total rows in df_sorted: {len(df_sorted)}")


for index, row in df_sorted.iterrows():
    eid = row['EMPLID']
    current_class = row['CLASS']

# -- test start
    if eid not in df2['EMPLID'].values:
        # Unprinted because student isn't in df2
        continue
    if current_class not in class_to_col_map:
        # Unprinted because the class isn't in your mapping
        continue

    # Only rows that make it here get printed
    print(f"ID: {eid} | Class: {current_class} ...")
# -- test end

    
    # Only process students present in our df2 (last_term cohort)
    if eid in df2['EMPLID'].values:
        
        # Check if the CLASS (e.g., 'BUS_AD_1500') is in our map
        if current_class in class_to_col_map:
            target_col = class_to_col_map[current_class]
            
            # Ensure Grade Points is treated as a float for comparison
            try:
                grade_pts = float(row['GRD_PTS_PER_UNIT'])
                
                print(f"ID: {eid} | Term: {row['STRM']} | Class: {current_class} | Target: {target_col} | GP: {grade_pts}")

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
print(df2[['EMPLID', 'ECONOM_1014_28', 'BUS_AD_1500_28', 'ACCTCY_2036_40', 'ACCTCY_2037_50', 'MRKTING_3000_60']].head(10))

# Summary of statuses
print("\nStatus counts for ECONOM_1014_28:")
print(df2['ECONOM_1014_28'].value_counts())

#%%
#%%
# -- updated Logic example below
import pandas as pd
import numpy as np
import re

# Load the new prerequisite table to drive the class list
df_preq_v5 = pd.read_excel(data_dir / 'preq_table_counter_v5.xlsx')

# %%
# 3. POPULATE df2 ELIGIBILITY COUNTERS
print("Processing eligibility counters with explicit class-by-class checks...")

# Helper function to check if a specific class exists in history with Grade Points >= 0
def check_pass(hist, strm_limit, target_class):
    return not hist[(hist['STRM'] <= strm_limit) & 
                    (hist['CLASS'] == target_class) & 
                    (hist['GRADE_POINTS'] >= 0)].empty

# Iterating through each student in the cohort (df2)
for idx, row_df2 in df2.iterrows():
    eid = row_df2['EMPLID']
    # Get all historical records for this student sorted by term
    student_history = df[df['EMPLID'] == eid]
    student_strms = sorted(student_history['STRM'].unique())
    
    # Check each target class (e.g., ECONOM_1014_28)
    for target_col in target_classes:
        base_class = target_col.rsplit('_', 1)[0]
        eli_col = f"{target_col}_SEM_ELI"
        meeting_term_idx = -1
        
        # --- ELIGIBILITY CHECKING (Identify the Meeting Term) ---
        for i, strm in enumerate(student_strms):
            is_eligible = False
            
            # Context for the current term (Credits and Level)
            term_data = student_history[student_history['STRM'] == strm]
            max_cum = term_data['TOT_CUMULATIVE'].max()
            current_levels = term_data['UM_CLEVEL_DESCR'].unique()
            
            # --- START CLASS-SPECIFIC IF-THEN CONDITIONS ---
            
            # ECONOM_1014, BUS_AD_1500, ENGLISH_1000, ECONOM_1015, BUS_AD_2500, 
            # STAT_2500, ECONOM_3229, ECONOM_3251: No Prerequisites
            if base_class in ['ECONOM_1014', 'BUS_AD_1500', 'ENGLISH_1000', 'ECONOM_1015', 
                            'BUS_AD_2500', 'STAT_2500', 'ECONOM_3229', 'ECONOM_3251']:
                is_eligible = True
                
            # ACCTCY_2036: Requires 28 cumulative credit hours
            elif base_class == 'ACCTCY_2036':
                if max_cum >= 28: is_eligible = True
                
            # ACCTCY_2037: Completion of ACCTCY 2036 or 2136
            elif base_class == 'ACCTCY_2037':
                if check_pass(student_history, strm, 'ACCTCY_2036') or check_pass(student_history, strm, 'ACCTCY_2136'):
                    is_eligible = True
                    
            # ACCTCY_2258: Requires Sophomore, Junior, or Senior standing
            elif base_class == 'ACCTCY_2258':
                if any(lvl in ['SOPHOMORE', 'JUNIOR', 'SENIOR'] for lvl in current_levels):
                    is_eligible = True
                    
            # MANGMT_3000: Requires 28 cumulative credit hours
            elif base_class == 'MANGMT_3000':
                if max_cum >= 28: is_eligible = True
                
            # MANGMT_3540: Requires 30 cumulative credit hours
            elif base_class == 'MANGMT_3540':
                if max_cum >= 30: is_eligible = True
                
            # MRKTING_3000: Requires 45 cumulative credit hours
            elif base_class == 'MRKTING_3000':
                if max_cum >= 45: is_eligible = True
                
            # FINANC_3000: Complex multi-part requirement
            elif base_class == 'FINANC_3000':
                # Condition 1: 45 Credits
                req1 = max_cum >= 45
                # Condition 2: Stats (Various options)
                req2 = (check_pass(student_history, strm, 'STAT_2500') or 
                       (check_pass(student_history, strm, 'STAT_2200') and check_pass(student_history, strm, 'STAT_1200')) or
                       (check_pass(student_history, strm, 'STAT_2200') and check_pass(student_history, strm, 'STAT_1300')) or
                       (check_pass(student_history, strm, 'STAT_2200') and check_pass(student_history, strm, 'STAT_1400')))
                # Condition 3: Econ 1014 / ABM 1041
                req3 = (check_pass(student_history, strm, 'ECONOM_1014') or check_pass(student_history, strm, 'ABM_1041'))
                # Condition 4: Econ 1015 / Econ 1051 / ABM 1042
                req4 = (check_pass(student_history, strm, 'ECONOM_1015') or 
                        check_pass(student_history, strm, 'ECONOM_1051') or 
                        check_pass(student_history, strm, 'ABM_1042'))
                # Condition 5: Acctcy 2027 / 2037 / 2137
                req5 = (check_pass(student_history, strm, 'ACCTCY_2027') or 
                        check_pass(student_history, strm, 'ACCTCY_2037') or 
                        check_pass(student_history, strm, 'ACCTCY_2137'))
                
                if all([req1, req2, req3, req4, req5]):
                    is_eligible = True
            
            # Once we find the FIRST term the student is eligible, mark it and stop checking terms
            if is_eligible:
                meeting_term_idx = i
                break

        # --- COUNTER LOGIC ---
        count_term = 0
        
        # Start counting terms AFTER the meeting term (or from the beginning if "none")
        if base_class in ['ECONOM_1014', 'BUS_AD_1500', 'ENGLISH_1000', 'ECONOM_1015', 
                        'BUS_AD_2500', 'STAT_2500', 'ECONOM_3229', 'ECONOM_3251']:
            start_idx = 0
        else:
            start_idx = meeting_term_idx + 1 if meeting_term_idx != -1 else None

        if start_idx is not None:
            for i in range(start_idx, len(student_strms)):
                current_strm = student_strms[i]
                count_term += 1
                
                # Was the class taken/completion found in this specific term?
                taken = not student_history[(student_history['STRM'] == current_strm) & 
                                          (student_history['CLASS'] == base_class) & 
                                          (student_history['GRADE_POINTS'] >= 0)].empty
                
                # Stop counting if taken OR if we reached the last_term
                if taken or current_strm == last_term:
                    break
            
            df2.at[idx, eli_col] = count_term

# %%
# VERIFY RESULTS
print("\nFinal wide-format summary (df2):")
cols_to_preview = ['EMPLID', 'ACCTCY_2037_50_SEM_ELI', 'FINANC_3000_64_SEM_ELI']
print(df2[cols_to_preview].head(10))

# Export to your output directory
df2.to_csv(output_dir / 'Student_Course_Eligibility_Report.csv', index=False)

# END updated logic example

#%%




# %%
# 3. VERIFY OUTPUT
print("\n--- Wide Format Transformation (df2) Summary ---")
print(f"Total Rows (Students): {len(df2)}")

# Displaying sample for verification
cols_to_show = ['EMPLID', 'ECONOM_1014_28_SEM_ELI', 'ACCTCY_2036_40_SEM_ELI', 'FINANC_3000_64_SEM_ELI']
print(df2[cols_to_show].head(10))

# Save the final DataFrame to a CSV for your review
df2.to_csv(output_dir / 'Student_Progress_Wide.csv', index=False)

#%%
# END 1_21_26 --- --- ---
# --- --- --- --- --- ---








































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


