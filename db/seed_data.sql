-- =============================================================================
-- KitmeK Lesson Generation — Idempotent Seed Data
-- Run safely multiple times: ON CONFLICT DO NOTHING throughout.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- GRADES: K, 1, 2, 3, 4, 5
-- ---------------------------------------------------------------------------
INSERT INTO grades (grade_code, grade_name, age_range) VALUES
  ('K', 'Kindergarten', '4-5'),
  ('1', 'Grade 1',      '6-7'),
  ('2', 'Grade 2',      '7-8'),
  ('3', 'Grade 3',      '8-9'),
  ('4', 'Grade 4',      '9-10'),
  ('5', 'Grade 5',      '10-11')
ON CONFLICT (grade_code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- SUBJECTS
--   Grade K  : General Knowledge, Colours
--   Grades 1-5: EVS, Math
-- ---------------------------------------------------------------------------

-- Grade K subjects
INSERT INTO subjects (grade_id, subject_name, subject_code) VALUES
  ((SELECT id FROM grades WHERE grade_code = 'K'), 'General Knowledge', 'GK'),
  ((SELECT id FROM grades WHERE grade_code = 'K'), 'Colours',           'COL')
ON CONFLICT (grade_id, subject_code) DO NOTHING;

-- Grade 1 subjects
INSERT INTO subjects (grade_id, subject_name, subject_code) VALUES
  ((SELECT id FROM grades WHERE grade_code = '1'), 'Environmental Studies', 'EVS'),
  ((SELECT id FROM grades WHERE grade_code = '1'), 'Mathematics',           'MATH')
ON CONFLICT (grade_id, subject_code) DO NOTHING;

-- Grade 2 subjects
INSERT INTO subjects (grade_id, subject_name, subject_code) VALUES
  ((SELECT id FROM grades WHERE grade_code = '2'), 'Environmental Studies', 'EVS'),
  ((SELECT id FROM grades WHERE grade_code = '2'), 'Mathematics',           'MATH')
ON CONFLICT (grade_id, subject_code) DO NOTHING;

-- Grade 3 subjects
INSERT INTO subjects (grade_id, subject_name, subject_code) VALUES
  ((SELECT id FROM grades WHERE grade_code = '3'), 'Environmental Studies', 'EVS'),
  ((SELECT id FROM grades WHERE grade_code = '3'), 'Mathematics',           'MATH')
ON CONFLICT (grade_id, subject_code) DO NOTHING;

-- Grade 4 subjects
INSERT INTO subjects (grade_id, subject_name, subject_code) VALUES
  ((SELECT id FROM grades WHERE grade_code = '4'), 'Environmental Studies', 'EVS'),
  ((SELECT id FROM grades WHERE grade_code = '4'), 'Mathematics',           'MATH')
ON CONFLICT (grade_id, subject_code) DO NOTHING;

-- Grade 5 subjects
INSERT INTO subjects (grade_id, subject_name, subject_code) VALUES
  ((SELECT id FROM grades WHERE grade_code = '5'), 'Environmental Studies', 'EVS'),
  ((SELECT id FROM grades WHERE grade_code = '5'), 'Mathematics',           'MATH')
ON CONFLICT (grade_id, subject_code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- CHAPTERS  (min 2 per subject)
-- ---------------------------------------------------------------------------

-- Grade K — General Knowledge
INSERT INTO chapters (subject_id, chapter_number, chapter_name, chapter_description, sequence_number) VALUES
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = 'K') AND subject_code = 'GK'),
   1, 'Myself and My World', 'Introduction to self, family, and immediate surroundings.', 1),
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = 'K') AND subject_code = 'GK'),
   2, 'Animals Around Us',   'Common domestic and wild animals children encounter.', 2)
ON CONFLICT (subject_id, chapter_number) DO NOTHING;

-- Grade K — Colours
INSERT INTO chapters (subject_id, chapter_number, chapter_name, chapter_description, sequence_number) VALUES
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = 'K') AND subject_code = 'COL'),
   1, 'Colours Around Us',  'Identifying and naming primary and secondary colours in everyday objects.', 1),
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = 'K') AND subject_code = 'COL'),
   2, 'Colours in Nature',  'Observing and describing how colours appear in plants, sky, and animals.', 2)
ON CONFLICT (subject_id, chapter_number) DO NOTHING;

-- Grade 1 — EVS
INSERT INTO chapters (subject_id, chapter_number, chapter_name, chapter_description, sequence_number) VALUES
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '1') AND subject_code = 'EVS'),
   1, 'My Family',        'Understanding family members, roles, and family celebrations.', 1),
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '1') AND subject_code = 'EVS'),
   2, 'My School',        'Exploring the school environment, classroom objects, and school helpers.', 2)
ON CONFLICT (subject_id, chapter_number) DO NOTHING;

-- Grade 1 — Math
INSERT INTO chapters (subject_id, chapter_number, chapter_name, chapter_description, sequence_number) VALUES
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '1') AND subject_code = 'MATH'),
   1, 'Numbers 1 to 10',  'Counting, recognising, and writing numbers 1 through 10.', 1),
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '1') AND subject_code = 'MATH'),
   2, 'Shapes Around Us', 'Identifying basic 2-D shapes: circle, square, triangle, rectangle.', 2)
ON CONFLICT (subject_id, chapter_number) DO NOTHING;

-- Grade 2 — EVS
INSERT INTO chapters (subject_id, chapter_number, chapter_name, chapter_description, sequence_number) VALUES
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '2') AND subject_code = 'EVS'),
   1, 'Our Helpers',      'Community helpers: doctors, teachers, farmers, and how they serve us.', 1),
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '2') AND subject_code = 'EVS'),
   2, 'Food We Eat',      'Sources of food, healthy eating habits, and food groups.', 2)
ON CONFLICT (subject_id, chapter_number) DO NOTHING;

-- Grade 2 — Math
INSERT INTO chapters (subject_id, chapter_number, chapter_name, chapter_description, sequence_number) VALUES
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '2') AND subject_code = 'MATH'),
   1, 'Addition',         'Addition of two-digit numbers with and without carrying.', 1),
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '2') AND subject_code = 'MATH'),
   2, 'Subtraction',      'Subtraction of two-digit numbers with and without borrowing.', 2)
ON CONFLICT (subject_id, chapter_number) DO NOTHING;

-- Grade 3 — EVS  (primary test subject)
INSERT INTO chapters (subject_id, chapter_number, chapter_name, chapter_description, sequence_number) VALUES
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '3') AND subject_code = 'EVS'),
   1, 'Types of Plants',  'Classification of plants into trees, shrubs, herbs, climbers, and creepers.', 1),
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '3') AND subject_code = 'EVS'),
   2, 'Animals and Their Homes', 'Understanding where different animals live and how they adapt.', 2)
ON CONFLICT (subject_id, chapter_number) DO NOTHING;

-- Grade 3 — Math
INSERT INTO chapters (subject_id, chapter_number, chapter_name, chapter_description, sequence_number) VALUES
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '3') AND subject_code = 'MATH'),
   1, 'Multiplication',   'Multiplication tables 1–10, understanding multiplication as repeated addition.', 1),
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '3') AND subject_code = 'MATH'),
   2, 'Division',         'Basic division concepts, relationship between multiplication and division.', 2)
ON CONFLICT (subject_id, chapter_number) DO NOTHING;

-- Grade 4 — EVS
INSERT INTO chapters (subject_id, chapter_number, chapter_name, chapter_description, sequence_number) VALUES
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '4') AND subject_code = 'EVS'),
   1, 'Water and Its Uses',     'Sources of water, water cycle, conservation, and uses in daily life.', 1),
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '4') AND subject_code = 'EVS'),
   2, 'Our Environment',        'Air, soil, and living organisms and their interdependence.', 2)
ON CONFLICT (subject_id, chapter_number) DO NOTHING;

-- Grade 4 — Math
INSERT INTO chapters (subject_id, chapter_number, chapter_name, chapter_description, sequence_number) VALUES
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '4') AND subject_code = 'MATH'),
   1, 'Fractions',              'Introduction to fractions, comparing fractions, adding like fractions.', 1),
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '4') AND subject_code = 'MATH'),
   2, 'Measurement',            'Measuring length, weight, and capacity using standard units.', 2)
ON CONFLICT (subject_id, chapter_number) DO NOTHING;

-- Grade 5 — EVS
INSERT INTO chapters (subject_id, chapter_number, chapter_name, chapter_description, sequence_number) VALUES
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '5') AND subject_code = 'EVS'),
   1, 'The Solar System',       'Planets, the sun, moon phases, and basic astronomy concepts.', 1),
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '5') AND subject_code = 'EVS'),
   2, 'Human Body Systems',     'Major body systems: digestive, respiratory, circulatory — overview.', 2)
ON CONFLICT (subject_id, chapter_number) DO NOTHING;

-- Grade 5 — Math
INSERT INTO chapters (subject_id, chapter_number, chapter_name, chapter_description, sequence_number) VALUES
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '5') AND subject_code = 'MATH'),
   1, 'Large Numbers',          'Reading, writing, and comparing numbers up to crores.', 1),
  ((SELECT id FROM subjects WHERE grade_id = (SELECT id FROM grades WHERE grade_code = '5') AND subject_code = 'MATH'),
   2, 'Decimals',               'Understanding decimals, comparing decimals, adding and subtracting decimals.', 2)
ON CONFLICT (subject_id, chapter_number) DO NOTHING;

-- ---------------------------------------------------------------------------
-- TOPICS  (min 3 for Grade 3 EVS including "Types of Plants")
-- ---------------------------------------------------------------------------

-- Grade K — Colours Around Us
INSERT INTO topics (chapter_id, topic_number, topic_name, topic_description, sequence_number, prerequisites, exclusions, context_narrative) VALUES
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = 'K' AND s.subject_code = 'COL' AND c.chapter_number = 1),
   1, 'Understanding Colours', 'Naming and identifying the six primary and secondary colours.', 1, '[]', '[]',
   'Children explore a colourful garden full of flowers and butterflies.'),
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = 'K' AND s.subject_code = 'COL' AND c.chapter_number = 1),
   2, 'Colours in Nature', 'Spotting colours in plants, sky, animals, and water.', 2, '[1]', '[]',
   'Children continue the garden walk, now looking closely at nature around them.')
ON CONFLICT (chapter_id, topic_number) DO NOTHING;

-- Grade K — Colours in Nature (chapter 2)
INSERT INTO topics (chapter_id, topic_number, topic_name, topic_description, sequence_number, prerequisites, exclusions, context_narrative) VALUES
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = 'K' AND s.subject_code = 'COL' AND c.chapter_number = 2),
   1, 'Rainbow Colours', 'Learning the seven colours of the rainbow and their order.', 1, '[]', '[]',
   'After the rain, children look at the sky and spot a beautiful rainbow.'),
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = 'K' AND s.subject_code = 'COL' AND c.chapter_number = 2),
   2, 'Mixing Colours', 'Discovering new colours by mixing primary colours together.', 2, '[1]', '[]',
   'Children use paint to mix colours and create new shades.')
ON CONFLICT (chapter_id, topic_number) DO NOTHING;

-- Grade 1 — My Family
INSERT INTO topics (chapter_id, topic_number, topic_name, topic_description, sequence_number, prerequisites, exclusions, context_narrative) VALUES
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = '1' AND s.subject_code = 'EVS' AND c.chapter_number = 1),
   1, 'Types of Families', 'Understanding nuclear and joint families and roles of family members.', 1, '[]', '[]',
   'Riya visits her grandparents and observes her large joint family.'),
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = '1' AND s.subject_code = 'EVS' AND c.chapter_number = 1),
   2, 'Family Celebrations', 'Festivals and celebrations that bring families together.', 2, '[1]', '[]',
   'Riya and her family celebrate Diwali together.')
ON CONFLICT (chapter_id, topic_number) DO NOTHING;

-- Grade 2 — Our Helpers
INSERT INTO topics (chapter_id, topic_number, topic_name, topic_description, sequence_number, prerequisites, exclusions, context_narrative) VALUES
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = '2' AND s.subject_code = 'EVS' AND c.chapter_number = 1),
   1, 'Community Helpers', 'Roles of doctors, teachers, police, and farmers in the community.', 1, '[]', '["helpers_in_detail"]',
   'Arjun walks through his town and meets people who help everyone.'),
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = '2' AND s.subject_code = 'EVS' AND c.chapter_number = 1),
   2, 'Helpers at School', 'Understanding the roles of principal, teachers, librarian, and peon.', 2, '[1]', '[]',
   'Arjun arrives at school and learns how everyone works together.')
ON CONFLICT (chapter_id, topic_number) DO NOTHING;

-- Grade 3 — Types of Plants (CRITICAL: min 3 topics, includes "Types of Plants")
INSERT INTO topics (chapter_id, topic_number, topic_name, topic_description, sequence_number, prerequisites, exclusions, context_narrative) VALUES
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = '3' AND s.subject_code = 'EVS' AND c.chapter_number = 1),
   1, 'Trees vs Shrubs',
   'Comparing trees and shrubs: height, trunk structure, lifespan, and examples.',
   1, '[]', '["climbers","creepers"]',
   'Priya walks through a forest and notices different kinds of plants around her.'),
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = '3' AND s.subject_code = 'EVS' AND c.chapter_number = 1),
   2, 'Herbs and Their Uses',
   'Understanding herbs: small soft-stemmed plants used in cooking and medicine.',
   2, '[1]', '["climbers"]',
   'Priya visits her grandmother''s kitchen garden and learns about herb plants.'),
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = '3' AND s.subject_code = 'EVS' AND c.chapter_number = 1),
   3, 'Climbers and Creepers',
   'Learning how climbers use support to grow upward and creepers spread along the ground.',
   3, '[1,2]', '[]',
   'Priya discovers the wall of her school covered in climbing plants.'),
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = '3' AND s.subject_code = 'EVS' AND c.chapter_number = 1),
   4, 'Types of Plants — Summary',
   'Review and compare all five plant types: trees, shrubs, herbs, climbers, creepers.',
   4, '[1,2,3]', '[]',
   'Priya draws a chart in her notebook to remember all the plants she has learned about.')
ON CONFLICT (chapter_id, topic_number) DO NOTHING;

-- Grade 3 — Animals and Their Homes
INSERT INTO topics (chapter_id, topic_number, topic_name, topic_description, sequence_number, prerequisites, exclusions, context_narrative) VALUES
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = '3' AND s.subject_code = 'EVS' AND c.chapter_number = 2),
   1, 'Domestic Animals and Their Shelters',
   'Common domestic animals and the shelters humans build for them.',
   1, '[]', '[]',
   'Priya visits a farm and sees how animals are kept safe.'),
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = '3' AND s.subject_code = 'EVS' AND c.chapter_number = 2),
   2, 'Wild Animals and Habitats',
   'How wild animals adapt to forests, deserts, oceans, and polar regions.',
   2, '[1]', '[]',
   'Priya reads a nature magazine and learns where wild animals live.')
ON CONFLICT (chapter_id, topic_number) DO NOTHING;

-- Grade 4 — Water and Its Uses
INSERT INTO topics (chapter_id, topic_number, topic_name, topic_description, sequence_number, prerequisites, exclusions, context_narrative) VALUES
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = '4' AND s.subject_code = 'EVS' AND c.chapter_number = 1),
   1, 'Sources of Water', 'Rivers, lakes, rain, wells, and groundwater as sources of water.', 1, '[]', '[]',
   'Ananya learns why her city gets water every day.'),
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = '4' AND s.subject_code = 'EVS' AND c.chapter_number = 1),
   2, 'The Water Cycle',  'Evaporation, condensation, precipitation, and the continuous cycle of water.', 2, '[1]', '[]',
   'Ananya watches a pot of boiling water and wonders where the steam goes.')
ON CONFLICT (chapter_id, topic_number) DO NOTHING;

-- Grade 5 — The Solar System
INSERT INTO topics (chapter_id, topic_number, topic_name, topic_description, sequence_number, prerequisites, exclusions, context_narrative) VALUES
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = '5' AND s.subject_code = 'EVS' AND c.chapter_number = 1),
   1, 'The Sun and the Planets',
   'Overview of the eight planets, their order from the sun, and basic characteristics.',
   1, '[]', '[]',
   'Vikram visits a planetarium and is amazed by the scale of the solar system.'),
  ((SELECT c.id FROM chapters c
      JOIN subjects s ON c.subject_id = s.id
      JOIN grades g ON s.grade_id = g.id
    WHERE g.grade_code = '5' AND s.subject_code = 'EVS' AND c.chapter_number = 1),
   2, 'The Moon and Its Phases',
   'Why the moon appears to change shape: waxing, waning, full moon, new moon.',
   2, '[1]', '[]',
   'Vikram observes the moon every night for a month and records its changing shape.')
ON CONFLICT (chapter_id, topic_number) DO NOTHING;

-- ---------------------------------------------------------------------------
-- KNOWLEDGE BASE VERSIONS — 1 active row
-- ---------------------------------------------------------------------------
INSERT INTO knowledge_base_versions (kb_version, is_active, checksum) VALUES
  ('1.0', TRUE, 'placeholder_sha256_checksum_will_be_updated_on_kb_load')
ON CONFLICT (kb_version) DO NOTHING;
