WITH Business_Students AS (
    -- Driving set: Identifies the target population
    SELECT DISTINCT emplid
    FROM sa_c.ps_um_census_enrl 
--    WHERE strm = '5343'  --Enter the Reference Term Here (5343 = FS25) For SP26 enroll
    WHERE strm = '5243'  --Enter the Reference Term Here (5243 = FS24) For SP25 enroll
      AND um_deg_seeking = 'Y'
      AND (um_acad_prog1 = 'BUSNU' 
        OR um_acad_prog2 = 'BUSNU' 
        OR um_acad_prog3 = 'BUSNU' 
        OR um_acad_prog4 = 'BUSNU')
--       AND emplid = '14404855' -- Uncomment for testing
--       AND emplid IN('12581334', '12587176', '12596190', '14407310', '14330940', '14381520','14382621','14399123')
--       AND emplid IN('12581334', '12587176', '12596190', '14407310')
--       AND emplid IN('14382621','14399123','14404855', '14444172') -- last two Seniors with many transfer classes only two that show in end counts.
--       AND emplid IN('12581334')
),

Course_Catalog_Lookup AS (
    -- This prevents the Cartesian product by getting a unique mapping of Crse ID to Subject
    SELECT crse_id
    , subject
    , catalog_nbr
    FROM sa_c.sa_class_dm
    GROUP BY crse_id, subject, catalog_nbr
),

Courses_Taken AS (
    -- 1. MU Enrollment (Specific to Class Number)
    SELECT 
        a.emplid
        , b.crse_id
        , b.subject
        , b.catalog_nbr
        , b.class_section
        , a.crse_grade_off
        , a.strm
        , a.acad_prog
        , a.crse_grade_input
        , a.grd_pts_per_unit
        , a.unt_taken
        , a.grade_points
        , a.class_nbr
        , 'MU' AS COURSE_SOURCE -- <--- SOURCE FLAG
    FROM sa_c.sa_stdnt_enrl_fc a
    INNER JOIN Business_Students bus ON a.emplid = bus.emplid
    INNER JOIN sa_c.sa_class_dm b ON a.class_nbr = b.class_nbr AND a.strm = b.strm
    WHERE a.stdnt_enrl_status = 'E' 
      AND a.enrl_status_reason = 'ENRL'
      AND a.repeat_code <> 'NING'        -- added back    NING means this course is excluded and repeated later on.
      AND a.grading_basis_enrl <> 'NON'  -- added back
      AND a.strm >= '3543' -- All Terms

    UNION ALL -- Using UNION ALL + DISTINCT later is often faster than UNION early

    -- 2. Transfer Courses (Join to Lookup, NOT the full class_dm)
    -- *** 99 for transfer classes if float(row['grd_pts_per_unit']) > 0:
    SELECT 
        a.emplid
        , a.crse_id
        , l.subject
        , l.catalog_nbr
        , '' as class_section
        , a.crse_grade_off
        , a.articulation_term as strm
        , '' as acad_prog
        , '' as crse_grade_input
        , 99 AS grd_pts_per_unit
        , NULL -- unt_taken
        , NULL -- grade_points 
        , NULL -- class_nbr
        , 'TRANSFER' AS COURSE_SOURCE -- <--- SOURCE FLAG
    FROM sa_c.sa_trns_crse_dtl_fc a
    INNER JOIN Business_Students bus ON a.emplid = bus.emplid
    INNER JOIN Course_Catalog_Lookup l ON a.crse_id = l.crse_id
    WHERE a.trnsfr_stat IN ('Y', 'P')
      AND a.CRSE_GRADE_OFF IN ('A+','A','A-','B+','B','B-','C+','C','C-','S')

    UNION ALL

    -- 3. Test Credits
    -- *** 99 for transfer classes if float(row['grd_pts_per_unit']) > 0:
    SELECT 
        a.emplid
        , a.crse_id
        , l.subject
        , l.catalog_nbr
        , '' as class_section
        , a.crse_grade_off
        , a.articulation_term as strm
        , '' as acad_prog
        , '' as crse_grade_input
        , 99 AS grd_pts_per_unit
        , NULL -- unt_taken
        , NULL -- grade_points 
        , NULL -- class_nbr
        , 'TEST' AS COURSE_SOURCE -- <--- SOURCE FLAG
    FROM sa_c.sa_trns_test_dtl_fc a
    INNER JOIN Business_Students bus ON a.emplid = bus.emplid
    INNER JOIN Course_Catalog_Lookup l ON a.crse_id = l.crse_id
    WHERE a.trnsfr_stat IN ('Y', 'P')
),

Earliest_Admit AS (
    SELECT *
    FROM (
        SELECT 
            e.emplid, e.admit_term_rollup, e.admit_term_rollup_descrshort,
            ROW_NUMBER() OVER (PARTITION BY e.emplid ORDER BY e.admit_term_rollup ASC) as row_num
        FROM um_sdsc.mu_4d_adm_appl_dtl_wk0 e
        WHERE e.um_deg_seeking = 'Y'
          AND e.acad_career = 'UGRD'
          AND e.admit_type IN ('FTC','TRE')
          AND e.acad_group = 'CBUSN'
    ) ranked_e
    WHERE row_num = 1
)

SELECT DISTINCT
    bus.emplid,
    a.strm,
    c.term,
    a.COURSE_SOURCE,
    e.admit_term_rollup AS ADMIT_TERM,
    e.admit_term_rollup_descrshort AS ADMIT_TERM_DESC,
    -- Fallback: If no census record for that term, label as Transfer/Test
--    COALESCE(curr_census.um_clevel_descr, 'TRANS/TEST') AS STUDENT_LEVEL,
    curr_census.um_clevel_descr,
    a.acad_prog,
    c.acad_plan,
    c.acad_subplan,
    a.subject,
    a.catalog_nbr,
    a.class_section,
    a.class_nbr,
    a.crse_grade_input,
    a.grd_pts_per_unit,
    a.unt_taken,
    c.unt_taken_prgrss,
    a.grade_points,
    c.cum_gpa,
    c.tot_cumulative,
    MAX(c.tot_cumulative) OVER (PARTITION BY a.emplid) AS tot_hrs_life 
FROM Business_Students bus
JOIN Courses_Taken a ON bus.emplid = a.emplid
LEFT JOIN Earliest_Admit e ON bus.emplid = e.emplid
-- LEFT JOIN to Census here to get the clevel for EVERY term in the student's history
LEFT JOIN sa_c.ps_um_census_enrl curr_census 
    ON a.emplid = curr_census.emplid 
    AND a.strm = curr_census.strm
JOIN mu_sis_mv.students_active_in_prog_by_term_mv c ON a.strm = c.strm 
    AND a.emplid = c.emplid
WHERE c.ACAD_PLAN IN ('UNDEC_BUS', 'BUSAD_BSBA', 'ACCT_BSACC')
-- Extra code below --
--AND a.subject = 'ACCTCY'
--AND a.catalog_nbr = '2036'
AND a.strm = '5427'
ORDER BY a.class_nbr
-- END extra code --
--ORDER BY bus.emplid, a.strm
;




-- TEST CODE BELOW --- --- --- --- --- 
Course_Catalog_Lookup AS (
    -- This prevents the Cartesian product by getting a unique mapping of Crse ID to Subject
    SELECT crse_id
    , subject
    , catalog_nbr
    , MAX(subject_ldesc) as subject_ldesc
    FROM sa_c.sa_class_dm
    GROUP BY crse_id, subject, catalog_nbr
    FETCH FIRST 20 ROWS ONLY;
    
),

SELECT  
crse_id
    , subject
    , catalog_nbr
    , MAX(subject_ldesc) as subject_ldesc
    FROM sa_c.sa_class_dm
    WHERE subject = 'ACCTCY' AND catalog_nbr = '2037'
    GROUP BY crse_id, subject, catalog_nbr
    FETCH FIRST 20 ROWS ONLY;


SELECT  
* 
--crse_id
--    , subject
--    , catalog_nbr
--    , MAX(subject_ldesc) as subject_ldesc
    FROM sa_c.sa_class_dm
    WHERE subject = 'ACCTCY' AND catalog_nbr = '2036'
--    GROUP BY crse_id, subject, catalog_nbr
    FETCH FIRST 20 ROWS ONLY;
    
SELECT * 
FROM sa_c.sa_stdnt_enrl_fc  
--WHERE subject = 'ACCTCY' AND catalog_nbr = '2036'
--    GROUP BY crse_id, subject, catalog_nbr
    FETCH FIRST 20 ROWS ONLY;




-- --- START --- 
-Getting one or multiple courses and busi or non-busi
-- ------------------------------------------------------------------------------------
 SELECT 
        a.emplid
        , b.crse_id
        , b.subject
        , b.catalog_nbr
        , b.class_section
        , a.crse_grade_off
        , a.strm
        , a.acad_prog
        , a.crse_grade_input
        , a.grd_pts_per_unit
        , a.unt_taken
        , a.grade_points
        , a.class_nbr
        , 'MU' AS COURSE_SOURCE -- <--- SOURCE FLAG
    FROM sa_c.sa_stdnt_enrl_fc a
--    INNER JOIN Business_Students bus ON a.emplid = bus.emplid
    INNER JOIN sa_c.sa_class_dm b ON a.class_nbr = b.class_nbr AND a.strm = b.strm
    WHERE a.stdnt_enrl_status = 'E' 
      AND a.enrl_status_reason = 'ENRL'
      AND a.repeat_code <> 'NING'        -- added back    NING means this course is excluded and repeated later on.
      AND a.grading_basis_enrl <> 'NON'  -- added back
      AND a.strm = '5427' -- SP26
      AND subject = 'ACCTCY'
      AND catalog_nbr = '2036'
      AND acad_prog = 'BUSNU'
--      AND a.strm >= '3543' -- All Terms
;
FETCH FIRST 20 ROWS ONLY;


SELECT * 
FROM sa_c.sa_stdnt_enrl_fc a

WHERE a.strm = '5427'
--AND a.subject = 'ACCTCY'
--AND a.catalog_nbr = '2036'
AND acad_prog = 'BUSNU'
   FETCH FIRST 50 ROWS ONLY;

;
UM_ACAD_prog  FROM FROM sa_c.ps_um_census_enrl 

Business class enrollment
FROM sa_c.sa_stdnt_enrl_fc a
UM_ACAD_prog  FROM FROM sa_c.ps_um_census_enrl 
For the set of classes
for a given term
Business student and not business student
Business student = 
(um_acad_prog1 = 'BUSNU' or
um_acad_prog2 = 'BUSNU' or
um_acad_prog3 = 'BUSNU' or
um_acad_prog4 = 'BUSNU')

-- --------------------------------------------------
Can there be any of these:
(um_acad_prog1 = 'BUSNU' or
um_acad_prog2 = 'BUSNU' or
um_acad_prog3 = 'BUSNU' or
um_acad_prog4 = 'BUSNU')
Who are not WHERE c.ACAD_PLAN IN ('UNDEC_BUS', 'BUSAD_BSBA', 'ACCT_BSACC')
-- ----------------------------------------------------






--Program stack
Program plan
program subplan





acad_group = academic unit =CBUSN    Undergrad can have only one acad unit, Graduate programs can have multiple academic units

um_acad_prog1 = 'BUSNU' = program 
ACAD_PLAN = major
ACAD_Subplan

ACAD_PROG1 !=3bus, ACAD_PROG2 !=3bus, ACAD_PROG3 !=3bus, ACAD_PROG4 !=3bus,

select * from cs_c_data_mart.cs_um_enrl_daily -- end of term data

Join on emplid, and term

where strm = '5143' and
um_deg_seeking = 'Y' and
(um_acad_prog1 = 'BUSNU' or
um_acad_prog2 = 'BUSNU' or
um_acad_prog3 = 'BUSNU' or
um_acad_prog4 = 'BUSNU')




