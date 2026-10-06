
# This program uses two files to perform operations.
# 1. The data file FSJtemp.xlsx
# 2. The class prereq file preq_table_counter_v5.xlsx

# For the prereq BUS_AD_3500
# Line 340 4/20/26, Note we currently use 'Bus_Maj' to catch this requirement 
# and we set the Bus_Maj in the SQL. Doing this avoids potential duplicates 
# when we try and capture ACAD_PLAN. Cleaner solution.
# in SQL line 130-137:  census_courses_MU_TRE_TEST.sql

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
cen_trm = 'FS25' # equates with 5343
lst_trm = 'SP26' # equates with 5427
# data_file_name = 'FSJtemp_readin.xlsx' # test data still need to try FIN test
# data_file_name = 'FSJtemp3_readin.xlsx' # test data still need to try FIN test
# data_file_name = 'FSJ_all_SP26.xlsx' # Fall 25 census IDs Download 4_20_26
# data_file_name = 'FSJ_all_SP26_testset2.xlsx' # Fall 25 census IDs Three students to check prereq count terms eligible

data_file_name = cen_trm + '_' + lst_trm + '.xlsx' # prefix is the term used for census IDs prior to last term (lst_trm)
print(f"Data File: {data_file_name}")
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

df.head(7)

#%%
# Data cleaning starts here. 5_29_26
#  CATALOG_NBR '3000H', '3000W', '3000HW' --> '3000'
# UM_CLEVEL_DESCR Drop 'MASTERS'

# 1. Replace '3000H', '3000W', and '3000HW' with '3000' in the CATALOG_NBR column
values_to_replace = ['3000H', '3000W', '3000HW']
df['catalog_nbr'] = df['catalog_nbr'].replace(values_to_replace, '3000')

# 2. Drop any row where UM_CLEVEL_DESCR is 'MASTERS'
df = df[df['um_clevel_descr'] != 'MASTERS']


# %%
# 2. Transform catalog_nbr and create 'class'
# *** Catalog NBR revision needed here.

print("\n--- DIAGNOSTIC: Column Transformation ---")
# Check if catalog_nbr exists after lowercasing
if 'catalog_nbr' in df.columns:
    # Extract exactly 4 digits. Example: '_0110' -> '0110', '1014W' -> '1014'
    df['catalog_nbr_clean'] = df['catalog_nbr'].astype(str).str.extract(r'(\d{4})')
    
    # Create 'class' = subject + '_' + cleaned catalog_nbr
    # Using .fillna('0000') in case regex fails to find 4 digits
    df['class'] = df['subject'].astype(str) + '_' + df['catalog_nbr_clean'].fillna('0000')
    
    print("Sample of cleaning logic:")
    print(df[['subject', 'catalog_nbr', 'class']].drop_duplicates().head(31))
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
last_term = '5427' # SP26  last term having enrollment in classes. Fall 2025 = 5343
# note, EMPLIDs come from cenus one term prior to last_term. For last_term='5427' IDs came from census FS25
# note, SQL result is from Fall_25 Census students, degree seeking, um_acad_prog1-4 = BUSNU
# 'BUSNU' in (a.um_acad_prog1, a.um_acad_prog2, a.um_acad_prog3, a.um_acad_prog4)

print(f"\n--- DIAGNOSTIC: Filtering for Term {last_term} ---")

# original pre 4/20
# constant_cols = [
#     'emplid', 'strm', 'term', 'admit_term', 'admit_term_desc', 
#     'um_clevel_descr', 'acad_prog', 'acad_plan', 'acad_subplan',
#     'cum_gpa', 'tot_cumulative', 'tot_hrs_life'
# ]
# dropped acad_prog because it came from the enrollment fc table and is not used.
constant_cols = [
    'emplid', 'strm', 'term', 'admit_term',  
    'um_clevel_descr', 'bus_maj', 
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
    print(f"Unique in strm= {last_term}")
    print(f"Note students who graduate or who are not enrolled in, last_term -1, are not in this set.")

    # 5. Initialize Target Columns
    print("\n--- DIAGNOSTIC: Initializing Target Columns ---")
    for target in target_classes:
        df2[target] = 0
        df2[target + '_SEM_ELI'] = 0

#%%
    print(f"Total columns in df2 now: {len(df2.columns)}")
    print("\n--- PREVIEW OF df2 STRUCTURE ---")
    print(df2.head(15))

#%%
    print(f"Total columns in df now: {len(df.columns)}")
    print("\n--- PREVIEW OF df STRUCTURE ---")
    print(df.head(15))

#%%
# check to see the last_term
print(f"This is the last_term = {last_term}")

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
# *** may need to change query to put value in for transfer classes if float(row['grd_pts_per_unit']) > 0: # we don't do this 6/8/26
for idx, row in df_sorted.iterrows():
    sid = str(row['emplid'])
    current_class = str(row['class']) # This is now guaranteed Uppercase
    
    # Matching check
    if sid in df2.index and current_class in df2.columns:
        # 5/23/26 do not use grade points becuase some classes post grades early in current term.
        # New check if strm < last_term (already taken)
        # --- START REVISED GRADE & TERM LOGIC ---
        # 1. First Check: Student took but failed the class (Assign 0)
        if float(row['grd_pts_per_unit']) == 0 and str(row['crse_grade_input']).upper() == 'F':
            df2.at[sid, current_class] = 0
            
        # 2. Second Check: Class taken in a semester prior to last_term (Assign 2)
        elif int(row['strm']) < int(last_term):
            df2.at[sid, current_class] = 2
            
        # 3. Third Check: Class taken during the last_term (Assign 1)
        elif int(row['strm']) == int(last_term):
            df2.at[sid, current_class] = 1
        # --- END REVISED GRADE & TERM LOGIC ---
        
        
        # # OLD Check grade points
        # if float(row['grd_pts_per_unit']) > 0:
        #     df2.at[sid, current_class] = 2

        # # Have to manage an 'F' grade that results in 0 for grade points (0 for grades points also 
        # # recorded for a class that a student is enrolled in during current semester but not completed.
        # # This is the final condition where df2.at[sid, current_class] = 1)    
        # # --- START ADDITION: Check for failing grade to mark as taken (2) ---
        # elif float(row['grd_pts_per_unit']) == 0 and str(row['crse_grade_input']).upper() == 'F':
        #     df2.at[sid, current_class] = 2
        # # --- END ADDITION ---
        
        # else:
        #     df2.at[sid, current_class] = 1

# 7. Reset index
df2.reset_index(inplace=True)

#%%
print(f"Total columns in df2 now: {len(df2.columns)}")
print("\n--- PREVIEW OF df2 STRUCTURE ---")
print(df2.head(15))

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
# output_filename = "df2_populated_wide_FS25census.csv"
# output_path = output_dir / output_filename

# 2. Ensure the output directory exists
# output_dir.mkdir(parents=True, exist_ok=True)

# 3. Export to CSV (index=False avoids adding an extra ID column)
# df2.to_csv(output_path, index=False)

# print(f"--- Export Complete ---")
# print(f"File saved to: {output_path}")
#%%
print(target_classes)
print("This is the end of stepping through the code for 5/23/26")



      
# %%
# --- Step 3: Semester Eligibility Counting (Revised with Set Isolation) ---
# -- The below gap counting excludes any summer semester.  
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
                
                # --- NEW ADDITIONS START ---
                # Requirement: Student must be a Business Major (ACCT_BSACC or BUSAD_BSBA)
                # -- 6/9/26 Robert says do not include ACCT_BSACC for Bus_Maj relating to BUS_AD_3500
                elif target_class == 'BUS_AD_3500':
                    # Access the pre-calculated flag from your SQL query
                    # We check if any value in the bus_maj column for this group is 1
                    if term_rows['bus_maj'].iloc[0] == 1:
                        is_eligible = True

                # Requirement: TOT_CUMULATIVE >= 24
                elif target_class == 'MANGMT_3300' and current_credits >= 24:
                    is_eligible = True
                
                # Requirement: TOT_CUMULATIVE >= 102 AND MANGMT_3000, MRKTNG_3000, FINANC_3000 completed
                elif target_class == 'MANGMT_4970':
                    c1 = (current_credits >= 102)
                    c2 = 'MANGMT_3000' in completed_courses
                    c3 = 'MRKTNG_3000' in completed_courses
                    c4 = 'FINANC_3000' in completed_courses
                    if all([c1, c2, c3, c4]): is_eligible = True
                # --- NEW ADDITIONS END ---

                elif target_class == 'FINANC_3000':
                    c1 = (current_credits >= 45)
                    c2 = ('STAT_2500' in completed_courses or ('STAT_2200' in completed_courses and any(s in completed_courses for s in ['STAT_1200', 'STAT_1300', 'STAT_1400'])))
                    c3 = any(e in completed_courses for e in ['ECONOM_1014', 'ABM_1041'])
                    c4 = any(e in completed_courses for e in ['ECONOM_1015', 'ECONOM_1051', 'ABM_1042'])
                    c5 = any(a in completed_courses for a in ['ACCTCY_2027', 'ACCTCY_2037', 'ACCTCY_2137'])
                    if all([c1, c2, c3, c4, c5]): is_eligible = True
                
                if is_diag and is_eligible:
                    print(f"  >> Became eligible at end of term {term}")

# --- MODIFICATION FOR CASE 3 ---
        # If the loop finished naturally without hitting a 'break', the student never took the class.
        # If they were eligible by the end of that final term, increment by 1 for the elapsing term.
        # (This mimics Case 2's logic for inclusion of the final evaluated sequence, matching the rules for summer exclusion if applicable).
        else:
            if is_eligible:
                if unique_terms: # Safety check to ensure student has history
                    last_term = unique_terms[-1]
                    if not str(last_term).endswith('35'):
                        count_term += 1
                        if is_diag:
                            print(f" [CASE 3 ADJUSTMENT] Student never took class but was eligible through final term: {last_term}. Counter bumped to: {count_term}")
        # --- END OF MODIFICATION ---


        # Final store
        col_name = target_class + '_SEM_ELI'
        if col_name in df2.columns:
            df2.at[student_id, col_name] = count_term

df2.reset_index(inplace=True)
print("Updated all eligibility counters.")
df2.head()

#%%
# Final export to the output directory
outfile = 'df2_eli_ct_' + cen_trm + '_' + lst_trm + '.csv'
df2.to_csv(output_dir / outfile, index=False)
print(f"Success! Final data saved to: {output_dir / outfile}")

#%%
df2.head(15)
#%%
# Build the classifier here --- ------------------------------------------------------------------

# 1. Create df3 by filtering rows where MANGMT_3000 is '0' or '1'
# (Using .isin covers both string versions as requested; you can add [0, 1] if they are integers)
# df3 = df2[df2['MANGMT_3000'].isin([0, 1])].copy()
df3 = df2[(df2['MANGMT_3000'].isin([0, 1])) & (df2['MANGMT_3000_SEM_ELI'] >= 1)].copy()
# 2. Split into target variable y
y = df3['MANGMT_3000']
# 3. Split into feature matrix X
X = df3[['CUM_GPA', 'TOT_CUMULATIVE', 'MANGMT_3000_SEM_ELI']]
# X = df3[['CUM_GPA', 'MANGMT_3000_SEM_ELI']]
X.head()

#%%
y.head()

#%%
X.describe()

#%%
# Build and score a Logistic Regression Model
from sklearn.linear_model import LogisticRegression
model = LogisticRegression(max_iter=5000)
model.fit(X, y)
model.score(X, y)  # Fit score .813 with eli = 0. With eil >=1 0.671  
# Our model predicted correctly whether students would take MGMT_3000 in 81% of the cases.

#%%
model.coef_   # array([[-0.5317906 ,  0.1465955 , -2.31730575]])

#%%
# Split data into a training and test set
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y)

#%%
from sklearn.ensemble import GradientBoostingClassifier
# Gradient Boosting is based on starting with trees that are more general so max_depth is usually lower
model = GradientBoostingClassifier(max_depth=4) 
model.fit(X_train, y_train)
model.score(X_test, y_test) # 0.885 with eli = 0, eli >=1  0.696

#%%

import matplotlib.pyplot as plt

# 1. Generate predictions from your trained model
y_pred = model.predict(X)

# 2. Identify which predictions are correct (True) and incorrect (False)
correct = (y == y_pred)

# MANGMT_3000_SEM_ELI
# 3. Plot correctly classified points (Green circles)
plt.scatter(
    X.loc[correct, 'CUM_GPA'], 
    X.loc[correct, 'TOT_CUMULATIVE'], 
    color='green', 
    label='Correctly Classified', 
    alpha=0.5, 
    edgecolors='w', 
    s=40
)

# 4. Plot incorrectly classified points (Red 'X's)
plt.scatter(
    X.loc[~correct, 'CUM_GPA'], 
    X.loc[~correct, 'TOT_CUMULATIVE'], 
    color='red', 
    label='Incorrectly Classified', 
    alpha=0.8, 
    marker='x', 
    s=50
)

# 5. Add labels, title, and a legend
plt.xlabel('CUM_GPA')
plt.ylabel('TOT_CUMULATIVE')
plt.title('Logistic Regression: Correct vs. Incorrect Classifications')
plt.legend(loc='best')
plt.tight_layout()

# 6. Save the plot to a file
plt.savefig('classification_results.png', dpi=300)

#%%
# MANGMT_3000_SEM_ELI
# 3. Plot correctly classified points (Green circles)
plt.scatter(
    X.loc[correct, 'CUM_GPA'], 
    X.loc[correct, 'MANGMT_3000_SEM_ELI'], 
    color='green', 
    label='Correctly Classified', 
    alpha=0.5, 
    edgecolors='w', 
    s=40
)

# 4. Plot incorrectly classified points (Red 'X's)
plt.scatter(
    X.loc[~correct, 'CUM_GPA'], 
    X.loc[~correct, 'MANGMT_3000_SEM_ELI'], 
    color='red', 
    label='Incorrectly Classified', 
    alpha=0.8, 
    marker='x', 
    s=50
)

# 5. Add labels, title, and a legend
plt.xlabel('CUM_GPA')
plt.ylabel('MANGMT_3000_SEM_ELI')
plt.title('Logistic Regression: Correct vs. Incorrect Classifications')
plt.legend(loc='best')
plt.tight_layout()

# 6. Save the plot to a file
plt.savefig('classification_results_ELI.png', dpi=300)

#%%
# Fine Tune Models -- In particular Gradient Boosting Classifier
# Split classification data - use a random state for consistency
X2_train, X2_test, y2_train, y2_test = train_test_split(X, y, random_state=0)
# Stratify the data, which means keep it balanced
from sklearn.model_selection import StratifiedKFold
skfold = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)

#%%
# Show confusion matrix and classification report for details on precision/recall
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.ensemble import GradientBoostingClassifier
model = GradientBoostingClassifier(random_state=0)
model.fit(X2_train, y2_train)
y2_pred = model.predict(X2_test)
print(confusion_matrix(y2_test, y2_pred))
print(classification_report(y2_test, y2_pred))


#%%
# GridSearchCV searches all possible parameters and chooses the combinations with the best score
from sklearn.model_selection import GridSearchCV

# Here is a customized function to find the best scores - note the scoring is recall, and cv is skfold as defined earlier.
def grid_search(params, clf=model):
    grid_clf = GridSearchCV(clf, params, scoring='recall', cv=skfold)
    grid_clf.fit(X2_train, y2_train)
    best_params = grid_clf.best_params_
    print("Best params:", best_params)
    best_score = (grid_clf.best_score_)
    print("Best score:", best_score)

#%%
# We start by modifying just max_depth, and n_estimaters - it will search  6*3=18 different combinations 
model = GradientBoostingClassifier(random_state=0)
grid_search({'max_depth':[1, 2, 3, 4, 6, 8],
            'n_estimators':[50, 100, 200]}) # with an average of 100 trees - this is 18*100=1800 ML models being built!
# Best params: {'max_depth': 3, 'n_estimators': 50} 
# Best score: 0.8936170212765957

# 'subsample':[0.4, 0.6], # percentage of rows to use per tree
# 'min_samples_split':[2, 3], # number of rows required before a split must be made
#'learning_rate':[0.001, 0.01, 0.1], # rate at which model "learns", how quickly it steps toward minimum errors
#'max_depth':[1, 2, 3], # number of splits the tree makes
#'n_estimators':[25, 50] # n_estimators, total number of trees, is often better used later

# WARNING - You must be carefuly when using GridSearchCV. 
# This code ran fairly quickly because our dataset is super small. 
# GridSearchCV can be very time consuming. A nice alternative is to use RandomizedSearchCV. 
# It will randomly check 10 or any other combinations that you want. 
# When starting with a larger range of parameters, this is usually a better option.

#%%
# RandomizedSearchCV works the same way as GridSearchCV, but checks n (10 by default) random combinations
from sklearn.model_selection import RandomizedSearchCV
def random_search(params, clf=model):
    grid_clf = RandomizedSearchCV(clf, params, scoring='recall', cv=skfold, n_iter=10, random_state=0)
    grid_clf.fit(X2_train, y2_train)
    best_params = grid_clf.best_params_
    print("Best params:", best_params)
    best_score = (grid_clf.best_score_)
    print("Best score:", best_score)

#%%
# the following is a reasonable starting sample of params for a randomized search
model = GradientBoostingClassifier(random_state=0)
random_search(params={'subsample':[0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1], # percentage of rows to use per tree
       'min_samples_split':[2, 3, 4, 5, 6, 7, 8], # number of rows required before a split must be made
        'learning_rate':[0.001, 0.01, 0.1, 0.2, 0.4, 0.6], # rate at which model "learns", how quickly it steps toward minimum errors
        'max_depth':[1, 2, 3, 4, 5, 6, 8, 10], # number of splits the tree makes
        #'n_estimators':[25, 50, 100, 200, 400] # n_estimators, total number of trees, is often better used later
                     })
# Best params: {'subsample': 0.5, 'min_samples_split': 7, 'max_depth': 2, 'learning_rate': 0.4}
# Best score: 0.8617021276595744

#%%
# Narrow down the parameters and try again
random_search(params={'subsample':[0.4, 0.5, 0.6, 0.7],
       'min_samples_split':[6, 7, 8],
        'learning_rate':[0.01, 0.1, 0.2, 0.4, 0.6],
        'max_depth':[1, 2, 3],
        #'n_estimators':[25, 50, 100, 200, 400]
                     })
# Best params: {'subsample': 0.7, 'min_samples_split': 8, 'max_depth': 3, 'learning_rate': 0.1}
# Best score: 0.874468085106383

#%%
# Narrow down the parameters and try again
random_search(params={'subsample':[0.5, 0.6, 0.7, 0.8],
       'min_samples_split':[7, 8, 9],
        'learning_rate':[0.01, 0.1, 0.2, 0.4],
        'max_depth':[2, 3, 4],
        #'n_estimators':[25, 50, 100, 200, 400]
                     })
# Best params: {'subsample': 0.8, 'min_samples_split': 9, 'max_depth': 3, 'learning_rate': 0.1}
# Best score: 0.8808510638297872

#%%
# Narrow down the parameters and try again
random_search(params={'subsample':[0.6, 0.7, 0.8, 0.9],
       'min_samples_split':[8, 9, 10],
        'learning_rate':[0.01, 0.015, 0.1, 0.2],
        'max_depth':[2, 3, 4],
        #'n_estimators':[25, 50, 100, 200, 400]
                     })
# Best params: {'subsample': 0.8, 'min_samples_split': 8, 'max_depth': 2, 'learning_rate': 0.2}
# Best score: 0.8808510638297872
# This and the one above seem to max out the score.

#%%
# Let's check the confusion matrix and classifation report using the parameters above.
# Show confusion matrix and classification report
model = GradientBoostingClassifier(subsample=0.8, min_samples_split=8, max_depth=2, learning_rate=0.2, random_state=0)
model.fit(X2_train, y2_train)
y2_pred = model.predict(X2_test)
print(confusion_matrix(y2_test, y2_pred))
print(classification_report(y2_test, y2_pred))
# [[189  33]
#  [ 25 121]]
#               precision    recall  f1-score   support

#            0       0.88      0.85      0.87       222
#            1       0.79      0.83      0.81       146

#     accuracy                           0.84       368
#    macro avg       0.83      0.84      0.84       368
# weighted avg       0.84      0.84      0.84       368

#%%
# We can modify our search using the f1-score instead. Recall that f1 is the harmonic balance between precision and recall.
# Combine functions into one with f1 scoring as default parameter
def params_search(params, clf=GradientBoostingClassifier(random_state=0), random=False, scoring='f1'):
    if random:
        grid_clf = RandomizedSearchCV(clf, params, scoring='f1', cv=skfold, n_iter=10, random_state=0)
    else:
        grid_clf = GridSearchCV(clf, params, scoring='f1', cv=skfold)
    grid_clf.fit(X2_train, y2_train)
    best_params = grid_clf.best_params_
    print("Best params:", best_params)
    best_score = (grid_clf.best_score_)
    print("Best score:", best_score)

#%%
# Search params using f1-score
params_search(random=True, params={'subsample':[0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1],
       'min_samples_split':[3, 4, 5, 6, 7, 8, 9],
        'learning_rate':[0.001, 0.01, 0.1, 0.2, 0.4, 0.6],
        'max_depth':[1, 2, 3, 4, 5, 6, 8, 10],
        #'n_estimators':[25, 50, 100, 200, 400]
                     })
# Best params: {'subsample': 0.5, 'min_samples_split': 8, 'max_depth': 2, 'learning_rate': 0.4}
# Best score: 0.8588135178171671

#%%
# Narrow params using f1-score
params_search(random=True, params={'subsample':[0.4, 0.5, 0.6],
       'min_samples_split':[7, 8, 9, 10],
        'learning_rate':[0.2, 0.4, 0.5, 0.6],
        'max_depth':[1, 2, 3, 4],
        #'n_estimators':[25, 50, 100, 200, 400]
                     })
# Best params: {'subsample': 0.6, 'min_samples_split': 10, 'max_depth': 2, 'learning_rate': 0.4}
# Best score: 0.8485958485958486

#%%
# Narrow params using f1-score
params_search(random=True, params={'subsample':[0.5, 0.6, 0.7],
       'min_samples_split':[7, 8, 9, 10, 11],
        'learning_rate':[0.2, 0.3, 0.4, 0.45, 0.5],
        'max_depth':[1, 2, 3],
        #'n_estimators':[25, 50, 100, 200, 400]
                     })
# Best params: {'subsample': 0.6, 'min_samples_split': 8, 'max_depth': 2, 'learning_rate': 0.3}
# Best score: 0.8594534153179658

#%%
# Narrow params using f1-score
params_search(random=True, params={'subsample':[0.5, 0.6, 0.7],
       'min_samples_split':[7, 8, 9],
        'learning_rate':[0.2, 0.25, 0.3, 0.35],
        'max_depth':[1, 2, 3],
        #'n_estimators':[25, 50, 100, 200, 400]
                     })
# Best params: {'subsample': 0.5, 'min_samples_split': 9, 'max_depth': 3, 'learning_rate': 0.2}
# Best score: 0.8602547253641604

#%%
# Now that we are close to the best model, 
# Check all values with gridsearch -- note function above if random is not specified, gridsearch
params_search(params={'subsample':[0.4, 0.5, 0.6],
       'min_samples_split':[9],
        'learning_rate':[.15, 0.2, 0.25],
        'max_depth':[2, 3],
        #'n_estimators':[25, 50, 100, 200, 400]
                     })
# Best params: {'learning_rate': 0.15, 'max_depth': 2, 'min_samples_split': 9, 'subsample': 0.4}
# Best score: 0.8659286419878474

#%%
# Add n_estimators
params_search(params={'subsample':[0.3, 0.4],
       'min_samples_split':[9],
        'learning_rate':[0.1, 0.15, 0.2],
        'max_depth':[1, 2],
        'n_estimators':[10, 25, 50, 100, 200]
                     })
# Best params: {'learning_rate': 0.15, 'max_depth': 2, 'min_samples_split': 9, 'n_estimators': 100, 'subsample': 0.4}
# Best score: 0.8659286419878474

#%%
# Narrow params using f1-score
params_search(params={'subsample':[0.3, 0.4],
       'min_samples_split':[9],
        'learning_rate':[0.1, 0.15, 0.2],
        'max_depth':[1, 2],
        'n_estimators':[50, 100, 150]
                     })
# Best params: {'learning_rate': 0.15, 'max_depth': 2, 'min_samples_split': 9, 'n_estimators': 100, 'subsample': 0.4}
# Best score: 0.8659286419878474
# !!! Model is not changing score.

#%%
# Show confusion matrix and classification report
# For the final model
model = GradientBoostingClassifier(subsample=0.4, min_samples_split=2, max_depth=2, learning_rate=0.15, random_state=0, n_estimators=100)
model.fit(X2_train, y2_train)
y2_pred = model.predict(X2_test)
print(confusion_matrix(y2_test, y2_pred))
print(classification_report(y2_test, y2_pred))
# [[188  34]
#  [ 26 120]]
#               precision    recall  f1-score   support

#            0       0.88      0.85      0.86       222
#            1       0.78      0.82      0.80       146

#     accuracy                           0.84       368
#    macro avg       0.83      0.83      0.83       368
# weighted avg       0.84      0.84      0.84       368
# So slightly better at predicting will not take vs. will take class.

#%%
# Finalize Model
# Generally speaking, models are finalized when there will be no more training/testing in the foreseeable future. 
# Obviously models can be retrained when more data comes in. 
# A couple of helpful steps in finalizing models: 1) Convert data to numpy arrays to avoid the need of labels, and
# 2) Go back and train the model on all the data. Why? We are done training and testing. The more data, the better.
# Convert data to numpy arrays
import numpy as np
X_np = np.array(X)
y_np = np.array(y)

#%%
# Train model on all data as numpy arrays
model = GradientBoostingClassifier(subsample=0.4, min_samples_split=2, max_depth=2, learning_rate=0.15, n_estimators=100)
model.fit(X_np, y_np)

#%%
#Save models using pickle for future use
import pickle

# Save model to local machine
filename = 'final_model.sav'
pickle.dump(model, open(filename, 'wb'))

# Load the model from disk
load_model = pickle.load(open(filename, 'rb'))

# Check model
print(load_model)

#%%
# Show the influence of each column
model.feature_importances_
# array([0.13344161, 0.42887337, 0.43768502])

#%%
# Zip columns and feature_importances_ into dict for greater readability
feature_dict = dict(zip(X.columns, model.feature_importances_))

import operator
# Sort dict by values (as list of tuples)
sorted(feature_dict.items(), key=operator.itemgetter(1), reverse=True)

# [('MANGMT_3000_SEM_ELI', 0.43768502331710085),
#  ('TOT_CUMULATIVE', 0.4288733713510719),
#  ('CUM_GPA', 0.13344160533182728)]

#%%


df.head(10)


#%%
# -- --- Loop over all UL classes and collect model fit scores -- ----------------------------
from sklearn.linear_model import LogisticRegression
import pandas as pd
import matplotlib.pyplot as plt
# --- MODIFICATION: EXPORT PATH ---
from pathlib import Path

# Define and create the specific output directory for your plots
output_directory = Path(r"C:\Users\jhyn9\Documents\ULout\plots")
output_directory.mkdir(parents=True, exist_ok=True) 
# --- END OF MODIFICATION ---

# --- TOGGLE UL CLASSES FOR MODELING ---
# Comment this out if you ever want to revert or use a different list.
target_classes_UL = ['BUS_AD_3500', 'ACCTCY_2036', 'ACCTCY_2037', 'ACCTCY_2258', 
                     'MANGMT_3000', 'MANGMT_3300', 'MANGMT_3540', 'MANGMT_4970', 
                     'FINANC_3000', 'MRKTNG_3000']
# --- END OF MODIFICATION ---

# 1. Initialize a list to store scores for each class
model_results = []

print("Training Logistic Regression models and generating plots for UL classes...")

# 2. Loop through each class dynamically
for target_class in target_classes_UL:
    status_col = target_class
    eli_col = target_class + '_SEM_ELI'
    
    # Check if both required columns exist in df2 to avoid KeyErrors
    if status_col in df2.columns and eli_col in df2.columns:
        
        # DYNAMIC FILTER: Replicates your filtering logic dynamically for the current class
        df3 = df2[(df2[status_col].isin([0, 1])) & (df2[eli_col] >= 1)].copy()
        
        # Calculate never enrolled count
        never_enrolled_count = len(df3[df3[status_col] == 0])
        total_sample_size = len(df3)
        
        # Calculate Pct of Total Sample
        if total_sample_size > 0:
            pct_never_enrolled = (never_enrolled_count / total_sample_size) * 100
        else:
            pct_never_enrolled = 0.0
        
        # Safety check: Ensure we have both classes (0 and 1) and enough data to train a model
        if total_sample_size > 1 and df3[status_col].nunique() == 2:
            
            # Dynamic Target variable y
            y = df3[status_col]
            
            # Dynamic Feature matrix X (Uses the specific eli_col for this class)
            X = df3[['CUM_GPA', 'TOT_CUMULATIVE', eli_col]]
            
            # 3. Build, fit, and score the Logistic Regression Model
            model = LogisticRegression(max_iter=5000)
            model.fit(X, y)
            score = model.score(X, y)
            
            # Get model predictions to determine correct/incorrect classifications
            predictions = model.predict(X)
            correct = (predictions == y)
            
            # Initialize a side-by-side 1 row, 2 column figure layout
            fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(14, 6))
            
            # --- PANEL A: CUM_GPA vs TOT_CUMULATIVE ---
            ax_a.scatter(
                X.loc[correct, 'CUM_GPA'], 
                X.loc[correct, 'TOT_CUMULATIVE'], 
                color='green', label='Correctly Classified', alpha=0.5, edgecolors='w', s=40
            )
            ax_a.scatter(
                X.loc[~correct, 'CUM_GPA'], 
                X.loc[~correct, 'TOT_CUMULATIVE'], 
                color='red', label='Incorrectly Classified', alpha=0.8, marker='x', s=50
            )
            ax_a.set_xlabel('CUM_GPA')
            ax_a.set_ylabel('TOT_CUMULATIVE')
            ax_a.set_title('Panel a: GPA vs Total Cumulative Credits')
            ax_a.legend(loc='best')
            
            # --- PANEL B: CUM_GPA vs DYNAMIC ELI COLUMN ---
            ax_b.scatter(
                X.loc[correct, 'CUM_GPA'], 
                X.loc[correct, eli_col], 
                color='green', label='Correctly Classified', alpha=0.5, edgecolors='w', s=40
            )
            ax_b.scatter(
                X.loc[~correct, 'CUM_GPA'], 
                X.loc[~correct, eli_col], 
                color='red', label='Incorrectly Classified', alpha=0.8, marker='x', s=50
            )
            ax_b.set_xlabel('CUM_GPA')
            ax_b.set_ylabel(eli_col)
            ax_b.set_title(f'Panel b: GPA vs {eli_col}')
            ax_b.legend(loc='best')
            
            # Set Main Title for the whole figure canvas
            plt.suptitle(f'Logistic Regression Classification Analysis: {target_class}', fontsize=14, fontweight='bold')
            plt.tight_layout()
            
            # --- MODIFICATION: SAVE TO SPECIFIC PATH ---
            # Combines the directory path with the dynamic filename
            plot_filename = output_directory / f'classification_results_{target_class}.png'
            plt.savefig(plot_filename, dpi=300)
            # --- END OF MODIFICATION ---
            
            plt.close(fig) # Closes figure window to save system memory
            
            # Append result
            model_results.append({
                'Class': target_class,
                'Model Score (Accuracy)': round(score, 4),
                'Total Sample Size (N)': total_sample_size,
                'Elig Never Enrolled (Status 0)': never_enrolled_count,
                '% Never Enrolled': f"{round(pct_never_enrolled, 2)}%"
            })
        else:
            # Handle edge cases where data is missing or doesn't have both 0 and 1 statuses
            model_results.append({
                'Class': target_class,
                'Model Score (Accuracy)': 'Insuff. Data / Single Class',
                'Total Sample Size (N)': total_sample_size,
                'Elig Never Enrolled (Status 0)': never_enrolled_count,
                '% Never Enrolled': f"{round(pct_never_enrolled, 2)}%"
            })

# 4. Create the final summary DataFrame
scores_df = pd.DataFrame(model_results)

# 5. Display the single consolidated output table
print("\n--- Consolidated Logistic Regression Scores ---")
print(scores_df)

# Optional: Export the final scores to a CSV
scores_df.to_csv(output_dir / 'ul_classes_model_scores.csv', index=False)
#%%




#%%


#%%











#%%

# --- Descriptive Statistics Table with Dynamic 'last_term' Label ---
# --- Step 4: Descriptive Statistics Table with Fixed SD Calculation ---

# 1. Initialize list for statistics
final_stats_list = []

# Define the dynamic column header using the last_term variable
dynamic_col_label = f" Enrolled '{last_term}'"

# --- MODIFICATION: TOGGLE UL CLASSES ONLY ---
# Uncomment the line below to filter the output for ONLY Upper Level (UL) classes.
# Comment it out again if you want to fall back to the original full list of classes.
target_classes_upper = [c.upper() for c in ['BUS_AD_3500', 'ACCTCY_2036', 'ACCTCY_2037', 'ACCTCY_2258', 'MANGMT_3000', 'MANGMT_3300', 'MANGMT_3540', 'MANGMT_4970', 'FINANC_3000', 'MRKTNG_3000']]
# --- END OF MODIFICATION ---

# 2. Iterate through each target class to calculate unique stats
for target_class in target_classes_upper:
    # Set the relevant columns for this iteration
    status_col = target_class              # The enrollment status (0, 1, or 2)
    eli_col = target_class + '_SEM_ELI'    # The eligibility counter
    
    # FILTER: Only include students who:
    # A) Have NOT taken/attempted the class (status == 0)
    # B) HAVE been eligible for at least 1 term (eli_col > 0)
    subset = df2[(df2[status_col] == 0) & (df2[eli_col] > 0)]
    
    # SUBSET FOR DYNAMIC COLUMN: Students currently enrolled. Term after Census term.
    # Few students are enrolled but missing a few prereq, econ 1014, Stat, etc.
    last_term_eligible_subset = df2[(df2[status_col] == 1) & (df2[eli_col] >= 0)]
    
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
        'Mean Terms Eligible': round(class_mean, 2),
        'SD': round(class_sd, 2) if not pd.isna(class_sd) else 0,
        'Elig Never Enrolled': class_count,
        dynamic_col_label: len(last_term_eligible_subset)
    })

# 5. Create the final statistics DataFrame
stats_df = pd.DataFrame(final_stats_list)

# 6. Display the table to verify unique SD values
print(f"\n--- Descriptive Statistics: Analysis for Term {last_term} ---")
print(stats_df)

#%%
# 7. Export the table to your output directory
stats_df.to_csv(output_dir / 'descriptive_stats_FS25.csv', index=False)

#%%
# END CODE REVIEW 5_25_26
# *********************************************************


#%%
# --- Exporting Class-Specific Eligibility Tables ---

# 1. Define the structural columns we want to keep in every table
# These are the metadata columns (emplid, strm, etc.)
metadata_cols = [
    'EMPLID', 'STRM', 'TERM', 'ADMIT_TERM', 
    'UM_CLEVEL_DESCR', 'BUS_MAJ',
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
    'um_clevel_descr', 'acad_plan', 'acad_subplan',
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