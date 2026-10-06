-- Notes dropped acad_prog from the  sa_c.sa_stdnt_enrl_fc as it does not always match census acad_prog1-4
-- and it is not used in the python code. JH 5/23/26.
-- 
WITH Business_Students AS (
    -- Driving set: Identifies the target population
    SELECT DISTINCT emplid
    FROM sa_c.ps_um_census_enrl 
    WHERE strm = '5343'  --Enter the Reference Term Here (5343 = FS25) For SP26 enroll
                         -- Note you must set the final query  AND a.strm <= '5427' -- SP26
--    WHERE strm = '5243'  --Enter the Reference Term Here (5243 = FS24) For SP25 enroll
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
        , a.crse_grade_off
        , a.strm
 --       , a.acad_prog -- Looks like this != census um_acad_prog1-4  jh5/23/26
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
        , a.crse_grade_off
        , a.articulation_term as strm
 --       , '' as acad_prog
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
        , a.crse_grade_off
        , a.articulation_term as strm
 --       , '' as acad_prog
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

--left outer join this table onto the emplid's from current census.
-- Note this query is useful for finding most all admit terms.
Earliest_Admit AS (
    SELECT *
    FROM (
        SELECT 
            e.emplid
            , e.admit_term
        FROM sa_c.ps_um_census_enrl e
        WHERE e.um_deg_seeking = 'Y'
          AND e.acad_career = 'UGRD'
          AND e.admit_type IN ('FTC','TRE')
         ) --ranked_e
)

SELECT DISTINCT
    bus.emplid,
    a.strm,
    c.term,
    a.COURSE_SOURCE,
    e.admit_term, -- AS ADMIT_TERM,
--    e.admit_term_rollup_descrshort AS ADMIT_TERM_DESC,
    -- Fallback: If no census record for that term, label as Transfer/Test
--    COALESCE(curr_census.um_clevel_descr, 'TRANS/TEST') AS STUDENT_LEVEL,

    curr_census.um_clevel_descr,
--    a.acad_prog,
    -- Logic to determine if they are a Business Major
    -- 6/9/26 Robert says do not include ACCT_BSACC for Bus_Maj relating to BUS_AD_3500
    CASE 
        WHEN (curr_census.UM_ACAD_PLAN1 IN ('ACCT_BSACC', 'BUSAD_BSBA') AND curr_census.UM_AC_PL_TYPE1 = 'MAJ') OR
             (curr_census.UM_ACAD_PLAN2 IN ('ACCT_BSACC', 'BUSAD_BSBA') AND curr_census.UM_AC_PL_TYPE2 = 'MAJ') OR
             (curr_census.UM_ACAD_PLAN3 IN ('ACCT_BSACC', 'BUSAD_BSBA') AND curr_census.UM_AC_PL_TYPE3 = 'MAJ') OR
             (curr_census.UM_ACAD_PLAN4 IN ('ACCT_BSACC', 'BUSAD_BSBA') AND curr_census.UM_AC_PL_TYPE4 = 'MAJ')
        THEN 1 
        ELSE 0 
    END AS Bus_Maj,
--    c.acad_plan, -- may be dupe
--    c.acad_subplan, -- may be dupe
    a.subject,
    a.catalog_nbr,
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
LEFT JOIN sa_c.ps_um_census_enrl curr_census   --put back in to get all of the historical data
    ON a.emplid = curr_census.emplid 
    AND a.strm = curr_census.strm
JOIN mu_sis_mv.students_active_in_prog_by_term_mv c ON a.strm = c.strm 
    AND a.emplid = c.emplid
--WHERE c.ACAD_PLAN IN ('UNDEC_BUS', 'BUSAD_BSBA', 'ACCT_BSACC')

-- test to see if counts match to just (sa_stdnt_enrl_fc and ps_um_census_enrl n=493)   --4/20 n=491
-- This query n=477 (n=592) (removing acad_plan and acad_subplan we remove dupes n=493) --4/20 n=491
--      AND a.subject = 'ACCTCY' 
--      AND a.catalog_nbr = '2036'
      AND a.strm <= '5427' -- SP26
ORDER BY bus.emplid, a.strm
;

-- n=190,996 5/23/26


-- END Query that works for the prediction model -- --------------------------



-- ------------------------------------
-- Then use this for the query of the actual term, in this case SP26
-- Both BUSNU and non Bus students.
-- Note the cognos report has still the withdrawn students.
-- --------------------------------------------------------
--Spring 26 enrollment       
    -- 1. MU Enrollment (Specific to Class Number)
    SELECT   -- Cognos Report: n=719 Because still includes withdrawn students
             -- n=687 (Both BUSNU and All other - sa_stdnt_enrl_fc)
             -- n=526 (BUSNU only               - sa_stdnt_enrl_fc)
             -- n=493 (BUSNU only               - ps_um_census_enrl)             
        a.emplid
        , b.crse_id
        , b.subject
        , b.catalog_nbr
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
      AND b.subject = 'ACCTCY'
      AND a.acad_prog = 'BUSNU'
      AND b.catalog_nbr = '2036'
--      FETCH FIRST 20 ROWS ONLY;
      ;

-- Query that will aggregate enrollment for business classes by term
SELECT             
        a.emplid
        , b.crse_id
        , b.subject
        , b.catalog_nbr
        , a.crse_grade_off
        , a.strm
        , a.acad_prog
        , a.crse_grade_input
        , a.grd_pts_per_unit
        , a.unt_taken
        , a.grade_points
        , a.class_nbr
        , 'MU' AS COURSE_SOURCE 
    FROM sa_c.sa_stdnt_enrl_fc a
    INNER JOIN sa_c.sa_class_dm b ON a.class_nbr = b.class_nbr AND a.strm = b.strm
    WHERE a.stdnt_enrl_status = 'E' 
      AND a.enrl_status_reason = 'ENRL'
      AND a.repeat_code <> 'NING'        
      AND a.grading_basis_enrl <> 'NON'  
      AND a.strm = '5427' -- SP26
      AND b.subject = 'ACCTCY'
      AND a.acad_prog != 'BUSNU' -- n=159
      AND b.catalog_nbr = '2036'
      ;

-- First for ACCTCY_2036 in '5427' -- SP26
SELECT 
    b.subject || '_' || b.catalog_nbr AS CLASS,
    COUNT(a.emplid) AS ENRL_5427
FROM sa_c.sa_stdnt_enrl_fc a
INNER JOIN sa_c.sa_class_dm b 
    ON a.class_nbr = b.class_nbr 
    AND a.strm = b.strm
WHERE a.stdnt_enrl_status = 'E' 
  AND a.enrl_status_reason = 'ENRL'
  AND a.repeat_code <> 'NING'        
  AND a.grading_basis_enrl <> 'NON'  
  AND a.strm = '5427' 
  AND b.subject = 'ACCTCY'
  AND b.catalog_nbr = '2036'
  AND a.acad_prog != 'BUSNU'
GROUP BY 
    b.subject, 
    b.catalog_nbr;
    
-- Next for ACCTCY_2036 in '5427' -- SP26, 5327, 5237, 5127
SELECT 
    b.subject || '_' || b.catalog_nbr AS CLASS,
    COUNT(CASE WHEN a.strm = '5427' THEN a.emplid END) AS ENRL_5427,
    COUNT(CASE WHEN a.strm = '5327' THEN a.emplid END) AS ENRL_5327,
    COUNT(CASE WHEN a.strm = '5227' THEN a.emplid END) AS ENRL_5227,
    COUNT(CASE WHEN a.strm = '5127' THEN a.emplid END) AS ENRL_5127
FROM sa_c.sa_stdnt_enrl_fc a
INNER JOIN sa_c.sa_class_dm b 
    ON a.class_nbr = b.class_nbr 
    AND a.strm = b.strm
WHERE a.stdnt_enrl_status = 'E' 
  AND a.enrl_status_reason = 'ENRL'
  AND a.repeat_code <> 'NING'        
  AND a.grading_basis_enrl <> 'NON'  
  AND a.strm IN ('5427', '5327', '5227', '5127')
  AND b.subject = 'ACCTCY'
  AND b.catalog_nbr = '2036'
  AND a.acad_prog != 'BUSNU'
GROUP BY 
    b.subject, 
    b.catalog_nbr;

-- Add in the average column
WITH EnrollmentCounts AS (
    SELECT 
        b.subject || '_' || b.catalog_nbr AS CLASS,
        COUNT(CASE WHEN a.strm = '5427' THEN a.emplid END) AS ENRL_5427,
        COUNT(CASE WHEN a.strm = '5327' THEN a.emplid END) AS ENRL_5327,
        COUNT(CASE WHEN a.strm = '5227' THEN a.emplid END) AS ENRL_5227,
        COUNT(CASE WHEN a.strm = '5127' THEN a.emplid END) AS ENRL_5127
    FROM sa_c.sa_stdnt_enrl_fc a
    INNER JOIN sa_c.sa_class_dm b 
        ON a.class_nbr = b.class_nbr 
        AND a.strm = b.strm
    WHERE a.stdnt_enrl_status = 'E' 
      AND a.enrl_status_reason = 'ENRL'
      AND a.repeat_code <> 'NING'        
      AND a.grading_basis_enrl <> 'NON'  
      AND a.strm IN ('5427', '5327', '5227', '5127')
      AND b.subject = 'ACCTCY'
      AND b.catalog_nbr = '2036'
      AND a.acad_prog != 'BUSNU'
    GROUP BY 
        b.subject, 
        b.catalog_nbr
)
SELECT 
    CLASS,
    ENRL_5427,
    ENRL_5327,
    ENRL_5227,
    ENRL_5127,
    ROUND((ENRL_5427 + ENRL_5327 + ENRL_5227 + ENRL_5127) / 4.0, 0) AS ENRL_AVE
FROM EnrollmentCounts;

-- Now for all 12 classes
WITH ClassList AS (
    -- Mapping specific pairs and assigning a sequence for ordering
    SELECT 'BUS_AD' AS SUBJ, '1500' AS NBR, 1 AS SEQ FROM DUAL UNION ALL
    SELECT 'BUS_AD', '2500', 2 FROM DUAL UNION ALL
    SELECT 'BUS_AD', '3500', 3 FROM DUAL UNION ALL
    SELECT 'ACCTCY', '2036', 4 FROM DUAL UNION ALL
    SELECT 'ACCTCY', '2037', 5 FROM DUAL UNION ALL
    SELECT 'ACCTCY', '2258', 6 FROM DUAL UNION ALL
    SELECT 'MANGMT', '3000', 7 FROM DUAL UNION ALL
    SELECT 'MANGMT', '3540', 8 FROM DUAL UNION ALL
    SELECT 'MANGMT', '3300', 9 FROM DUAL UNION ALL
    SELECT 'MANGMT', '4970', 10 FROM DUAL UNION ALL
    SELECT 'FINANC', '3000', 11 FROM DUAL UNION ALL
    SELECT 'MRKTNG', '3000', 12 FROM DUAL
),
EnrollmentCounts AS (
    SELECT 
        cl.SUBJ || '_' || cl.NBR AS CLASS,
        cl.SEQ,
        COUNT(CASE WHEN a.strm = '5427' THEN a.emplid END) AS ENRL_5427,
        COUNT(CASE WHEN a.strm = '5327' THEN a.emplid END) AS ENRL_5327,
        COUNT(CASE WHEN a.strm = '5227' THEN a.emplid END) AS ENRL_5227,
        COUNT(CASE WHEN a.strm = '5127' THEN a.emplid END) AS ENRL_5127
    FROM ClassList cl
    INNER JOIN sa_c.sa_class_dm b 
        ON cl.SUBJ = b.subject 
        AND cl.NBR = b.catalog_nbr
    INNER JOIN sa_c.sa_stdnt_enrl_fc a 
        ON a.class_nbr = b.class_nbr 
        AND a.strm = b.strm
    WHERE a.stdnt_enrl_status = 'E' 
      AND a.enrl_status_reason = 'ENRL'
      AND a.repeat_code <> 'NING'        
      AND a.grading_basis_enrl <> 'NON'  
      AND a.strm IN ('5427', '5327', '5227', '5127')
      AND a.acad_prog != 'BUSNU'
    GROUP BY 
        cl.SUBJ, 
        cl.NBR,
        cl.SEQ
)
SELECT 
    CLASS,
    ENRL_5427,
    ENRL_5327,
    ENRL_5227,
    ENRL_5127,
    ROUND((ENRL_5427 + ENRL_5327 + ENRL_5227 + ENRL_5127) / 4.0, 0) AS ENRL_AVE
FROM EnrollmentCounts
ORDER BY SEQ;

--And now add in the totals for the four terms
WITH ClassList AS (
    SELECT 'BUS_AD' AS SUBJ, '1500' AS NBR, 1 AS SEQ FROM DUAL UNION ALL
    SELECT 'BUS_AD', '2500', 2 FROM DUAL UNION ALL
    SELECT 'BUS_AD', '3500', 3 FROM DUAL UNION ALL
    SELECT 'ACCTCY', '2036', 4 FROM DUAL UNION ALL
    SELECT 'ACCTCY', '2037', 5 FROM DUAL UNION ALL
    SELECT 'ACCTCY', '2258', 6 FROM DUAL UNION ALL
    SELECT 'MANGMT', '3000', 7 FROM DUAL UNION ALL
    SELECT 'MANGMT', '3540', 8 FROM DUAL UNION ALL
    SELECT 'MANGMT', '3300', 9 FROM DUAL UNION ALL
    SELECT 'MANGMT', '4970', 10 FROM DUAL UNION ALL
    SELECT 'FINANC', '3000', 11 FROM DUAL UNION ALL
    SELECT 'MRKTNG', '3000', 12 FROM DUAL
),
EnrollmentCounts AS (
    SELECT 
        cl.SUBJ || '_' || cl.NBR AS CLASS,
        cl.SEQ,
        -- Counts excluding BUSNU
        COUNT(CASE WHEN a.strm = '5427' AND a.acad_prog != 'BUSNU' THEN a.emplid END) AS ENRL_5427,
        COUNT(CASE WHEN a.strm = '5327' AND a.acad_prog != 'BUSNU' THEN a.emplid END) AS ENRL_5327,
        COUNT(CASE WHEN a.strm = '5227' AND a.acad_prog != 'BUSNU' THEN a.emplid END) AS ENRL_5227,
        COUNT(CASE WHEN a.strm = '5127' AND a.acad_prog != 'BUSNU' THEN a.emplid END) AS ENRL_5127,
        -- Total counts for all students
        COUNT(CASE WHEN a.strm = '5427' THEN a.emplid END) AS ENRLTOT_5427,
        COUNT(CASE WHEN a.strm = '5327' THEN a.emplid END) AS ENRLTOT_5327,
        COUNT(CASE WHEN a.strm = '5227' THEN a.emplid END) AS ENRLTOT_5227,
        COUNT(CASE WHEN a.strm = '5127' THEN a.emplid END) AS ENRLTOT_5127
    FROM ClassList cl
    INNER JOIN sa_c.sa_class_dm b 
        ON cl.SUBJ = b.subject 
        AND cl.NBR = b.catalog_nbr
    INNER JOIN sa_c.sa_stdnt_enrl_fc a 
        ON a.class_nbr = b.class_nbr 
        AND a.strm = b.strm
    WHERE a.stdnt_enrl_status = 'E' 
      AND a.enrl_status_reason = 'ENRL'
      AND a.repeat_code <> 'NING'        
      AND a.grading_basis_enrl <> 'NON'  
      AND a.strm IN ('5427', '5327', '5227', '5127')
    GROUP BY 
        cl.SUBJ, 
        cl.NBR,
        cl.SEQ
)
SELECT 
    CLASS,
    ENRL_5427,
    ENRL_5327,
    ENRL_5227,
    ENRL_5127,
    ROUND((ENRL_5427 + ENRL_5327 + ENRL_5227 + ENRL_5127) / 4.0, 0) AS ENRL_AVE,
    ENRLTOT_5427,
    ENRLTOT_5327,
    ENRLTOT_5227,
    ENRLTOT_5127
FROM EnrollmentCounts
ORDER BY SEQ;

-- Revised to manage 3000W etc.
WITH ClassList AS (
    SELECT 'BUS_AD' AS SUBJ, '1500' AS NBR, 1 AS SEQ FROM DUAL UNION ALL
    SELECT 'BUS_AD', '2500', 2 FROM DUAL UNION ALL
    SELECT 'BUS_AD', '3500', 3 FROM DUAL UNION ALL
    SELECT 'ACCTCY', '2036', 4 FROM DUAL UNION ALL
    SELECT 'ACCTCY', '2037', 5 FROM DUAL UNION ALL
    SELECT 'ACCTCY', '2258', 6 FROM DUAL UNION ALL
    SELECT 'MANGMT', '3000', 7 FROM DUAL UNION ALL
    SELECT 'MANGMT', '3540', 8 FROM DUAL UNION ALL
    SELECT 'MANGMT', '3300', 9 FROM DUAL UNION ALL
    SELECT 'MANGMT', '4970', 10 FROM DUAL UNION ALL
    SELECT 'FINANC', '3000', 11 FROM DUAL UNION ALL
    SELECT 'MRKTNG', '3000', 12 FROM DUAL
),
EnrollmentCounts AS (
    SELECT 
        cl.SUBJ || '_' || cl.NBR AS CLASS,
        cl.SEQ,
        -- Counts excluding BUSNU
        COUNT(CASE WHEN a.strm = '5427' AND a.acad_prog != 'BUSNU' THEN a.emplid END) AS ENRL_5427,
        COUNT(CASE WHEN a.strm = '5327' AND a.acad_prog != 'BUSNU' THEN a.emplid END) AS ENRL_5327,
        COUNT(CASE WHEN a.strm = '5227' AND a.acad_prog != 'BUSNU' THEN a.emplid END) AS ENRL_5227,
        COUNT(CASE WHEN a.strm = '5127' AND a.acad_prog != 'BUSNU' THEN a.emplid END) AS ENRL_5127,
        -- Total counts for all students
        COUNT(CASE WHEN a.strm = '5427' THEN a.emplid END) AS ENRLTOT_5427,
        COUNT(CASE WHEN a.strm = '5327' THEN a.emplid END) AS ENRLTOT_5327,
        COUNT(CASE WHEN a.strm = '5227' THEN a.emplid END) AS ENRLTOT_5227,
        COUNT(CASE WHEN a.strm = '5127' THEN a.emplid END) AS ENRLTOT_5127
    FROM ClassList cl
    INNER JOIN sa_c.sa_class_dm b 
        ON cl.SUBJ = b.subject 
        AND b.catalog_nbr LIKE cl.NBR || '%' -- Concatenates NBR with wildcard %
    INNER JOIN sa_c.sa_stdnt_enrl_fc a 
        ON a.class_nbr = b.class_nbr 
        AND a.strm = b.strm
    WHERE a.stdnt_enrl_status = 'E' 
      AND a.enrl_status_reason = 'ENRL'
      AND a.repeat_code <> 'NING'        
      AND a.grading_basis_enrl <> 'NON'  
      AND a.strm IN ('5427', '5327', '5227', '5127')
    GROUP BY 
        cl.SUBJ, 
        cl.NBR,
        cl.SEQ
)
SELECT 
    CLASS,
    ENRL_5427,
    ENRL_5327,
    ENRL_5227,
    ENRL_5127,
    ROUND((ENRL_5427 + ENRL_5327 + ENRL_5227 + ENRL_5127) / 4.0, 0) AS ENRL_AVE,
    ENRLTOT_5427,
    ENRLTOT_5327,
    ENRLTOT_5227,
    ENRLTOT_5127
FROM EnrollmentCounts
ORDER BY SEQ;


-- END -----------------------------------------------
-- ---------------------------------------------------


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
