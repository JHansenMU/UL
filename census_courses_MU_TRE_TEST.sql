WITH Business_Students AS (
    -- Driving set: Identifies the target population
    SELECT DISTINCT emplid
    FROM sa_c.ps_um_census_enrl 
    WHERE strm = '5343'  --Enter the Reference Term Here (5343 = FS25)
      AND um_deg_seeking = 'Y'
      AND (um_acad_prog1 = 'BUSNU' 
        OR um_acad_prog2 = 'BUSNU' 
        OR um_acad_prog3 = 'BUSNU' 
        OR um_acad_prog4 = 'BUSNU')
       AND emplid = '14404855' -- Uncomment for testing
),

Course_Catalog_Lookup AS (
    -- This prevents the Cartesian product by getting a unique mapping of Crse ID to Subject
    SELECT crse_id
    , subject
    , catalog_nbr
--    , MAX(subject_ldesc) as subject_ldesc
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
        , a.acad_prog
        , a.crse_grade_input
        , a.grd_pts_per_unit
        , a.unt_taken
        , a.grade_points
        , a.class_nbr
        , 'MU Course' AS COURSE_SOURCE -- <--- SOURCE FLAG
    FROM sa_c.sa_stdnt_enrl_fc a
    INNER JOIN Business_Students bus ON a.emplid = bus.emplid
    INNER JOIN sa_c.sa_class_dm b ON a.class_nbr = b.class_nbr AND a.strm = b.strm
    WHERE a.stdnt_enrl_status = 'E' 
      AND a.enrl_status_reason = 'ENRL'
      AND a.strm >= '3543' -- All Terms

    UNION ALL -- Using UNION ALL + DISTINCT later is often faster than UNION early

    -- 2. Transfer Courses (Join to Lookup, NOT the full class_dm)
    SELECT 
        a.emplid
        , a.crse_id
        , l.subject
        , l.catalog_nbr
        , a.crse_grade_off
        , a.articulation_term as strm
        , '' as acad_prog
        , '' as crse_grade_input
        , NULL -- grd_pts_per_unit
        , NULL -- unt_taken
        , NULL -- grade_points 
        , NULL -- class_nbr
        , 'TRE Course' AS COURSE_SOURCE -- <--- SOURCE FLAG
    FROM sa_c.sa_trns_crse_dtl_fc a
    INNER JOIN Business_Students bus ON a.emplid = bus.emplid
    INNER JOIN Course_Catalog_Lookup l ON a.crse_id = l.crse_id
    WHERE a.trnsfr_stat IN ('Y', 'P')
      AND a.CRSE_GRADE_OFF IN ('A+','A','A-','B+','B','B-','C+','C','C-','S')

    UNION ALL

    -- 3. Test Credits
    SELECT 
        a.emplid
        , a.crse_id
        , l.subject
        , l.catalog_nbr
        , a.crse_grade_off
        , a.articulation_term as strm
        , '' as acad_prog
        , '' as crse_grade_input
        , NULL -- grd_pts_per_unit
        , NULL -- unt_taken
        , NULL -- grade_points 
        , NULL -- class_nbr
        , 'TEST Credit' AS COURSE_SOURCE -- <--- SOURCE FLAG
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
    COALESCE(curr_census.um_clevel_descr, 'TRANS/TEST') AS STUDENT_LEVEL,
    curr_census.um_clevel_descr,
    a.acad_prog,
    c.acad_plan,
    c.acad_subplan,
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
-- JOIN to Census here to get the level for EVERY term in the student's history
LEFT JOIN sa_c.ps_um_census_enrl curr_census 
    ON a.emplid = curr_census.emplid 
    AND a.strm = curr_census.strm
JOIN mu_sis_mv.students_active_in_prog_by_term_mv c ON a.strm = c.strm 
    AND a.emplid = c.emplid
WHERE c.ACAD_PLAN IN ('UNDEC_BUS', 'BUSAD_BSBA', 'ACCT_BSACC')
ORDER BY bus.emplid, a.strm
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


