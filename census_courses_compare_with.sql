
-- 1/23/26
-- There’s such function that you can check the student’s prerequisites for a course. 
-- The code below pulls all the business courses a student has completed, including 
-- the transfer coursework and test credit. You may need to modify the code to 
-- make it work for your purposes.

select distinct strm, emplid, crse_id, subject, catalog_nbr, crse_grade_off, stdnt_enrl_status, enrl_status_reason
from ((select distinct a.emplid, b.crse_id, b.subject, b.catalog_nbr, a.crse_grade_off, a.strm, a.stdnt_enrl_status, a.enrl_status_reason
from sa_c.sa_stdnt_enrl_fc a, sa_c.sa_class_dm b
where a.stdnt_enrl_status = 'E' and
    a.enrl_status_reason = 'ENRL' and
    a.repeat_code <> 'NING' and
    a.grading_basis_enrl <> 'NON' and
    a.strm = b.strm and
    a.class_nbr = b.class_nbr and
    b.subject in ('BUS_AD', 'MANGMT', 'MRKTNG', 'FINANC', 'ACCTCY'))
union
(select distinct a.emplid, b.crse_id, b.subject, b.catalog_nbr, a.crse_grade_off, a.articulation_term, '' stdnt_enrl_status, '' enrl_status_reason
from sa_c.sa_trns_crse_dtl_fc a, sa_c.sa_class_dm b
where a.trnsfr_stat in ('Y', 'P') and
    a.CRSE_GRADE_OFF IN ('A+','A','A-','B+','B','B-','C+','C','C-','S') and
    a.crse_id = b.crse_id and
    b.subject in ('BUS_AD', 'MANGMT', 'MRKTNG', 'FINANC', 'ACCTCY'))
union
(select distinct a.emplid, b.crse_id, b.subject, b.catalog_nbr, a.crse_grade_off, a.articulation_term, '' stdnt_enrl_status, '' enrl_status_reason
from sa_c.sa_trns_test_dtl_fc a, sa_c.sa_class_dm b
where a.trnsfr_stat in ('Y', 'P') and
    --a.CRSE_GRADE_OFF IN ('A+','A','A-','B+','B','B-','C+','C','C-','S') and
    a.crse_id = b.crse_id and
    b.subject in ('BUS_AD', 'MANGMT', 'MRKTNG', 'FINANC', 'ACCTCY')))
where strm >= '3543'
;
-- --- --
-- Start here with this
-- formatted version of above.
SELECT DISTINCT
    strm
  , emplid
  , crse_id
  , subject
  , catalog_nbr
  , crse_grade_off
  , stdnt_enrl_status
  , enrl_status_reason
FROM (
    (
        SELECT DISTINCT
            a.emplid
          , b.crse_id
          , b.subject
          , b.catalog_nbr
          , a.crse_grade_off
          , a.strm
          , a.stdnt_enrl_status
          , a.enrl_status_reason
        FROM
            sa_c.sa_stdnt_enrl_fc a
          , sa_c.sa_class_dm b
        WHERE
            a.stdnt_enrl_status = 'E'
            AND a.enrl_status_reason = 'ENRL'
            AND a.repeat_code <> 'NING'
            AND a.grading_basis_enrl <> 'NON'
            AND a.strm = b.strm
            AND a.class_nbr = b.class_nbr
            AND b.subject IN ('BUS_AD', 'MANGMT', 'MRKTNG', 'FINANC', 'ACCTCY')
    )
    UNION
    (
        SELECT DISTINCT
            a.emplid
          , b.crse_id
          , b.subject
          , b.catalog_nbr
          , a.crse_grade_off
          , a.articulation_term
          , '' AS stdnt_enrl_status
          , '' AS enrl_status_reason
        FROM
            sa_c.sa_trns_crse_dtl_fc a
          , sa_c.sa_class_dm b
        WHERE
            a.trnsfr_stat IN ('Y', 'P')
            AND a.CRSE_GRADE_OFF IN ('A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'S')
            AND a.crse_id = b.crse_id
            AND b.subject IN ('BUS_AD', 'MANGMT', 'MRKTNG', 'FINANC', 'ACCTCY')
    )
    UNION
    (
        SELECT DISTINCT
            a.emplid
          , b.crse_id
          , b.subject
          , b.catalog_nbr
          , a.crse_grade_off
          , a.articulation_term
          , '' AS stdnt_enrl_status
          , '' AS enrl_status_reason
        FROM
            sa_c.sa_trns_test_dtl_fc a
          , sa_c.sa_class_dm b
        WHERE
            a.trnsfr_stat IN ('Y', 'P')
            -- AND a.CRSE_GRADE_OFF IN ('A+','A','A-','B+','B','B-','C+','C','C-','S')
            AND a.crse_id = b.crse_id
            AND b.subject IN ('BUS_AD', 'MANGMT', 'MRKTNG', 'FINANC', 'ACCTCY')
    )
)
WHERE
    strm >= '3543' -- Fall 2025
AND EMPLID IN('14467584') -- FRESHMAN
;

