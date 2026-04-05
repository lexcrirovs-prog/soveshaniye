import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Types
export interface Employee {
  id: number
  bitrix_id: number
  name: string
  department?: string
  position?: string
  is_active: boolean
  total_calls: number
  avg_score?: number
}

export interface EmployeeProfile extends Employee {
  score_trends: ScoreTrend[]
  top_strengths: string[]
  top_weaknesses: string[]
  development_plan: string[]
  priority_training?: string
}

export interface ScoreTrend {
  week: string
  greeting?: number
  needs_discovery?: number
  presentation?: number
  objection_handling?: number
  closing?: number
  initiative?: number
  overall?: number
}

export interface Segment {
  start: number
  end: number
  text: string
  confidence?: number
}

export interface Transcript {
  id: number
  text: string
  language: string
  confidence?: number
  segments?: Segment[]
}

export interface Analysis {
  id: number
  call_id: number
  script_id?: number
  greeting_score?: number
  needs_discovery?: number
  presentation_score?: number
  objection_handling?: number
  closing_score?: number
  initiative_score?: number
  overall_score?: number
  summary?: string
  strengths?: string[]
  weaknesses?: string[]
  recommendations?: string[]
  missed_script_steps?: string[]
  who_leads?: string
  next_step_agreed?: boolean
  crm_note_suggestion?: string
}

export interface Call {
  id: number
  bitrix_call_id: string
  employee_id?: number
  employee_name?: string
  direction: string
  phone_number?: string
  duration_sec: number
  call_date: string
  deal_id?: number
  deal_name?: string
  deal_stage?: string
  deal_amount?: number
  status: string
  overall_score?: number
  who_leads?: string
  next_step_agreed?: boolean
}

export interface CallDetail extends Call {
  transcript?: Transcript
  analysis?: Analysis
  audio_url?: string
}

export interface CallListResponse {
  items: Call[]
  total: number
  page: number
  page_size: number
}

export interface ExportJob {
  id: number
  period: string
  date_from?: string
  date_to?: string
  department_id?: number
  status: string
  started_at?: string
  finished_at?: string
  total_calls: number
  processed: number
  error_msg?: string
  report_path?: string
  created_at?: string
}

export interface SalesScript {
  id: number
  name: string
  description?: string
  content: string
  original_file?: string
  file_type?: string
  is_active: boolean
  created_at?: string
}

export interface DashboardSummary {
  total_calls: number
  total_employees: number
  total_deals: number
  avg_score?: number
  avg_duration?: number
  calls_with_next_step: number
  calls_without_next_step: number
  top_problems: string[]
  top_recommendations: string[]
}

export interface EmployeeRanking {
  employee_id: number
  name: string
  total_calls: number
  avg_greeting?: number
  avg_needs_discovery?: number
  avg_presentation?: number
  avg_objection_handling?: number
  avg_closing?: number
  avg_initiative?: number
  avg_overall?: number
  priority_training?: string
}

export interface TrendPoint {
  week: string
  avg_score?: number
  total_calls: number
}

// API functions
export const fetchDashboardSummary = (params?: Record<string, string>) =>
  api.get<DashboardSummary>('/dashboard/summary', { params }).then(r => r.data)

export const fetchDashboardScores = (params?: Record<string, string>) =>
  api.get<EmployeeRanking[]>('/dashboard/scores', { params }).then(r => r.data)

export const fetchDashboardTrends = (params?: Record<string, string>) =>
  api.get<TrendPoint[]>('/dashboard/trends', { params }).then(r => r.data)

export const fetchCalls = (params?: Record<string, string>) =>
  api.get<CallListResponse>('/calls', { params }).then(r => r.data)

export const fetchCall = (id: number) =>
  api.get<CallDetail>(`/calls/${id}`).then(r => r.data)

export const reanalyzeCall = (id: number, scriptId?: number) =>
  api.post(`/calls/${id}/reanalyze`, { script_id: scriptId }).then(r => r.data)

export const fetchEmployees = () =>
  api.get<Employee[]>('/employees').then(r => r.data)

export const fetchEmployee = (id: number) =>
  api.get<EmployeeProfile>(`/employees/${id}`).then(r => r.data)

export const fetchEmployeeCalls = (id: number) =>
  api.get<Call[]>(`/employees/${id}/calls`).then(r => r.data)

export const fetchEmployeeScores = (id: number) =>
  api.get<ScoreTrend[]>(`/employees/${id}/scores`).then(r => r.data)

export const fetchScripts = () =>
  api.get<SalesScript[]>('/scripts').then(r => r.data)

export const createScript = (formData: FormData) =>
  api.post<SalesScript>('/scripts', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)

export const updateScript = (id: number, data: Partial<SalesScript>) =>
  api.put<SalesScript>(`/scripts/${id}`, data).then(r => r.data)

export const deleteScript = (id: number) =>
  api.delete(`/scripts/${id}`).then(r => r.data)

export const fetchExports = () =>
  api.get<ExportJob[]>('/exports').then(r => r.data)

export const createExport = (period: string, departmentId?: number) =>
  api.post<ExportJob>('/exports', { period, department_id: departmentId }).then(r => r.data)

export const fetchExport = (id: number) =>
  api.get<ExportJob>(`/exports/${id}`).then(r => r.data)

export const fetchExportReport = (id: number) =>
  api.get<{ url: string }>(`/exports/${id}/report`).then(r => r.data)

export default api
