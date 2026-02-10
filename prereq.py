
# This program uses two files to perform operations.
# 1. The data file FSJtemp.xlsx
# 2. The class prereq file preq_table_counter_v5.xlsx
# --- --- --- 
#
#%%
import pandas as pd
import numpy as np
import re
from pathlib import Path

# %%
# Formatting for diagnostics
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

# Path setup
curr_dir = Path.cwd()
main_dir = curr_dir.parent
data_dir = main_dir / "UpperLevel"
output_dir = main_dir / "ULout"

# Filenames
# data_file_name = 'FSJtemp_readin.xlsx' # test data still need to try FIN test
# data_file_name = 'FSJtemp3_readin.xlsx' # test data still need to try FIN test
data_file_name = 'FSJtemp3all_readin.xlsx' # Full Data FS25 census IDs
preq_file_name = 'preq_table_counter_v6.xlsx'

print(f"--- DIAGNOSTIC: Path Check ---")
print(f"Data Directory: {data_dir}")

# %%
# 1. Read in the main student data
df = pd.DataFrame()
try:
    xls = pd.ExcelFile(data_dir / data_file_name)
    # Reading without dtype first to get all columns, then we will handle types
    df = pd.read_excel(xls, keep_default_na=False)
    
    # FIX: Force all column names to lowercase to avoid KeyErrors
    df.columns = df.columns.str.lower()
    
    # Ensure ID and Term columns are strings
    cols_to_fix = ['emplid', 'strm', 'term', 'admit_term']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = df[col].astype(str)

    # NEW: Ensure grd_pts_per_unit is a float
    if 'grd_pts_per_unit' in df.columns:
        # errors='coerce' turns non-numeric values into NaN to prevent crashes
        df['grd_pts_per_unit'] = pd.to_numeric(df['grd_pts_per_unit'], errors='coerce')
            
    print(f"SUCCESS: Read {data_file_name}. Shape: {df.shape}")
    print(f"Columns found: {df.columns.tolist()}")

except Exception as e:
    print(f"ERROR reading {data_file_name}: {e}")
    # Fallback/Debug: print available files if not found
    import os
    print(f"Files in directory: {os.listdir(data_dir) if data_dir.exists() else 'Dir not found'}")
    raise e

# %%
# 2. Transform catalog_nbr and create 'class'
print("\n--- DIAGNOSTIC: Column Transformation ---")
# Check if catalog_nbr exists after lowercasing
if 'catalog_nbr' in df.columns:
    # Extract exactly 4 digits. Example: '_0110' -> '0110', '1014W' -> '1014'
    df['catalog_nbr_clean'] = df['catalog_nbr'].astype(str).str.extract(r'(\d{4})')
    
    # Create 'class' = subject + '_' + cleaned catalog_nbr
    # Using .fillna('0000') in case regex fails to find 4 digits
    df['class'] = df['subject'].astype(str) + '_' + df['catalog_nbr_clean'].fillna('0000')
    
    print("Sample of cleaning logic:")
    print(df[['subject', 'catalog_nbr', 'class']].drop_duplicates().head(20))
else:
    print("CRITICAL ERROR: 'catalog_nbr' column not found. Check Excel headers.")

# %%
# 3. Read the Prerequisite Table
print("\n--- DIAGNOSTIC: Prerequisite Table Loading ---")
try:
    preq_df = pd.read_excel(data_dir / preq_file_name)
    # Force preq columns to lowercase for consistency
    preq_df.columns = preq_df.columns.str.lower()
    
    # The user mentioned 'Class' column in preq file
    target_classes = preq_df['class'].dropna().unique().tolist()
    print(f"Found {len(target_classes)} target classes in {preq_file_name}.")
    print(f"Targets: {target_classes}")
except Exception as e:
    print(f"ERROR reading prerequisite file: {e}")
    target_classes = []

# %%
# 4. Prepare df2 (The Wide File)
df2 = pd.DataFrame()
last_term = '5427'
print(f"\n--- DIAGNOSTIC: Filtering for Term {last_term} ---")

constant_cols = [
    'emplid', 'strm', 'term', 'admit_term', 'admit_term_desc', 
    'um_clevel_descr', 'acad_prog', 'acad_plan', 'acad_subplan',
    'course_source', # MU, TRANSFER, Test
    'cum_gpa', 'tot_cumulative', 'tot_hrs_life'
]

# Create df2 using only the records from the last_term
df2 = df[df['strm'] == last_term].copy()

if df2.empty:
    print(f"WARNING: No data found for strm {last_term}. Check if data uses that term code.")
else:
    # Get unique students (one row per student)
    df2 = df2[constant_cols].drop_duplicates(subset=['emplid'])
    print(f"Unique students in df2: {len(df2)}")
    print(f"Note students who graduate or who are not enrolled in, last_term +1, are not in this set.")

    # 5. Initialize Target Columns
    print("\n--- DIAGNOSTIC: Initializing Target Columns ---")
    for target in target_classes:
        df2[target] = 0
        df2[target + '_SEM_ELI'] = 0

#%%
    print(f"Total columns in df2 now: {len(df2.columns)}")
    print("\n--- PREVIEW OF df2 STRUCTURE ---")
    print(df2.head())

#%%
    print(f"Total columns in df now: {len(df.columns)}")
    print("\n--- PREVIEW OF df STRUCTURE ---")
    print(df.head())

#%%
# --- Step 3: Populate df2 columns (Case-Standardized Version) ---

# 1. Standardize metadata headers to Lowercase (emplid, strm, class, etc.)
df.columns = df.columns.str.lower()
df2.columns = df2.columns.str.lower()

# 2. Standardize COURSE IDENTIFIERS to Uppercase in both the data and the target list
# This ensures 'ECONOM_1014' in the data matches 'ECONOM_1014' in the column names
df['class'] = df['class'].astype(str).str.upper()
target_classes = [str(c).upper() for c in target_classes]

# 3. Rename the existing target columns in df2 to Uppercase
# This fixes the problem where df2 had 'econom_1014' but the data had 'ECONOM_1014'
rename_dict = {c.lower(): c.upper() for c in target_classes}
df2 = df2.rename(columns=rename_dict)

# 4. Ensure SEM_ELI columns also follow a consistent pattern (e.g., uppercase class + _SEM_ELI)
eli_rename = { (c.lower() + '_sem_eli'): (c.upper() + '_SEM_ELI') for c in target_classes }
df2 = df2.rename(columns=eli_rename)

# 5. Prepare for the loop
df_sorted = df.sort_values(by=['emplid', 'strm'], ascending=True)
df2.set_index('emplid', inplace=True)

print(f"Standardization Complete. Tracking {len(target_classes)} uppercase target classes.")

# 6. Step through each row and populate. If class exists mark as taken (2) or in progress (1).
# *** may need to change query to put value in query for transfer classes if float(row['grd_pts_per_unit']) > 0: 
for idx, row in df_sorted.iterrows():
    sid = str(row['emplid'])
    current_class = str(row['class']) # This is now guaranteed Uppercase
    
    # Matching check
    if sid in df2.index and current_class in df2.columns:
        # Check grade points
        if float(row['grd_pts_per_unit']) > 0:
            df2.at[sid, current_class] = 2
        else:
            df2.at[sid, current_class] = 1

# 7. Reset index
df2.reset_index(inplace=True)

#%%
print(f"Total columns in df2 now: {len(df2.columns)}")
print("\n--- PREVIEW OF df2 STRUCTURE ---")
print(df2.head())

#%%
# --- DIAGNOSTICS ---
print("\n" + "="*50)
print("DIAGNOSTIC: CASE-SENSITIVITY VERIFICATION")
print("="*50)

# Check if any 2s or 1s were actually placed
passed_count = (df2[target_classes] == 2).sum().sum()
attemp_count = (df2[target_classes] == 1).sum().sum()

print(f"Matches found and updated as PASSED (2):   {passed_count}")
print(f"Matches found and updated as ATTEMPTED (1): {attemp_count}")

if passed_count == 0:
    print("\n[STILL NO MATCHES FOUND] - Secondary Debugging:")
    print(f"Example class from Source df: '{df['class'].iloc[0]}'")
    print(f"Example class from df2 columns: '{target_classes[0]}'")
    print(f"Are they identical? {df['class'].iloc[0] == target_classes[0]}")
else:
    # Show a successful match sample
    sample_student = df2[df2[target_classes].any(axis=1)].head(1)
    if not sample_student.empty:
        sid = sample_student['emplid'].values[0]
        print(f"\nSuccess! Found matches for Student {sid}.")
        active_cols = [c for c in target_classes if df2.loc[df2['emplid']==sid, c].values[0] > 0]
        print(f"Courses populated: {active_cols}")

print("="*50)

#%%
# --- Export df2 to CSV ---

# 1. Define the output file name
output_filename = "df2_populated_wide_FS25census.csv"
output_path = output_dir / output_filename

# 2. Ensure the output directory exists
output_dir.mkdir(parents=True, exist_ok=True)

# 3. Export to CSV (index=False avoids adding an extra ID column)
df2.to_csv(output_path, index=False)

print(f"--- Export Complete ---")
print(f"File saved to: {output_path}")

# %%
# --- Step 3: Semester Eligibility Counting (Revised with Set Isolation) ---
# -- The below gap counting excludes any summer semester. Previous code below script notated. 
# -- Note: If class was taken twice (low grade repeat) eligibility flag will throw at first taken.
# -- an example student is '12581334' for 'ACCTCY_2037'
# 1. Standardize Case and Identification
df.columns = df.columns.str.lower()
df2.columns = df2.columns.str.upper()

# Ensure identifiers are consistent
df['catalog_nbr_clean'] = df['catalog_nbr'].astype(str).str.extract(r'(\d{4})')
df['class'] = (df['subject'].astype(str) + '_' + df['catalog_nbr_clean'].fillna('0000')).str.upper()

df['emplid'] = df['emplid'].astype(str)
df2['EMPLID'] = df2['EMPLID'].astype(str)
df2.set_index('EMPLID', inplace=True)

df_sorted = df.sort_values(by=['emplid', 'strm'])
target_classes_upper = [str(c).upper() for c in target_classes]

print("Processing student eligibility terms...")

for student_id in df2.index:
    student_history = df_sorted[df_sorted['emplid'] == student_id]
    unique_terms = sorted(student_history['strm'].unique())
    
    for target_class in target_classes_upper:
        # --- CRITICAL FIX ---
        # Initialize set inside target_class loop so history resets for each class evaluation
        completed_courses = set()
        count_term = 0
        
        # Determine eligibility baseline
        req_row = preq_df[preq_df['class'].str.upper() == target_class].iloc[0]
        cond_req = req_row['condreq']
        is_eligible = (cond_req == 0)

        # Diagnostics for requested class
        is_diag = (target_class == 'ACCTCY_2037')
        if is_diag:
            print(f"\n[DIAGNOSTIC] Student: {student_id} | Class: {target_class}")
            print(f" Initial is_eligible: {is_eligible}")

        for i, term in enumerate(unique_terms):
            term_rows = student_history[student_history['strm'] == term]
            
            # State at the START of the term
            already_eligible_at_start = is_eligible
            
            # Context for evaluation
            current_credits = term_rows['tot_cumulative'].max()
            current_level = str(term_rows['um_clevel_descr'].iloc[0]).upper()
            
            # 1. CHECK: Is student taking class this term?
            is_taking_now = target_class in term_rows['class'].values
            
            if is_taking_now:
                # Count if eligible prior to this term (unless it is the very first term)
                if already_eligible_at_start and i > 0:
                    count_term += 1
                if is_diag:
                    print(f" Term: {term} (i={i}) | TAKING NOW | count_term final: {count_term}")
                break 
            
            # 2. INCREMENT: Count elapsed terms (Gap)
            # Only if eligible prior to this term AND it is not the first term
            if already_eligible_at_start and i > 0:
                # --- ADDED: Check to skip counting Gap terms ending in '35' ---
                if not str(term).endswith('35'):
                    count_term += 1
            
            if is_diag:
                print(f" Term: {term} (i={i}) | EligibleAtStart: {already_eligible_at_start} | count_term: {count_term}")

            # 3. UPDATE HISTORY & ELIGIBILITY: For the NEXT iteration
            passed = term_rows[term_rows['grd_pts_per_unit'] > 0]['class'].tolist()
            completed_courses.update(passed)
            
            if not is_eligible:
                # If-Then Prerequisite Logic
                if target_class in ['ACCTCY_2036', 'MANGMT_3000'] and current_credits >= 28:
                    is_eligible = True
                elif target_class == 'ACCTCY_2037':
                    if any(c in completed_courses for c in ['ACCTCY_2036', 'ACCTCY_2136']):
                        is_eligible = True
                elif target_class == 'ACCTCY_2258' and current_level in ['SOPHOMORE', 'JUNIOR', 'SENIOR']:
                    is_eligible = True
                elif target_class == 'MANGMT_3540' and current_credits >= 30:
                    is_eligible = True
                elif target_class == 'MRKTNG_3000' and current_credits >= 45:
                    is_eligible = True
                elif target_class == 'FINANC_3000':
                    c1 = (current_credits >= 45)
                    c2 = ('STAT_2500' in completed_courses or ('STAT_2200' in completed_courses and any(s in completed_courses for s in ['STAT_1200', 'STAT_1300', 'STAT_1400'])))
                    c3 = any(e in completed_courses for e in ['ECONOM_1014', 'ABM_1041'])
                    c4 = any(e in completed_courses for e in ['ECONOM_1015', 'ECONOM_1051', 'ABM_1042'])
                    c5 = any(a in completed_courses for a in ['ACCTCY_2027', 'ACCTCY_2037', 'ACCTCY_2137'])
                    if all([c1, c2, c3, c4, c5]): is_eligible = True
                
                if is_diag and is_eligible:
                    print(f"  >> Became eligible at end of term {term}")

        # Final store
        col_name = target_class + '_SEM_ELI'
        if col_name in df2.columns:
            df2.at[student_id, col_name] = count_term

df2.reset_index(inplace=True)
print("Updated all eligibility counters.")
df2.head()

#%%
# Final export to the output directory
df2.to_csv(output_dir / "df2_final_with_counts_all.csv", index=False)
print(f"Success! Final data saved to: {output_dir / 'df2_final_with_counts_all.csv'}")



#%%

# --- Descriptive Statistics Table with Dynamic 'last_term' Label ---
# --- Step 4: Descriptive Statistics Table with Fixed SD Calculation ---

# 1. Initialize list for statistics
final_stats_list = []

# Define the dynamic column header using the last_term variable
dynamic_col_label = f"Students Elg '{last_term}' not enrolled"

# 2. Iterate through each target class to calculate unique stats
for target_class in target_classes_upper:
    # Set the relevant columns for this iteration
    status_col = target_class              # The enrollment status (0, 1, or 2)
    eli_col = target_class + '_SEM_ELI'    # The eligibility counter
    
    # FILTER: Only include students who:
    # A) Have NOT taken/attempted the class (status == 0)
    # B) HAVE been eligible for at least 1 term (eli_col > 0)
    subset = df2[(df2[status_col] == 0) & (df2[eli_col] > 0)]
    
    # SUBSET FOR DYNAMIC COLUMN: Eligible in last_term specifically and not enrolled
    last_term_eligible_subset = df2[(df2[status_col] == 0) & (df2[eli_col] == 1)]
    
    # 3. Calculate Descriptive Stats for THIS class's subset only
    if not subset.empty:
        # Calculate mean of the SEM_ELI column for this filtered subset
        class_mean = subset[eli_col].mean()
        
        # Calculate standard deviation of the SEM_ELI column for this filtered subset
        # Note: std() returns NaN if Num Students is 1
        class_sd = subset[eli_col].std()
        
        class_count = len(subset)
    else:
        class_mean = 0
        class_sd = 0
        class_count = 0
        
    # 4. Compile Row Data
    final_stats_list.append({
        'Class': target_class,
        'Mean num Terms Eligible': round(class_mean, 2),
        'SD': round(class_sd, 2) if not pd.isna(class_sd) else 0,
        'Num Students': class_count,
        dynamic_col_label: len(last_term_eligible_subset)
    })

# 5. Create the final statistics DataFrame
stats_df = pd.DataFrame(final_stats_list)

# 6. Display the table to verify unique SD values
print(f"\n--- Descriptive Statistics: Analysis for Term {last_term} ---")
print(stats_df)

# 7. Export the table to your output directory
stats_df.to_csv(output_dir / 'descriptive_stats_final.csv', index=False)

#%%
# --- Exporting Class-Specific Eligibility Tables ---

# 1. Define the structural columns we want to keep in every table
# These are the metadata columns (emplid, strm, etc.)
metadata_cols = [
    'EMPLID', 'STRM', 'TERM', 'ADMIT_TERM', 'ADMIT_TERM_DESC',
    'UM_CLEVEL_DESCR', 'ACAD_PROG', 'ACAD_PLAN', 'ACAD_SUBPLAN',
    'CUM_GPA', 'TOT_CUMULATIVE', 'TOT_HRS_LIFE'
]

# 2. Define the target classes for the individual tables
export_targets = ['FINANC_3000', 'MRKTNG_3000', 'MANGMT_3000']

print("Exporting specific eligibility tables...")

for base_class in export_targets:
    status_col = base_class
    eli_col = base_class + '_SEM_ELI'
    
    # Check if columns exist in df2 to prevent KeyErrors
    if status_col in df2.columns and eli_col in df2.columns:
        
        # FILTER: Only include students used in the 'Num Students' count
        # Logic: Status == 0 (Not Taken) AND SEM_ELI > 0 (Eligible)
        filtered_subset = df2[(df2[status_col] == 0) & (df2[eli_col] > 0)].copy()
        
        # SELECT: Metadata columns + the 2 specific class columns
        columns_to_export = metadata_cols + [status_col, eli_col]
        final_table = filtered_subset[columns_to_export]
        
        # 3. EXPORT: Save to the output directory
        file_name = f"Eligible_Not_Enrolled_{base_class}.csv"
        file_path = output_dir / file_name
        final_table.to_csv(file_path, index=False)
        
        print(f" - Exported {len(final_table)} records for {base_class} to {file_name}")
    else:
        print(f" - Skipping {base_class}: Columns not found in df2.")

print("\nAll individual class tables have been saved to the output directory.")

#%% ---- END ---




#%%
# Block of code before '35' update


# --- Step 3: Semester Eligibility Counting (Revised with Set Isolation) ---

# 1. Standardize Case and Identification
df.columns = df.columns.str.lower()
df2.columns = df2.columns.str.upper()

# Ensure identifiers are consistent
df['catalog_nbr_clean'] = df['catalog_nbr'].astype(str).str.extract(r'(\d{4})')
df['class'] = (df['subject'].astype(str) + '_' + df['catalog_nbr_clean'].fillna('0000')).str.upper()

df['emplid'] = df['emplid'].astype(str)
df2['EMPLID'] = df2['EMPLID'].astype(str)
df2.set_index('EMPLID', inplace=True)

df_sorted = df.sort_values(by=['emplid', 'strm'])
target_classes_upper = [str(c).upper() for c in target_classes]

print("Processing student eligibility terms...")

for student_id in df2.index:
    student_history = df_sorted[df_sorted['emplid'] == student_id]
    unique_terms = sorted(student_history['strm'].unique())
    
    for target_class in target_classes_upper:
        # --- CRITICAL FIX ---
        # Initialize set inside target_class loop so history resets for each class evaluation
        completed_courses = set()
        count_term = 0
        
        # Determine eligibility baseline
        req_row = preq_df[preq_df['class'].str.upper() == target_class].iloc[0]
        cond_req = req_row['condreq']
        is_eligible = (cond_req == 0)

        # Diagnostics for requested class
        is_diag = (target_class == 'ACCTCY_2037')
        if is_diag:
            print(f"\n[DIAGNOSTIC] Student: {student_id} | Class: {target_class}")
            print(f" Initial is_eligible: {is_eligible}")

        for i, term in enumerate(unique_terms):
            term_rows = student_history[student_history['strm'] == term]
            
            # State at the START of the term
            already_eligible_at_start = is_eligible
            
            # Context for evaluation
            current_credits = term_rows['tot_cumulative'].max()
            current_level = str(term_rows['um_clevel_descr'].iloc[0]).upper()
            
            # 1. CHECK: Is student taking class this term?
            is_taking_now = target_class in term_rows['class'].values
            
            if is_taking_now:
                # Count if eligible prior to this term (unless it is the very first term)
                if already_eligible_at_start and i > 0:
                    count_term += 1
                if is_diag:
                    print(f" Term: {term} (i={i}) | TAKING NOW | count_term final: {count_term}")
                break 
            
            # 2. INCREMENT: Count elapsed terms (Gap)
            # Only if eligible prior to this term AND it is not the first term
            if already_eligible_at_start and i > 0:
                count_term += 1
            
            if is_diag:
                print(f" Term: {term} (i={i}) | EligibleAtStart: {already_eligible_at_start} | count_term: {count_term}")

            # 3. UPDATE HISTORY & ELIGIBILITY: For the NEXT iteration
            passed = term_rows[term_rows['grd_pts_per_unit'] > 0]['class'].tolist()
            completed_courses.update(passed)
            
            if not is_eligible:
                # If-Then Prerequisite Logic
                if target_class in ['ACCTCY_2036', 'MANGMT_3000'] and current_credits >= 28:
                    is_eligible = True
                elif target_class == 'ACCTCY_2037':
                    if any(c in completed_courses for c in ['ACCTCY_2036', 'ACCTCY_2136']):
                        is_eligible = True
                elif target_class == 'ACCTCY_2258' and current_level in ['SOPHOMORE', 'JUNIOR', 'SENIOR']:
                    is_eligible = True
                elif target_class == 'MANGMT_3540' and current_credits >= 30:
                    is_eligible = True
                elif target_class == 'MRKTNG_3000' and current_credits >= 45:
                    is_eligible = True
                elif target_class == 'FINANC_3000':
                    c1 = (current_credits >= 45)
                    c2 = ('STAT_2500' in completed_courses or ('STAT_2200' in completed_courses and any(s in completed_courses for s in ['STAT_1200', 'STAT_1300', 'STAT_1400'])))
                    c3 = any(e in completed_courses for e in ['ECONOM_1014', 'ABM_1041'])
                    c4 = any(e in completed_courses for e in ['ECONOM_1015', 'ECONOM_1051', 'ABM_1042'])
                    c5 = any(a in completed_courses for a in ['ACCTCY_2027', 'ACCTCY_2037', 'ACCTCY_2137'])
                    if all([c1, c2, c3, c4, c5]): is_eligible = True
                
                if is_diag and is_eligible:
                    print(f"  >> Became eligible at end of term {term}")

        # Final store
        col_name = target_class + '_SEM_ELI'
        if col_name in df2.columns:
            df2.at[student_id, col_name] = count_term

df2.reset_index(inplace=True)
print("Updated all eligibility counters.")
df2.head()





#%%
#%%






#%%

import pandas as pd
import numpy as np
import re
from pathlib import Path

# %%
# Formatting for diagnostics
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

# Path setup logic from your previous steps
curr_dir = Path.cwd()
main_dir = curr_dir.parent
data_dir = main_dir / "UpperLevel"
output_dir = main_dir / "ULout"

# Filenames
data_file_name = 'FSJtemp_readin.xlsx'
preq_file_name = 'preq_table_counter_v5.xlsx'

print(f"--- DIAGNOSTIC: Directory Check ---")
print(f"Looking for data in: {data_dir}")
print(f"Looking for targets in: {data_dir / preq_file_name}")

# %%
# 1. Read in the main student data
try:
    # Attempt to read the Excel file
    xls = pd.ExcelFile(data_dir / data_file_name)
    df = pd.read_excel(xls, dtype={
        'emplid': str,
        'strm': str,
        'term': str,
        'ADMIT_TERM': str
    }, keep_default_na=False)
    print(f"\nSUCCESS: Read {data_file_name}. Shape: {df.shape}")
except Exception as e:
    print(f"\nERROR: Could not read {data_file_name}. Error: {e}")
    # Fallback for environment testing if file is differently named
    df = pd.read_csv('FSJtemp_readin.xlsx - FSJ.csv', dtype={'EMPLID': str, 'STRM': str})
    df.columns = [c.lower() for c in df.columns]
# Preview the results
print("--- DataFrame Head ---")
print(df.head())
print("\n--- DataFrame Info ---")
print(df.info())

# %%
print("--- DataFrame Tail ---")
print(df.tail(8))

# %%
# 2. Transform catalog_nbr and create 'class'
print("\n--- DIAGNOSTIC: Column Transformation ---")
# Extract exactly 4 digits. Example: '_0110' -> '0110', '1014W' -> '1014'
df['catalog_nbr_clean'] = df['catalog_nbr'].astype(str).str.extract(r'(\d{4})')
df['class'] = df['subject'].astype(str) + '_' + df['catalog_nbr_clean'].fillna('XXXX')

print(f"Sample of transformed classes:\n{df[['subject', 'catalog_nbr', 'class']].head(5)}")

# %%
# 3. Read the Prerequisite Table
print("\n--- DIAGNOSTIC: Prerequisite Table Loading ---")
try:
    preq_df = pd.read_excel(data_dir / preq_file_name)
    target_classes = preq_df['Class'].dropna().unique().tolist()
    print(f"Found {len(target_classes)} target classes in {preq_file_name}.")
    print(f"Target Classes: {target_classes}")
except Exception as e:
    print(f"ERROR reading prerequisite file: {e}")
    target_classes = []

# %%
# 4. Prepare df2 (The Wide File)
last_term = '5427'
print(f"\n--- DIAGNOSTIC: Filtering for Term {last_term} ---")

constant_cols = [
    'emplid', 'strm', 'term', 'admit_term', 'admit_term_desc',
    'um_clevel_descr', 'acad_prog', 'acad_plan', 'acad_subplan',
    'cum_gpa', 'tot_cumulative', 'tot_hrs_life'
]

# Ensure we only have unique students from the latest term
df2 = df[df['strm'] == last_term].copy()
initial_count = len(df2)
df2 = df2[constant_cols].drop_duplicates(subset=['emplid'])
final_count = len(df2)

print(f"Initial rows for term {last_term}: {initial_count}")
print(f"Unique students (rows) in df2: {final_count}")

# %%
# 5. Initialize set of Target Columns
print("\n--- DIAGNOSTIC: Column Initialization ---")
new_cols_added = 0
for target in target_classes:
    # Initialize the class indicator and the semester eligibility counter
    df2[target] = 0
    df2[target + '_SEM_ELI'] = 0
    new_cols_added += 2

print(f"Added {new_cols_added} tracking columns to df2.")

# %%
# 6. Final Data Integrity Check
print("\n--- FINAL DF2 CHECK ---")
print(f"Final df2 Shape: {df2.shape}")
print("\nFirst 3 rows of df2 (Metadata):")
print(df2[constant_cols].head(3))

print("\nFirst 3 rows of df2 (Target Class Columns sample):")
# Show the first few initialized target columns
sample_targets = [c for c in df2.columns if c not in constant_cols][:6]
print(df2[sample_targets].head(3))

# Verify if any students from df2 exist in the source data
student_sample = df2['emplid'].iloc[0] if not df2.empty else "None"
print(f"\nVerification: Student {student_sample} has {len(df[df['emplid']==student_sample])} total course records in source df.")

# --- 6. Checks and Verification ---
print("--- df2 Shape ---")
print(df2.shape)
print("\n--- df2 Sample Columns ---")
print(df2.columns.tolist()[:20]) # Displaying first 20 columns for brevity
print("\n--- df2 Preview ---")
print(df2.head())

# Save the initial structure to a CSV for inspection
df2.to_csv('df2_initial_structure.csv', index=False)