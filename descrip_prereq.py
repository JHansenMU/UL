#%%
#
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
data_file_name = 'FSJ_all.csv' 
preq_file_name = 'preq_table_counter_v5.xlsx'

print(f"--- DIAGNOSTIC: Path Check ---")
print(f"Data Directory: {data_dir}")

# %%
# 1. Read in the main student data
df = pd.DataFrame()
try:
    # Reading CSV as requested
    df = pd.read_csv(data_dir / data_file_name, keep_default_na=False)
    
    # FIX: Force all column names to lowercase to avoid KeyErrors
    df.columns = df.columns.str.lower()
    
    # Ensure ID and Term columns are strings
    cols_to_fix = ['emplid', 'strm', 'term', 'admit_term', 'admit_term_rollup']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = df[col].astype(str)
            
    print(f"SUCCESS: Read {data_file_name}. Shape: {df.shape}")
    print(f"Columns found: {df.columns.tolist()}")

except Exception as e:
    print(f"ERROR reading {data_file_name}: {e}")
    import os
    print(f"Files in directory: {os.listdir(data_dir) if data_dir.exists() else 'Dir not found'}")
    raise e


# %%
# 1. Filter by Term and Academic Level
# Filter for specific term '5343'
df_term = df[df['strm'] == '5343'].copy()

# Define target levels and further filter the dataframe
target_levels = ['FRESHMAN', 'SOPHOMORE', 'JUNIOR', 'SENIOR']
df_filtered = df_term[df_term['um_clevel_descr'].isin(target_levels)].copy()

# Calculate totals
total_unique_term = df_term['emplid'].nunique()
total_unique_filtered = df_filtered['emplid'].nunique()

print(f"Total Unique Students in Term 5343: {total_unique_term:,}")
print(f"Total Unique Students (FR, SO, JR, SR) in Term 5343: {total_unique_filtered:,}")

# Breakdown by level to verify sorting and counts
level_counts = df_filtered.groupby('um_clevel_descr')['emplid'].nunique()
print("\nBreakdown by Level (Term 5343):")
print(level_counts.reindex(target_levels))


# These numbers are less than ELMO Census reporting but we will use it for now. 2/2/26

# The rest below is test material.
# --- ------------------------------------------------------------------
#%%

# %% 

# 3. Filtering and Custom Sorting
# Drop 2ND BACH
df = df[df['um_clevel_descr'] != '2ND BACH'].copy()

# Set categorical order for Levels
level_order = ['FRESHMAN', 'SOPHOMORE', 'JUNIOR', 'SENIOR', 'MASTERS']
df['um_clevel_descr'] = pd.Categorical(df['um_clevel_descr'], categories=level_order, ordered=True)

# %%
# 4. Diagnostic Table: FIN_BANK, REAL_EST, and BOTH (Distinct Counts)
print("\n" + "="*65)
print("DIAGNOSTIC: DISTINCT STUDENT OVERLAP (FIN_BANK & REAL_EST)")
print("="*65)

fin_ids = set(df[df['acad_subplan'] == 'FIN_BANK']['emplid'])
re_ids = set(df[df['acad_subplan'] == 'REAL_EST']['emplid'])
both_ids = fin_ids.intersection(re_ids)

def get_distinct_by_level(id_set):
    subset = df[df['emplid'].isin(id_set)]
    return subset.groupby('um_clevel_descr', observed=False)['emplid'].nunique()

diag_df = pd.DataFrame({
    'FIN_BANK_TOTAL': get_distinct_by_level(fin_ids),
    'REAL_EST_TOTAL': get_distinct_by_level(re_ids),
    'BOTH_FIN_AND_RE': get_distinct_by_level(both_ids)
})

# Add Total Row for the Diagnostic
diag_df.loc['TOTAL_UNIQUE'] = [len(fin_ids), len(re_ids), len(both_ids)]
print(diag_df)

# %%
# 5. Descriptive Stats with Specific Plan Totals
print("\n" + "="*65)
print("DISTINCT STUDENT COUNTS BY PLAN (WITH TOTALS)")
print("="*65)

# Create the main Plan table
plan_stats = df.groupby(['acad_plan', 'um_clevel_descr'], observed=False)['emplid'].nunique().unstack(fill_value=0)

# Add a 'TOTAL' column (Sum across the levels)
plan_stats['TOTAL'] = plan_stats.sum(axis=1)

# Filter for the specific plans requested
requested_plans = ['ACCT_BSACC', 'BUSAD_BSBA', 'UNDEC_BUS']
# Using intersection to avoid errors if a plan is missing from the data
available_plans = [p for p in requested_plans if p in plan_stats.index]

print("\n[1] Requested Academic Plan Totals:")
print(plan_stats.loc[available_plans])

# %%
# 6. Subplan Stats (Ensuring REAL_EST follows FIN_BANK)
print("\n" + "="*65)
print("DISTINCT STUDENT COUNTS BY SUBPLAN")
print("="*65)

subplan_stats = df.groupby(['acad_subplan', 'um_clevel_descr'], observed=False)['emplid'].nunique().unstack(fill_value=0)
subplan_stats['TOTAL'] = subplan_stats.sum(axis=1)

# Custom Sort for Subplans: Move FIN_BANK and REAL_EST to specific positions if they exist
sp_index = list(subplan_stats.index)
if 'FIN_BANK' in sp_index and 'REAL_EST' in sp_index:
    # Remove them from current list
    sp_index.remove('FIN_BANK')
    sp_index.remove('REAL_EST')
    # Re-insert them at the end (or specific position)
    sp_index.extend(['FIN_BANK', 'REAL_EST'])
    subplan_stats = subplan_stats.reindex(sp_index)

# Display only rows with students
print(subplan_stats[subplan_stats['TOTAL'] > 0])









#%%
# -- --- --- --------







# %%
# 3. Data Cleaning & Custom Sorting
# Drop 2ND BACH and set custom order for levels
df = df[df['um_clevel_descr'] != '2ND BACH'].copy()

level_order = ['FRESHMAN', 'SOPHOMORE', 'JUNIOR', 'SENIOR', 'MASTERS']
df['um_clevel_descr'] = pd.Categorical(df['um_clevel_descr'], categories=level_order, ordered=True)

# Custom order for Subplan to ensure REAL_EST follows FIN_BANK
# We get unique subplans, remove our targets, then insert them in specific order
all_subplans = [s for s in df['acad_subplan'].unique() if s not in ['FIN_BANK', 'REAL_EST', '']]
subplan_order = all_subplans + ['FIN_BANK', 'REAL_EST'] 
df['acad_subplan'] = pd.Categorical(df['acad_subplan'], categories=subplan_order, ordered=True)

# %%
# 4. Diagnostics: FIN_BANK vs REAL_EST Overlap
print("\n" + "="*60)
print("DIAGNOSTIC: FINANCE & REAL ESTATE STUDENT OVERLAP")
print("="*60)

# Create sets of IDs for comparison
fin_ids = set(df[df['acad_subplan'] == 'FIN_BANK']['emplid'])
re_ids = set(df[df['acad_subplan'] == 'REAL_EST']['emplid'])
both_ids = fin_ids.intersection(re_ids)

# Filter dataframe for these specific groups to get level distribution
fin_only_df = df[df['emplid'].isin(fin_ids - both_ids)]
re_only_df = df[df['emplid'].isin(re_ids - both_ids)]
both_df = df[df['emplid'].isin(both_ids)]

# Build the diagnostic table
diag_data = {
    'FIN_BANK (Only)': fin_only_df.groupby('um_clevel_descr')['emplid'].nunique(),
    'REAL_EST (Only)': re_only_df.groupby('um_clevel_descr')['emplid'].nunique(),
    'BOTH (FIN & RE)': both_df.groupby('um_clevel_descr')['emplid'].nunique()
}

diag_table = pd.DataFrame(diag_data).fillna(0).astype(int)
diag_table['TOTAL_UNIQUE'] = diag_table.sum(axis=1)

print(diag_table)

# %%
# 5. Updated Grouped Stats (Applying the new sorting)
print("\n" + "="*60)
print("ORDERED STATS BY SUBPLAN")
print("="*60)

subplan_stats = df.groupby(['acad_subplan', 'um_clevel_descr'], observed=False)['emplid'].nunique().unstack(fill_value=0)
# Displaying only subplans that have students
print(subplan_stats[subplan_stats.sum(axis=1) > 0])



# %%
# 2. Descriptive Statistics (Distinct Counts)
# We use nunique('emplid') to ensure we are counting unique students, 
# not just total rows (which might be multiple per student due to class enrollments).

print("\n" + "="*50)
print("DESCRIPTIVE STATISTICS: DISTINCT STUDENT COUNTS")
print("="*50)

# A. Overall Counts by Level
if 'um_clevel_descr' in df.columns and 'emplid' in df.columns:
    overall_stats = df.groupby('um_clevel_descr')['emplid'].nunique().sort_values(ascending=False)
    print("\n[1] Overall Student Counts by Level:")
    print(overall_stats)

# B. Counts by Academic Plan and Level
if all(col in df.columns for col in ['acad_plan', 'um_clevel_descr', 'emplid']):
    plan_stats = df.groupby(['acad_plan', 'um_clevel_descr'])['emplid'].nunique().unstack(fill_value=0)
    print("\n[2] Student Counts by Academic Plan and Level:")
    print(plan_stats)

# C. Counts by Academic Subplan and Level
if all(col in df.columns for col in ['acad_subplan', 'um_clevel_descr', 'emplid']):
    subplan_stats = df.groupby(['acad_subplan', 'um_clevel_descr'])['emplid'].nunique().unstack(fill_value=0)
    print("\n[3] Student Counts by Academic Subplan and Level:")
    print(subplan_stats)


# %%
