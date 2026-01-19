-- Build out query to identify first year business students 
-- n=1616 UGRD and GRAD
-- n=1541 UGRD
SELECT 
      EMPLID
    , UM_ACAD_GRP_DESCR
    , UM_ACAD_ORG_DESCR
    , INSTITUTION
    , ACAD_CAREER
    , STRM
    , DESCR_TERM
    , FIRST_NAME
    , LAST_NAME
    , REC_HS_GRAD
    , UM_DEG_SEEKING
    , ADMIT_TYPE
    , ADMIT_TERM
    , UM_DEGREEST_DESCR
    , UM_CLEVEL
    , UM_CLEVEL_DESCR
    , UNT_TERM_TOT
    , UNT_AUDIT
    , ACADEMIC_LOAD
    , FTE
    , TOT_BILLING_HRS
    , ACAD_PROG_PRIMARY
    , UM_ACAD_PROG1
    , UM_ACAD_PLAN1
    , UM_ACAD_SUB_PLAN1
    , UM_ACAD_PROG2
    , UM_ACAD_PLAN2
    , LOCATION
    , UM_C_CAMPUS
    , HS_GRAD_DT
    , CLASS_SIZE
    , CLASS_RANK
    , UM_HS_PCNT
    , UM_CENSUS_DT
    , UM_SATR_MATH
    , UM_SATR_READ_WR
    , UM_VETERAN
    , UM_ONLINE_LEARNER
    , UM_FIRST_GEN
    , UM_TEST_OPTIONAL
FROM sa_c.ps_um_census_enrl
WHERE strm = '5343'         -- 5343 = FS25
--    AND admit_term = '5343' -- 5343 = FS25
    AND acad_career = 'UGRD'
    AND um_deg_seeking = 'Y' -- Census includes non degree seeking students.
    AND um_acad_grp_descr = 'College of Business' --  for just Trulaske
--    AND emplid = '14509672'
ORDER BY ADMIT_TERM DESC
FETCH FIRST 50 ROWS ONLY;

-- --- --- --- 
-- Build out Query to list courses for one individual

10314423 -- FTC Freshman started FS25
10318624 -- TRE student Junior started FS25
14509672 -- FTC Freshman started FS25 Listed as 15 hours in census
14509711 -- 
WHERE emplid = '14467956' -- TRE student Sophpmore started FS25

SELECT a.* -- CLASS_NBR IN('52202', '53855')
     , b.subject
     , b.catalog_nbr
     , b.class_nbr
FROM  sa_c.sa_stdnt_enrl_Fc a LEFT JOIN sa_c.sa_class_dm b
        ON a.class_nbr = b.class_nbr 
--WHERE a.emplid = '14467956' -- Freshman transfered out after first Semester
WHERE a.emplid = '14467602' -- JUNIOR
AND a.STRM = '5343' -- FS25
;



-- Below query gives you student schedules, grades, cum_gpa, hours from their start to last time stamp.
-- A subset of this table could be used to show when students change from BUSNU to JOURN or other.
-- We now need to get a list of EMPLID's for the business students of interest. Perhaps use
-- the census table and STRM current semester and  AND um_acad_grp_descr = 'College of Business' --  for just Trulaske
-- Need to build in 'ADMIT_TERM' from census table or other location.
SELECT a.EMPLID
     , a.strm
     , c.term
     , a.last_upd_dt_stmp
     , d.um_clevel_descr  -- Freshman, Sophomore, etc.
     , a.acad_prog        -- BUSNU
     , c.acad_plan        -- BUSAD_BSBA
     , c.acad_subplan     -- FIN_BANK
     , b.subject
     , b.catalog_nbr
     , b.class_nbr
     , a.crse_grade_input
     , a.grd_pts_per_unit
     , a.unt_taken
     , c.unt_taken_prgrss
     , a.grade_points
     , c.cum_gpa
     , c.tot_cumulative    -- Assume total hours taken and in progress.
--     , c.tot_passd_prgrss
     , MAX(c.tot_cumulative) OVER (
        PARTITION BY a.emplid)      AS tot_hrs_life 
FROM  sa_c.sa_stdnt_enrl_Fc a 
    , sa_c.sa_class_dm b
    , mu_sis_mv.students_active_in_prog_by_term_mv c
    , sa_c.ps_um_census_enrl d
    , um_sdsc.mu_4d_adm_appl_dtl_wk0 e
WHERE
        a.stdnt_enrl_status = 'E'     -- These three col required
    and a.enrl_status_reason = 'ENRL' -- to get enrolled courses
    and a.grading_basis_enrl <> 'NON' -- 

    and a.class_nbr = b.class_nbr     -- Link to class table
    and a.strm = b.strm               -- for classes by term.
    
    and a.strm = c.strm               -- Link to CUM_GPA, hours,
    and a.emplid = c.emplid           -- ACAD_PLAN etc.
    
    and a.strm = d.strm               -- Link to UM_CLEVEL_DESCR,
    and a.emplid = d.emplid           -- ACAD_PLAN etc.
    
    and a.strm = e.strm               -- Link to UM_CLEVEL_DESCR,
    and a.emplid = e.emplid           -- ACAD_PLAN etc.
    
-- Below subquery returns full set of census EMPLID for semester of interest.
--    AND a.emplid IN (                 -- Per request from Shannon B use census
--        SELECT distinct emplid 
--        FROM sa_c.ps_um_census_enrl 
--        WHERE strm = '5343' 
--        AND acad_career = 'UGRD'
--        AND um_deg_seeking = 'Y' -- Census includes non degree seeking students.
--        AND um_acad_grp_descr = 'College of Business' --  for just Trulaske
--        AND um_clevel_descr IN('FRESHMAN', 'SOPHOMORE', 'JUNIOR', 'SENIOR') --n=1,337 for F, n=5226 for F,S,J,S
--        )
        
--    and a.emplid IN -- Subquery returns n=5,230 emplids
--    and see the subquery directly below. This will build a set of all Trulaske
-- students with each row being a class they have taken during their entire career
-- from freshmen to seniors. as many as 40 classes  times 5230 students = 209,200 max
 
--and a.emplid = '14467956' -- Freshman transfered out after first Semester
--and a.emplid IN('14467584') -- FRESHMAN
--and a.emplid IN('14467584', '14466324') -- FRESHMAN
--and a.emplid IN('14467078', '14509796') -- FRESHMAN start FS25
-- and a.emplid IN('14467581', '14466268') -- SOPHOMORE
-- and a.emplid IN('14467581', '14466268', '14467014') -- SOPHOMORE
-- and a.emplid = '14467602' -- JUNIOR

--AND a.STRM IN('5343', '5327') -- FS25, SP25
--AND a.STRM IN('5343', '5427') -- FS25, SP26
--AND a.STRM IN('5343') -- FS25
ORDER BY a.strm;

-- --- END --- -- 
AND a.emplid IN (
    SELECT distinct emplid 
    FROM sa_c.ps_um_census_enrl 
    WHERE strm = '5343' 
    AND acad_career = 'UGRD'
    AND um_deg_seeking = 'Y' -- Census includes non degree seeking students.
    AND um_acad_grp_descr = 'College of Business' --  for just Trulaske
    AND um_clevel_descr = 'FRESHMAN' --n=1,337
    ;
FETCH FIRST 30 ROWS ONLY;
;
)




-- Get Table columns sa_c.sa_stdnt_enrl_Fc
SELECT *
FROM sa_c.sa_stdnt_enrl_Fc
WHERE STRM = '5243'
and emplid = '14467602' -- JUNIOR
FETCH FIRST 20 ROWS ONLY;

-- Get Table columns mu_sis_mv.students_active_in_prog_by_term_mv
SELECT *
FROM mu_sis_mv.students_active_in_prog_by_term_mv
WHERE 
--STRM = '5343'
STRM IN('5343', '5327') -- FS25
--and emplid IN('14467584', '14466324') -- FRESHMAN
--and emplid IN('14467078', '14509796') -- FRESHMAN start FS25
and emplid IN('14467581', '14466268') -- SOPHOMORE
-- and emplid = '14467602' -- JUNIOR
FETCH FIRST 20 ROWS ONLY;


-- Get Table columns um_sdsc.mv_4d_adm_appl_dtl_wk0
--Pull admissions data out for FTC and TRE seperately here
  select distinct e.admit_term_rollup, e.admit_term_rollup_descrshort, e.emplid, 
  e.admit_type, e.um_deg_seeking, 
  e.ever_admit, e.is_deposit_paid, e.is_cancel

  from um_sdsc.mu_4d_adm_appl_dtl_wk0 e
  where 
--  e.admit_term_rollup = '5343' -- Fall 2025 = 5343
   e.um_deg_seeking = 'Y'
  and e.acad_career = 'UGRD'
  and e.admit_type in ('FTC','TRE')
  and e.acad_group = 'CBUSN'
  and a.emplid IN('14467581', '14466268', '14509796') -- SOPHOMORE
  FETCH FIRST 20 ROWS ONLY;


        SELECT distinct emplid 
        FROM sa_c.ps_um_census_enrl 
        WHERE strm = '5343' 
        AND acad_career = 'UGRD'
        AND um_deg_seeking = 'Y' -- Census includes non degree seeking students.
        AND um_acad_grp_descr = 'College of Business' --  for just Trulaske
        AND um_clevel_descr IN('FRESHMAN');, 'SOPHOMORE', 'JUNIOR', 'SENIOR');


-- --- TEST with Inner join --
SELECT a.EMPLID
     , a.strm
     , c.term
     , a.last_upd_dt_stmp
     , d.um_clevel_descr  -- Freshman, Sophomore, etc.
     , a.acad_prog        -- BUSNU
     , c.acad_plan        -- BUSAD_BSBA
     , c.acad_subplan     -- FIN_BANK
     , b.subject
     , b.catalog_nbr
     , b.class_nbr
     , a.crse_grade_input
     , a.grd_pts_per_unit
     , a.unt_taken
     , c.unt_taken_prgrss
     , a.grade_points
     , c.cum_gpa
     , c.tot_cumulative    -- Assume total hours taken and in progress.
--     , c.tot_passd_prgrss
     , MAX(c.tot_cumulative) OVER (
        PARTITION BY a.emplid)      AS tot_hrs_life 
FROM  sa_c.sa_stdnt_enrl_Fc a 
    , sa_c.sa_class_dm b
    , mu_sis_mv.students_active_in_prog_by_term_mv c
    , sa_c.ps_um_census_enrl d
--    , um_sdsc.mu_4d_adm_appl_dtl_wk0 e
WHERE
        a.stdnt_enrl_status = 'E'     -- These three col required
    and a.enrl_status_reason = 'ENRL' -- to get enrolled courses
    and a.grading_basis_enrl <> 'NON' -- 

    and a.class_nbr = b.class_nbr     -- Link to class table
    and a.strm = b.strm               -- for classes by term.
    
    and a.strm = c.strm               -- Link to CUM_GPA, hours,
    and a.emplid = c.emplid           -- ACAD_PLAN etc.
    
    and a.strm = d.strm               -- Link to UM_CLEVEL_DESCR,
    and a.emplid = d.emplid           -- ACAD_PLAN etc.
        
-- Below subquery returns full set of census EMPLID for semester of interest.
    AND a.emplid IN (                 -- Per request from Shannon B use census
        SELECT distinct emplid 
        FROM sa_c.ps_um_census_enrl 
        WHERE strm = '5343' 
        AND acad_career = 'UGRD'
        AND um_deg_seeking = 'Y' -- Census includes non degree seeking students.
        AND um_acad_grp_descr = 'College of Business' --  for just Trulaske
--        AND um_clevel_descr IN('FRESHMAN', 'SOPHOMORE', 'JUNIOR', 'SENIOR') --n=1,337 for F, n=5226 for F,S,J,S
        and emplid IN('14467078', '14466324') -- FRESHMAN
        )
        
--    and a.emplid IN -- Subquery returns n=5,230 emplids
--    and see the subquery directly below. This will build a set of all Trulaske
-- students with each row being a class they have taken during their entire career
-- from freshmen to seniors. as many as 40 classes  times 5230 students = 209,200 max
 
--and a.emplid = '14467956' -- Freshman transfered out after first Semester
--and a.emplid IN('14467584') -- FRESHMAN
--and a.emplid IN('14467584', '14466324') -- FRESHMAN
--and a.emplid IN('14467078', '14509796') -- FRESHMAN start FS25
-- and a.emplid IN('14467581', '14466268') -- SOPHOMORE
-- and a.emplid IN('14467581', '14466268', '14467014') -- SOPHOMORE
-- and a.emplid = '14467602' -- JUNIOR

--AND a.STRM IN('5343', '5327') -- FS25, SP25
--AND a.STRM IN('5343', '5427') -- FS25, SP26
--AND a.STRM IN('5343') -- FS25
ORDER BY a.strm;

-- First test = =29 rows

-- QUERY REWRITE with inner join -- Use this for the final version
WITH Business_Students AS (
    -- This small subset drives the performance of the entire query
    SELECT DISTINCT emplid 
    FROM sa_c.ps_um_census_enrl 
    WHERE strm = '5343'         -- The controling term for entire process.
      AND acad_career = 'UGRD'
      AND um_deg_seeking = 'Y'
      AND um_acad_grp_descr = 'College of Business'
      AND emplid IN ('14467078', '14466324', '14467014', '14467602') -- Remove for full set.
)
SELECT 
    a.emplid,
    a.strm,
    c.term,
    -- Admission Fields (Table E)
    e.admit_term_rollup AS ADMIT_TERM, 
    e.admit_term_rollup_descrshort ADMIT_TERM_DESC, 
--    e.ever_admit, 
--    e.is_deposit_paid, 
--    e.is_cancel,
    a.last_upd_dt_stmp,
    d.um_clevel_descr,
    a.acad_prog,
    c.acad_plan,
    c.acad_subplan,
    b.subject,
    b.catalog_nbr,
    b.class_nbr,
    a.crse_grade_input,
    a.grd_pts_per_unit,
    a.unt_taken,
    c.unt_taken_prgrss,
    a.grade_points,
    c.cum_gpa,
    c.tot_cumulative,
    MAX(c.tot_cumulative) OVER (PARTITION BY a.emplid) AS tot_hrs_life 
FROM sa_c.sa_stdnt_enrl_Fc a
-- The Inner Join below restricts 'a' to only the Business students immediately
-- Filter 'a' immediately by our driving list
INNER JOIN Business_Students bus 
    ON a.emplid = bus.emplid
-- Join the Admission Table (Table E)
INNER JOIN um_sdsc.mu_4d_adm_appl_dtl_wk0 e
    ON a.emplid = e.emplid
--    AND a.strm = e.admit_term_rollup
INNER JOIN sa_c.sa_class_dm b 
    ON a.class_nbr = b.class_nbr 
    AND a.strm = b.strm
INNER JOIN mu_sis_mv.students_active_in_prog_by_term_mv c 
    ON a.strm = c.strm 
    AND a.emplid = c.emplid
INNER JOIN sa_c.ps_um_census_enrl d 
    ON a.strm = d.strm 
    AND a.emplid = d.emplid
WHERE a.stdnt_enrl_status = 'E'
  AND a.enrl_status_reason = 'ENRL'
  AND a.grading_basis_enrl <> 'NON'
  -- Filter Table E to ensure we get the correct "Entry" record
  AND e.um_deg_seeking = 'Y'
  AND e.acad_career = 'UGRD'
  AND e.admit_type IN ('FTC','TRE')
  AND e.acad_group = 'CBUSN'
ORDER BY a.emplid, a.strm;
-- n-29 rows
-- --- END TEST with Inner join --













SELECT *
FROM sa_c.sa_stdnt_enrl_Fc
WHERE STRM = '5243'
and emplid = '14467602' -- JUNIOR
FETCH FIRST 20 ROWS ONLY;
--and a.emplid IN('14467078', '14509796') -- FRESHMAN start FS25
-- and a.emplid IN('14467581', '14466268') -- SOPHOMORE




sa_c.sa_stdnt_enrl_Fc a
a.UNT_ATTEMPTED -- Y = completed, I = inprogress
a.CRSE_GRADE_OFF -- their grade
a.UNT_TAKEN -- hours (add up where UNT_ATTEMPTED = Y)
a.ACAD_PROG --'BUSNU' or other looks to be the major

-- What is the difference between Business major and Business major undeclared?
-- mu_reg.mu_acad_plan_org_group
-- .acad_group = 'CBUSN' AND .acad_plan_type ('MAJ, 'MIN', 'CRT')


-- Business classes by Term
-- n = 365
select distinct 
      b.strm
    , b.strm_sdesc term
    , b.acad_group
    , b.acad_group_ldesc
    , b.subject
    , b.catalog_nbr
    , b.class_nbr
    , b.session_code
    , b.class_section
    , b.class_ldesc
    , count(distinct a.emplid) enrl_tot
    , sum(a.unt_taken) tot_credits
from sa_c.sa_stdnt_enrl_Fc a -- fact table, quantitative data in schema subject 
    -- to the unit of analysis. Each row is a single event/transaction STUDENT.
    , sa_c.sa_class_dm b -- dimension table -- Description qualitative context.
    -- Who what where table,
where 
        a.stdnt_enrl_status = 'E' 
    and a.enrl_status_reason = 'ENRL' 
    and a.strm = b.strm 
    and a.class_nbr = b.class_nbr 
    and a.grading_basis_enrl <> 'NON' 
    and a.strm = '5343'         -- 5343 = FS25 
    and b.acad_group = 'CBUSN'
--    and emplid = '14509672'
group by 
      b.strm
    , b.strm_sdesc
    , b.acad_group
    , b.acad_group_ldesc
    , b.subject
    , b.catalog_nbr
    , b.class_nbr
    , b.session_code
    , b.class_section
    , b.class_ldesc
order by 
      b.strm
    , b.subject
    , b.catalog_nbr
    , b.class_section
;

-- --- Try for a single student
-- Business classes by Term
-- n = 365
select distinct 
      a.*
    , b.strm
    , b.strm_sdesc term
    , b.acad_group
    , b.acad_group_ldesc
    , b.subject
    , b.catalog_nbr
    , b.class_nbr
    , b.session_code
    , b.class_section
    , b.class_ldesc
--    , count(distinct a.emplid) enrl_tot
--    , sum(a.unt_taken) tot_credits
from sa_c.sa_stdnt_enrl_Fc a -- fact table, quantitative data in schema subject 
    -- to the unit of analysis. Each row is a single event/transaction STUDENT.
    , sa_c.sa_class_dm b -- dimension table -- Description qualitative context.
    -- Who what where table,
where 
        a.stdnt_enrl_status = 'E' 
    and a.enrl_status_reason = 'ENRL' 
    and a.strm = b.strm 
    and a.class_nbr = b.class_nbr 
    and a.grading_basis_enrl <> 'NON' 
    and a.strm = '5343'         -- 5343 = FS25 
--    and b.acad_group = 'CBUSN'
    and a.emplid = '14467956'
--group by 
--      b.strm
--    , b.strm_sdesc
--    , b.acad_group
--    , b.acad_group_ldesc
--    , b.subject
--    , b.catalog_nbr
--    , b.class_nbr
--    , b.session_code
--    , b.class_section
--    , b.class_ldesc
order by 
      b.strm
    , b.subject
    , b.catalog_nbr
    , b.class_section
;












SET PAGESIZE 5000; -- Ensure the page size is large enough to show all rows without headers/footers
SELECT
    column_name
FROM
    ALL_TAB_COLUMNS
WHERE
    owner = 'SA_C'                      -- Specify the Schema/Owner in CAPITAL letters
    AND table_name = 'PS_UM_CENSUS_ENRL' -- Specify the Table Name in CAPITAL letters
ORDER BY
    column_id;


-- FROM sa_c.ps_um_census_enrl
SELECT 
      EMPLID
    , UM_ACAD_GRP_DESCR
    , UM_ACAD_ORG_DESCR
    , INSTITUTION
    , ACAD_CAREER
    , STRM
    , DESCR_TERM
    , NAME_SUFFIX
    , FIRST_NAME
    , MIDDLE_NAME
    , LAST_NAME
    , SEX
    , BIRTHDATE
    , AGE
    , AGE_CATEGORY_SR
    , UM_AGE_GROUP_TRANS
    , ETHNIC_GROUP
    , UM_ETHNIC_GRP_TRNS
    , UM_RACEA_HISPA
    , UM_RACEB_NRA
    , UM_RACEC_AMIND
    , UM_RACED_ASIAN
    , UM_RACEE_BLACK
    , UM_RACEF_PACIF
    , UM_RACEG_WHITE
    , UM_RACEH_OTHER
    , UM_ETHNIC_PRIMARY
    , UM_ETHNIC_PRI_DESC
    , RESIDENCY
    , CITIZENSHIP
    , COUNTY
    , STATE
    , COUNTRY
    , REC_HS_GRAD
    , UM_DEG_SEEKING
    , ADMIT_TYPE
    , UM_ADMIT_TYPE_DTL
    , ADMIT_TERM
    , ADM_APPL_CTR
    , UM_AP_CAMPUS
    , UM_HIDEGREE
    , UM_HIDEGREE_DESC
    , UM_DEGREEST
    , UM_DEGREEST_DESCR
    , UM_CLEVEL
    , UM_CLEVEL_DESCR
    , ACAD_LEVEL_BOT
    , UNT_TERM_TOT
    , UNT_AUDIT
    , ACADEMIC_LOAD
    , UM_FTPTOVR
    , FTE
    , TOT_BILLING_HRS
    , ACAD_PROG_PRIMARY
    , UM_ACAD_PROG1
    , UM_ACAD_PLAN1
    , UM_CIP1
    , UM_AC_PL_TYPE1
    , UM_ACAD_SUB_PLAN1
    , UM_ACAD_PROG2
    , UM_ACAD_PLAN2
    , UM_CIP2
    , UM_AC_PL_TYPE2
    , UM_ACAD_SUB_PLAN2
    , UM_ACAD_PROG3
    , UM_ACAD_PLAN3
    , UM_CIP3
    , UM_AC_PL_TYPE3
    , UM_ACAD_SUB_PLAN3
    , UM_ACAD_PROG4
    , UM_ACAD_PLAN4
    , UM_CIP4
    , UM_AC_PL_TYPE4
    , UM_ACAD_SUB_PLAN4
    , UM_VIDEO_ONLY
    , UM_AUDIT_ONLY
    , LOCATION
    , UM_C_CAMPUS
    , UM_PS_TYPE
    , UM_PSSTATE
    , UM_CUMCREDE
    , UM_CRTRAN1E
    , UM_CRTRAN2E
    , SSN1
    , UM_SSTAT1
    , UM_SSN2
    , UM_SSTAT2
    , UM_CBHE_ORIG_TS
    , UM_CBHE_GEO_ORIG
    , UM_MHECPRO
    , HS_GRAD_DT
    , CLASS_SIZE
    , CLASS_RANK
    , UM_HS_PCNT
    , UM_CORE_IND
    , UM_HSENGCRS
    , UM_HSMATCRS
    , UM_HSSSTCRS
    , UM_HSSCICRS
    , UM_HSVPACRS
    , UM_HSFLGCRS
    , UM_FLELECT
    , UM_ACTENG
    , UM_ACTMAT
    , UM_ACTRED
    , UM_ACTSCR
    , UM_ACTCOM
    , UM_SATVER
    , UM_SATMAT
    , FREEZE_REC_FL
    , UM_TRNS_EXT_ORG_ID
    , UM_TRNS_COUNTRY
    , UM_TRNS_FICE_CD
    , UM_HS_EXT_ORG_ID
    , UM_HS_ATP_CD
    , UM_REMATHE
    , UM_REENGLE
    , UM_REREADE
    , UM_REOTHRE
    , UM_NONCOLE
    , UM_PREPMATHE
    , UM_PREPENGLE
    , UM_PREPREADE
    , UM_MANUALYEAR
    , UM_GEODOMI
    , UM_TRANSCHIPEDS
    , UM_DISTANCE
    , UM_MOSIS
    , UM_CENSUS_DT
    , RUNDTTM
    , LOAD_DTTM_PC
    , LASTUPDDTTM_PC
    , ERROR_FLAG_PC
    , UM_SATR_MATH
    , UM_SATR_READ_WR
    , UM_VETERAN
    , UM_ONLINE_LEARNER
    , UM_FIRST_GEN
    , UM_TEST_OPTIONAL
    , UM_FSS_YEAR
    , UM_SFS_YEAR
FROM sa_c.ps_um_census_enrl
;
















































