USE uwc_hr_decision_support;

UPDATE applications
SET ai_summary = 'Alice Chen is a highly ranked frontend candidate with strong React, TypeScript, Node.js and AWS experience. She is suitable for HR review.'
WHERE id = 1;

UPDATE applications
SET ai_summary = 'Daniel Tan has relevant frontend exposure and can be reviewed through the score breakdown.'
WHERE id = 2;

UPDATE applications
SET ai_summary = 'Emma Wilson has frontend skills and can be reviewed through the score breakdown.'
WHERE id = 6;

UPDATE applications
SET ai_summary = 'Hafiz Ismail has relevant skills and can be reviewed through the score breakdown.'
WHERE id = 108;
