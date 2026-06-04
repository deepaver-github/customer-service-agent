export interface ParticipantListItem {
  id: string;
  ndis_number: string;
  first_name: string;
  last_name: string;
  preferred_name: string | null;
  primary_disability_category: string | null;
  suburb: string | null;
  state: string | null;
  status: string;
  primary_contact_name: string | null;
  primary_contact_relationship: string | null;
  active_plan_management_type: string | null;
}

export interface ParticipantListResponse {
  items: ParticipantListItem[];
  total: number;
}

export interface ParticipantCreatePayload {
  ndis_number: string;
  first_name: string;
  last_name: string;
  preferred_name?: string | null;
  dob?: string | null;
  primary_disability_category?: string | null;
  communication_needs?: string | null;
  address_line1?: string | null;
  suburb?: string | null;
  state?: string | null;
  postcode?: string | null;
  phone?: string | null;
  email?: string | null;
  status?: string;
}

export type ParticipantUpdatePayload = Partial<ParticipantCreatePayload & { address_line2: string | null }>;

export interface ContactItem {
  id: string;
  name: string;
  relationship: string;
  phone: string | null;
  email: string | null;
  is_primary: boolean;
  is_emergency: boolean;
  notes: string | null;
}

export interface GoalItem {
  id: string;
  description: string;
  category: string;
  target_date: string | null;
  status: string;
}

export interface ActivePlanItem {
  id: string;
  plan_number: string;
  start_date: string;
  end_date: string;
  management_type: string;
  plan_manager_name: string | null;
  plan_manager_contact: string | null;
  status: string;
}

export interface ServiceAgreementItem {
  id: string;
  service_code: string;
  service_name: string;
  valid_from: string;
  valid_to: string | null;
  scope_notes: string | null;
  status: string;
}

export interface StaffAssignmentItem {
  staff_id: string;
  staff_name: string;
  staff_role: string;
  assignment_type: string;
  valid_from: string;
}

export interface ShiftItem {
  id: string;
  service_name: string;
  service_code: string;
  scheduled_start: string;
  scheduled_end: string;
  actual_start: string | null;
  actual_end: string | null;
  location: string | null;
  support_worker_name: string | null;
  status: string;
  cancelled_reason: string | null;
}

export interface MedicationItem {
  id: string;
  medication_name: string;
  dose: string;
  route: string;
  frequency: string;
  prn: boolean;
  prescriber: string | null;
  start_date: string;
  end_date: string | null;
  notes: string | null;
  status: string;
}

export interface PreferenceItem {
  id: string;
  category: string;
  priority: string;
  detail: string;
}

export interface IncidentItem {
  id: string;
  incident_type: string;
  category: string;
  status: string;
  occurred_at: string;
  location: string | null;
  summary: string;
}

export interface RiskAssessmentItem {
  id: string;
  assessment_type: string;
  level: string;
  controls: string;
  assessed_at: string;
  review_due: string | null;
}

export interface RestrictivePracticeItem {
  id: string;
  practice_type: string;
  status: string;
  authorisation_ref: string | null;
  authorised_from: string | null;
  authorised_to: string | null;
  notes: string | null;
}

export interface AuditChangeItem {
  table: string;
  record_id: string;
  action: string;
  changed_at: string;
}

export interface ParticipantDetail {
  id: string;
  ndis_number: string;
  first_name: string;
  last_name: string;
  preferred_name: string | null;
  dob: string | null;
  primary_disability_category: string | null;
  communication_needs: string | null;
  address_line1: string | null;
  address_line2: string | null;
  suburb: string | null;
  state: string | null;
  postcode: string | null;
  phone: string | null;
  email: string | null;
  status: string;
  created_at: string;
  contacts: ContactItem[];
  active_plan: ActivePlanItem | null;
  goals: GoalItem[];
  service_agreements: ServiceAgreementItem[];
  assigned_staff: StaffAssignmentItem[];
  upcoming_shifts: ShiftItem[];
  recent_shifts: ShiftItem[];
  medications: MedicationItem[];
  preferences: PreferenceItem[];
  open_incidents: IncidentItem[];
  risk_assessments: RiskAssessmentItem[];
  restrictive_practices: RestrictivePracticeItem[];
  recent_changes: AuditChangeItem[];
}

export interface DashboardStats {
  active_participants: number;
  onboarding_participants: number;
  active_plans: number;
  draft_plans: number;
  active_agreements: number;
  draft_agreements: number;
  conversations_today: number;
  escalated_today: number;
}

export interface StaffListItem {
  id: string;
  first_name: string;
  last_name: string;
  role: string;
  status: string;
  email: string | null;
}

export interface KnowledgeListItem {
  id: string;
  title: string;
  category: string;
  status: string;
}
