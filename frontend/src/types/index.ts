export type UserRole = 'STUDENT' | 'FACULTY' | 'MENTOR' | 'ADMIN';

export interface Department {
  id: number;
  code: string;
  name: string;
  description?: string;
  source_type?: string;
  source_url?: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  department?: number | null;
  department_details?: Department | null;
  register_number?: string;
  faculty_id?: string;
  year?: number | null;
  phone?: string;
  is_demo: boolean;
  is_active?: boolean;
  avatar_url?: string;
  created_at: string;
}

export interface FacultyMember {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  faculty_id?: string;
  register_number?: string;
  department?: number | null;
  department_details?: Department | null;
  phone?: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface SkillDomain {
  id: number;
  category: number;
  category_name?: string;
  name: string;
  description?: string;
  order: number;
  source_type?: string;
}

export interface SkillCategory {
  id: number;
  name: string;
  description: string;
  order?: number;
  source_type: string;
  source_url?: string;
  domains?: SkillDomain[];
}

export interface Skill {
  id: number;
  name: string;
  category: SkillCategory;
  domain?: SkillDomain | null;
  department?: Department | null;
  departments?: Department[];
  is_cross_department?: boolean;
  description: string;
  level: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED' | 'EXPERT';
  skill_type?: 'CORE' | 'ELECTIVE' | 'FACULTY_INITIATIVE' | 'EMERGING' | 'PLACEMENT' | 'TECHNICAL' | 'NON_TECHNICAL';
  learning_outcomes?: string[];
  estimated_duration?: string;
  source_type: string;
  source_url?: string;
  source_title?: string;
  approval_status: 'DRAFT' | 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED' | 'ARCHIVED';
  content_status?: string;
}

export interface Lesson {
  id: number;
  module: number;
  order: number;
  title: string;
  description?: string;
  content_type: 'VIDEO' | 'PDF' | 'TEXT' | 'INTERACTIVE';
  content_url?: string;
  text_content?: string;
  duration_minutes: number;
  is_required?: boolean;
  requires_video?: boolean;
  requires_notes?: boolean;
  requires_practice?: boolean;
  videos?: VideoResource[];
  materials?: StudyMaterial[];
  practice_tasks?: PracticeTask[];
  source_type?: string;
  learning_objectives?: string[];
  concept_explanation?: string;
  examples?: Array<{ title: string; code?: string; explanation: string }>;
  common_mistakes?: Array<{
    common_pitfall?: string;
    recommended_solution?: string;
    technical_rationale?: string;
    mistake?: string;
    correct?: string;
    reason?: string;
    bad_code?: string;
    good_code?: string;
    explanation?: string;
  }>;
  key_points?: string[];
  summary?: string;
  practice_recommendation?: string;
}

export interface LearningResource {
  id: number;
  module: number;
  title: string;
  resource_type: 'VIDEO_LINK' | 'DOCUMENT_LINK' | 'INTERACTIVE_LAB' | 'READING_MATERIAL';
  content_url?: string;
  text_content?: string;
  order: number;
  source_type: string;
  source_url?: string;
}

export interface StoryboardScene {
  scene_number: number;
  duration_seconds: number;
  visual_cue: string;
  narration_script: string;
  on_screen_text: string;
  code_snippet?: string;
  subtitles?: string;
}

export interface AIVideoScriptPackage {
  title: string;
  topic: string;
  estimated_duration_seconds: number;
  narration_script: string;
  visual_cues: string[];
  on_screen_code: string;
  subtitles: string[];
  scenes: StoryboardScene[];
  pedagogical_notes?: string;
  ai_model?: string;
  production_status: 'SCRIPT_READY' | 'RENDERED' | 'EXTERNAL_REFERENCE';
  render_disclaimer?: string;
}

export interface VideoResource {
  id: number;
  module: number;
  lesson?: number | null;
  title: string;
  description?: string;
  video_type: string;
  video_file?: string | null;
  external_url?: string | null;
  youtube_url?: string | null;
  youtube_video_id?: string | null;
  embed_url?: string | null;
  thumbnail?: string | null;
  thumbnail_url?: string | null;
  channel_name?: string | null;
  duration_seconds: number;
  duration_if_available?: string | null;
  completion_threshold_percent: number;
  order: number;
  is_required: boolean;
  source_type?: string;
  source_url?: string;
  source_title?: string;
  is_unavailable?: boolean;
  unavailable_reported_count?: number;
  status: string;
  ai_video_status?: 'NOT_APPLICABLE' | 'PENDING' | 'SCRIPT_READY' | 'RENDERED' | 'FAILED';
  video_provider?: string;
  generation_id?: string;
  script_package?: AIVideoScriptPackage | null;
  captions?: string;
}

export interface StudyMaterialStructuredContent {
  topic?: string;
  key?: string;
  introduction?: string;
  concept_explanation?: string;
  key_points?: string[];
  key_takeaways?: string[];
  syntax?: string;
  code_snippets?: Array<{
    title?: string;
    language?: string;
    code: string;
    explanation?: string;
  }>;
  examples?: Array<{
    title: string;
    code: string;
    output?: string;
    explanation?: string;
  }>;
  common_mistakes?: Array<{
    common_pitfall?: string;
    recommended_solution?: string;
    technical_rationale?: string;
    mistake?: string;
    correct?: string;
    reason?: string;
    bad_code?: string;
    good_code?: string;
    explanation?: string;
  }>;
  important_terms?: Array<{
    term: string;
    definition: string;
  }>;
  quick_revision?: string[];
  practice_questions?: Array<{
    question: string;
    answer: string;
    explanation: string;
  }>;
  self_check_questions?: Array<{
    question: string;
    options?: string[];
    answer?: string;
    explanation?: string;
  }>;
  [key: string]: any;
}

export interface StudyMaterial {
  id: number;
  module: number;
  lesson?: number | null;
  title: string;
  description?: string;
  resource_type: string;
  file?: string | null;
  external_url?: string | null;
  completion_method: 'MANUAL_COMPLETE' | 'OPEN' | 'PAGE_PROGRESS' | 'QUIZ_AFTER_READING';
  version: number;
  order: number;
  is_required: boolean;
  source_type?: string;
  source_url?: string;
  source_title?: string;
  status: string;
  explanation_level?: 'BEGINNER' | 'INTERMEDIATE' | 'QUICK_REVISION' | 'ADVANCED' | string;
  model_provider?: string;
  review_status?: string;
  structured_content?: StudyMaterialStructuredContent | null;
  text_content?: string | null;
}

export interface ReportedVideoIssue {
  id: number;
  video: number;
  video_title?: string;
  student: number;
  student_username?: string;
  issue_type: 'UNAVAILABLE' | 'EMBEDDING_DISABLED' | 'PRIVATE' | 'BROKEN_CONTENT' | 'TOPIC_MISMATCH' | 'OTHER';
  notes?: string;
  status: 'OPEN' | 'RESOLVED' | 'DISMISSED';
  replacement_video_id?: string;
  reported_at: string;
  resolved_at?: string;
}

export interface PracticeTask {
  id: number;
  module: number;
  lesson?: number | null;
  title: string;
  description?: string;
  task_type:
    | 'MCQ_PRACTICE'
    | 'CODING_TASK'
    | 'EXERCISE'
    | 'ASSIGNMENT'
    | 'DEBUGGING'
    | 'SHORT_ANSWER'
    | 'FILL_IN_BLANKS'
    | 'PROBLEM_SOLVING';
  difficulty?: 'EASY' | 'MEDIUM' | 'HARD';
  explanation?: string;
  content?: {
    questions?: Array<{
      id: number | string;
      question: string;
      options: string[];
      correct_option?: string;
      explanation?: string;
    }>;
    initial_code?: string;
    starter_code?: string;
    instructions?: string;
    solution_code?: string;
    buggy_code?: string;
    bug_description?: string;
    correct_code?: string;
    test_cases?: Array<{ input: string; expected: string }>;
    blanks?: Array<{ id: number; answer: string; hint: string }>;
    problem_statement?: string;
    key_points?: string[];
    [key: string]: any;
  };
  pass_score: number;
  order: number;
  is_required: boolean;
  status: string;
}

export interface Module {
  id: number;
  course: number;
  order: number;
  title: string;
  description: string;
  topic_tag: string;
  duration_minutes: number;
  estimated_minutes?: number;
  is_required?: boolean;
  status?: string;
  source_type?: string;
  source_url?: string;
  lessons?: Lesson[];
  resources?: LearningResource[];
  videos?: VideoResource[];
  materials?: StudyMaterial[];
  practice_tasks?: PracticeTask[];
}

export interface AssessmentBlueprint {
  total_questions: number;
  distribution: {
    EASY: number;
    MEDIUM: number;
    HARD: number;
  };
  duration_minutes: number;
  pass_percentage: number;
  randomize_questions?: boolean;
  randomize_options?: boolean;
}

export interface Course {
  id: number;
  title: string;
  slug: string;
  skill: Skill;
  skills?: Skill[];
  department?: Department | null;
  departments?: Department[];
  instructor_name: string;
  description: string;
  outcomes: string[];
  thumbnail_url?: string;
  estimated_hours: number;
  level?: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED' | 'EXPERT';
  course_types?: string[];
  version?: number;
  is_published: boolean;
  is_demo: boolean;
  source_type: string;
  source_url?: string;
  source_title?: string;
  source_accessed_at?: string;
  last_verified_at?: string;
  approval_status: 'DRAFT' | 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED' | 'ARCHIVED';
  content_status: string;
  modules_count?: number;
  modules?: Module[];
  prerequisites?: Course[];
  target_audience?: string;
  learning_goal?: string;
  prerequisites_text?: string;
  blueprint?: AssessmentBlueprint | null;
  programming_language?: string | null;
}

export interface AISkillSuggestion {
  id: number;
  title: string;
  category_name: string;
  domain_name?: string;
  department?: number | null;
  department_code?: string;
  level: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED' | 'EXPERT';
  skill_type: string;
  justification: string;
  prerequisites: string[];
  suggested_modules: Array<{ order: number; title: string; duration_minutes: number }>;
  learning_outcomes: string[];
  source_type: string;
  approval_status: 'DRAFT' | 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED' | 'ARCHIVED';
  created_at: string;
}

export interface DuplicateCheckMatch {
  skill_id: number;
  name: string;
  category?: string;
  domain?: string;
  level: string;
  source_type: string;
  approval_status: string;
  match_type: 'EXACT' | 'SUBSTRING' | 'TOKEN_SIMILARITY';
  confidence: number;
  similarity_reason: string;
  suggested_action: string;
}

export interface DuplicateCheckResult {
  is_duplicate: boolean;
  has_exact_match: boolean;
  matches: DuplicateCheckMatch[];
}

export interface SkillGapRecommendation {
  student_username: string;
  department?: string | null;
  strong_skills: Array<{ topic: string; average_score: number; evidence: string }>;
  needs_improvement: Array<{ topic: string; average_score: number; evidence: string }>;
  evidence_summary: string[];
  recommended_courses: Array<{
    course_id: number;
    slug: string;
    title: string;
    department: string;
    level: string;
    estimated_hours: number;
    source_type: string;
    why_recommended: string;
    priority: string;
  }>;
  diagnostic_timestamp: string;
}

export interface Enrollment {
  id: number;
  student: number;
  course: Course;
  enrolled_at: string;
  completed_at?: string;
  is_completed: boolean;
  progress_percent: number;
  is_demo: boolean;
}

export interface SystemHealth {
  status: string;
  service?: string;
  version: string;
  database?: string;
  platform?: string;
  institution?: string;
  timestamp?: string;
}

export interface QuestionOption {
  id: number;
  text: string;
  order: number;
}

export interface Question {
  id: number;
  text: string;
  title?: string;
  topic_tag: string;
  question_type: 'SINGLE_CHOICE' | 'MULTIPLE_CHOICE' | 'MCQ_SINGLE' | 'MCQ_MULTIPLE' | 'TRUE_FALSE' | 'CODING';
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
  marks: number;
  order: number;
  options: QuestionOption[];
  explanation?: string;
  is_bank_question?: boolean;
  problem_statement?: string;
  programming_language?: 'c' | 'cpp' | 'java' | 'python' | string;
  input_format?: string;
  output_format?: string;
  constraints?: string;
  sample_test_cases?: Array<{ input: string; output: string }>;
  hidden_test_cases?: Array<{ input: string; output: string }>;
  reference_solution?: string;
}

export interface SampleTestResult {
  test_index: number;
  input: string;
  expected_output: string;
  actual_output: string;
  passed: boolean;
  status: string;
  error?: string | null;
  execution_time_ms: number;
}

export interface RunCodeResponse {
  mode: 'RUN_CODE';
  language: string;
  sample_passed: number;
  sample_total: number;
  all_sample_passed: boolean;
  sample_results: SampleTestResult[];
}

export interface SubmitCodeResponse {
  mode: 'SUBMIT_CODE';
  language: string;
  sample_passed: number;
  sample_total: number;
  hidden_passed: number;
  hidden_total: number;
  total_passed: number;
  total_count: number;
  passed: boolean;
  status: 'PASSED' | 'FAILED';
  sample_results: SampleTestResult[];
  hidden_summary: {
    passed_count: number;
    total_count: number;
    results: Array<{
      test_index: number;
      passed: boolean;
      status: string;
      execution_time_ms: number;
    }>;
  };
}

export interface QuestionBankItem {
  id: number;
  text: string;
  topic_tag: string;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
  marks: number;
  explanation: string;
  options: Array<{ id: number; text: string; is_correct?: boolean }>;
}

export interface Assessment {
  id: number;
  title: string;
  assessment_type: 'PRE_ASSESSMENT' | 'FINAL_ASSESSMENT';
  version: number;
  duration_minutes: number;
  pass_percentage: number;
  max_attempts: number;
  questions_count: number;
  camera_required?: boolean;
  screen_share_required?: boolean;
  fullscreen_required?: boolean;
  face_detection_enabled?: boolean;
  max_camera_warnings?: number;
  max_multiple_face_warnings?: number;
  max_screen_share_warnings?: number;
  max_fullscreen_warnings?: number;
  max_tab_switch_warnings?: number;
  multiple_faces_threshold_seconds?: number;
  auto_terminate_on_limit?: boolean;
  blueprint?: AssessmentBlueprint | null;
  is_ai_generated?: boolean;
}

export interface AICourseGeneratePayload {
  skill_name: string;
  course_name?: string;
  level?: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED' | 'EXPERT';
  target_audience?: string;
  learning_goal?: string;
  duration_hours?: number;
  department_id?: number | null;
  publish_immediately?: boolean;
}

export interface AICourseGenerateResponse {
  course_id: number;
  slug: string;
  title: string;
  skill_id: number;
  skill_name: string;
  level: string;
  assessment_id?: number;
  assessment_title?: string;
  blueprint?: AssessmentBlueprint;
  modules_count: number;
  lessons_count: number;
  video_packages_count: number;
  study_materials_count: number;
  practice_tasks_count: number;
  question_bank_count: number;
  message?: string;
}

export interface AISkillGeneratePayload {
  skill_name: string;
  department_code?: string | null;
  level?: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED' | 'EXPERT';
  skill_type?: string;
  preview_only?: boolean;
}

export interface AISkillGenerateResponse {
  id?: number;
  slug?: string;
  name: string;
  category_id?: number | null;
  category_name?: string;
  domain_id?: number | null;
  domain_name?: string;
  department_id?: number | null;
  department_code?: string;
  department_name?: string;
  level: string;
  skill_type: string;
  learning_outcomes: string[];
  description: string;
  estimated_duration: string;
  prerequisites_text?: string;
  source_type: string;
  approval_status: string;
  status: string;
  created?: boolean;
}

export interface AssessmentAttempt {
  id: string;
  assessment: Assessment;
  status:
    | 'READY'
    | 'IN_PROGRESS'
    | 'WARNING'
    | 'SUBMITTED'
    | 'EXPIRED'
    | 'EVALUATED'
    | 'PASSED'
    | 'FAILED'
    | 'FLAGGED'
    | 'TERMINATED_SECURITY_VIOLATION'
    | 'CANCELLED';
  started_at: string;
  server_deadline: string;
  score: number;
  percentage: number;
  passed: boolean;
  review_status: 'NOT_REQUIRED' | 'PENDING_REVIEW' | 'VALID' | 'WARNING' | 'INVALID';
  questions: Question[];
  answers: Record<number, number[]>;
  camera_warning_count?: number;
  multiple_face_warning_count?: number;
  screen_share_warning_count?: number;
  fullscreen_warning_count?: number;
  tab_switch_warning_count?: number;
  termination_reason?: string | null;
  terminated_at?: string | null;
}

export interface RiskScore {
  numerical_score: number;
  tier: 'NORMAL' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'ELEVATED';
  event_count: number;
  evaluated_at: string;
}

export interface TopicBreakdownItem {
  total_marks: number;
  earned_marks: number;
  percentage: number;
  status: 'PROFICIENT' | 'GROWTH_NEEDED' | 'CRITICAL_GAP';
}

export interface QuestionOptionReview {
  id: number;
  text: string;
  is_correct: boolean;
  is_selected: boolean;
  order: number;
}

export interface AIMistakeDiagnosis {
  why_incorrect: string;
  why_correct: string;
  simple_explanation: string;
  small_example: string;
  recommended_topic: string;
}

export interface DetailedQuestionReview {
  question_id: number;
  order: number;
  question_text: string;
  question_type?: 'SINGLE_CHOICE' | 'MULTIPLE_CHOICE' | 'MCQ_SINGLE' | 'MCQ_MULTIPLE' | 'TRUE_FALSE' | 'CODING' | string;
  topic_tag: string;
  topic_label: string;
  difficulty: string;
  marks: number;
  is_answered: boolean;
  is_correct: boolean;
  options: QuestionOptionReview[];
  student_answers: string[];
  correct_answers: string[];
  explanation: string;
  ai_diagnosis?: AIMistakeDiagnosis | null;
  submitted_code?: string;
  code_language?: string;
  test_cases_passed?: number;
  total_test_cases?: number;
  code_execution_details?: any;
}

export interface WeakAreaRecommendation {
  topic_tag: string;
  topic_name: string;
  error_count: number;
  module_id: number;
  module_order: number;
  module_title: string;
  course_slug: string;
  video_reference?: {
    title: string;
    youtube_video_id: string;
    youtube_url: string;
    thumbnail_url: string;
    channel_name: string;
    duration: string;
  } | null;
  study_material?: {
    id: number;
    title: string;
    description: string;
  } | null;
  practice_task?: {
    id: number;
    title: string;
    task_type: string;
  } | null;
  ai_action_plan: string;
}

export interface AttemptReviewData {
  total_questions: number;
  answered_count: number;
  correct_count: number;
  wrong_count: number;
  passing_percentage: number;
  passed: boolean;
  score: number;
  percentage: number;
  ai_diagnostic_summary: string;
  primary_weak_area?: string | null;
  weak_area_recommendations: WeakAreaRecommendation[];
  detailed_questions: DetailedQuestionReview[];
}

export interface AssessmentResult {
  id: string;
  assessment: Assessment;
  student_name?: string;
  status: string;
  started_at: string;
  submitted_at: string;
  score: number;
  percentage: number;
  passed: boolean;
  topic_breakdown: Record<string, TopicBreakdownItem>;
  review_status: 'NOT_REQUIRED' | 'PENDING_REVIEW' | 'VALID' | 'WARNING' | 'INVALID';
  risk_assessment?: RiskScore;
  skill_gap_analysis?: any;
  review_data?: AttemptReviewData;
  camera_warning_count?: number;
  multiple_face_warning_count?: number;
  screen_share_warning_count?: number;
  fullscreen_warning_count?: number;
  tab_switch_warning_count?: number;
  termination_reason?: string | null;
  terminated_at?: string | null;
}

export interface Certificate {
  id: string;
  certificate_id?: string;
  certificate_number: string;
  course_title: string;
  course_slug?: string;
  student_name?: string;
  skill?: string;
  score?: string;
  assessment_score?: string;
  department?: string;
  issued_at: string;
  issue_date?: string;
  assessment_status?: string;
  is_revoked: boolean;
  revocation_reason?: string;
  revoked_at?: string;
  integrity_hash: string;
  qr_url: string;
  status?: 'VALID' | 'REVOKED' | 'NOT_FOUND';
  institution?: string;
  is_demo?: boolean;
}

