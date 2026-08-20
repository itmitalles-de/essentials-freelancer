export interface Client {
  id: number;
  name: string;
  contact_person: string;
  address_line1: string;
  address_line2: string;
  zip_city: string;
  email: string;
  hourly_rate: string | null;
  billing_rate_type: "private" | "business" | "custom";
  default_service_mode: "remote" | "onsite" | null;
  billing_profile_confirmed: boolean;
  notes: string;
  active: boolean;
  created_at: string;
}

export interface TimeEntry {
  id: number;
  client_id: number;
  project_id: number | null;
  date: string;
  description: string;
  duration_minutes: number;
  actual_minutes: number;
  hourly_rate: string;
  billable_minutes: number | null;
  billing_rate_type: string | null;
  billing_rate_source: string | null;
  applied_minimum_minutes: number | null;
  applied_increment_minutes: number | null;
  service_mode: "remote" | "onsite" | null;
  is_first_order: boolean;
  billing_reason: string | null;
  billing_policy_id: string | null;
  billing_policy_applied: boolean;
  travel_actual_minutes: number;
  travel_billable_minutes: number | null;
  travel_hourly_rate: string | null;
  travel_minimum_minutes: number | null;
  travel_increment_minutes: number | null;
  travel_billing_reason: string | null;
  running_started_at: string | null;
  billed: boolean;
  invoice_id: number | null;
}

export interface Project {
  id: number;
  client_id: number;
  name: string;
  description: string;
  hourly_rate: string | null;
  billing_rate_type_override: "private" | "business" | "custom" | null;
  default_service_mode: "remote" | "onsite";
  is_individual_project: boolean;
  billing_profile_confirmed: boolean;
  active: boolean;
  created_at: string;
}

export type InvoiceStatus = "draft" | "sent" | "paid" | "cancelled";

export interface InvoiceLineItem {
  id: number;
  description: string;
  quantity: string;
  unit_price: string;
  net_amount: string;
  tax_rate: string;
  tax_amount: string;
  amount: string;
  unit: string;
  project_id: number | null;
  snapshot_line_kind: string | null;
  snapshot_actual_minutes: number | null;
  snapshot_billable_minutes: number | null;
  snapshot_hourly_rate: string | null;
  snapshot_rate_type: string | null;
  snapshot_minimum_minutes: number | null;
  snapshot_increment_minutes: number | null;
  snapshot_service_mode: string | null;
  snapshot_is_first_order: boolean | null;
  snapshot_billing_reason: string | null;
  snapshot_billing_policy_id: string | null;
  snapshot_service_date: string | null;
  snapshot_project_name: string | null;
}

export interface InvoicePreviewLine {
  time_entry_id: number;
  line_kind: "work" | "travel";
  description: string;
  actual_minutes: number;
  billable_minutes: number;
  hourly_rate: string;
  rate_type: string;
  minimum_minutes: number;
  increment_minutes: number | null;
  service_mode: "remote" | "onsite";
  is_first_order: boolean;
  billing_reason: string;
  billing_policy_id: string;
  service_date: string;
  project_id: number | null;
  project_name: string | null;
  net_amount: string;
  tax_amount: string;
  total_amount: string;
}

export interface InvoicePreview {
  client_id: number;
  lines: InvoicePreviewLine[];
  work_total: string;
  travel_total: string;
  subtotal: string;
  tax_total: string;
  total: string;
  tax_rate: string;
  tax_status: string;
  tax_notice: string | null;
  confirmation_token: string;
}

export interface Invoice {
  id: number;
  client_id: number;
  invoice_number: string;
  issue_date: string;
  due_date: string;
  status: InvoiceStatus;
  subtotal: string;
  tax_total: string;
  total: string;
  notes: string;
  sent_at: string | null;
  paid_at: string | null;
  created_at: string;
  quote_id: number | null;
  tax_status_snapshot: string | null;
  tax_notice_snapshot: string | null;
  footer_note_snapshot: string | null;
  billing_confirmation_token: string | null;
  line_items: InvoiceLineItem[];
}

export interface InvoiceSendAttempt {
  id: number;
  recipient: string;
  is_resend: boolean;
  outcome: "pending" | "sent" | "failed";
  message_id_redacted: string | null;
  failure_code: string | null;
  created_at: string;
  completed_at: string | null;
}

export type QuoteStatus = "draft" | "sent" | "accepted" | "rejected" | "converted";

export interface QuoteLineItem {
  id: number;
  description: string;
  quantity: string;
  unit: string;
  unit_price: string;
  net_amount: string;
  tax_rate: string;
  tax_amount: string;
  amount: string;
}

export interface Quote {
  id: number;
  client_id: number;
  project_id: number | null;
  quote_number: string;
  issue_date: string;
  valid_until: string;
  status: QuoteStatus;
  subtotal: string;
  tax_total: string;
  total: string;
  notes: string;
  converted_invoice_id: number | null;
  created_at: string;
  line_items: QuoteLineItem[];
}

export interface QuoteInvoicePreviewLine {
  quote_line_item_id: number;
  description: string;
  quantity: string;
  unit: string;
  unit_price: string;
  actual_minutes: number | null;
  billable_minutes: number | null;
  rate_type: "fixed_quote";
  minimum_minutes: number | null;
  increment_minutes: number | null;
  service_mode: string | null;
  billing_reason: string;
  service_date: string;
  project_id: number | null;
  project_name: string | null;
  net_amount: string;
  tax_rate: string;
  tax_amount: string;
  total_amount: string;
}

export interface QuoteInvoicePreview {
  quote_id: number;
  lines: QuoteInvoicePreviewLine[];
  work_total: string;
  travel_total: string;
  fixed_total: string;
  subtotal: string;
  tax_total: string;
  total: string;
  tax_status: string;
  tax_notice: string | null;
  service_date: string;
  due_date: string;
  confirmation_token: string;
}

export interface Expense {
  id: number;
  date: string;
  description: string;
  category: string;
  amount: string;
  created_at: string;
  has_receipt: boolean;
}

export interface ReportSummary {
  date_from: string | null;
  date_to: string | null;
  client_id: number | null;
  project_id: number | null;
  time: {
    captured_hours: string;
    unbilled_hours: string;
    groups: {
      client_id: number;
      project_id: number | null;
      captured_hours: string;
      unbilled_hours: string;
    }[];
  };
  quotes: {
    statuses: Record<QuoteStatus, number>;
    conversion_rate_percent: string;
  };
  invoices: {
    statuses: Record<InvoiceStatus | "overdue", number>;
    open_amount: string;
    paid_amount: string;
  };
  expenses: {
    total: string;
    categories: { category: string; amount: string }[];
  };
}

export interface CompanySettings {
  company_name: string;
  owner_name: string;
  address_line1: string;
  address_line2: string;
  zip_city: string;
  email: string;
  phone: string;
  tax_id: string;
  iban: string;
  bic: string;
  bank_name: string;
  invoice_footer_note: string;
  invoice_number_prefix: string;
  quote_number_prefix: string;
  default_hourly_rate: string;
  default_payment_terms_days: number;
  private_hourly_rate: string;
  business_hourly_rate: string;
  travel_hourly_rate: string;
  first_order_minimum_minutes: number;
  onsite_minimum_minutes: number;
  remote_increment_minutes: number;
  travel_minimum_minutes: number;
  travel_increment_minutes: number | null;
  default_tax_rate: string;
  small_business_notice_enabled: boolean;
  small_business_notice_text: string;
  next_invoice_number: number;
  next_quote_number: number;
  has_logo: boolean;
}

export type ModuleState =
  | "not_installed"
  | "needs_configuration"
  | "disabled"
  | "enabled"
  | "degraded";

export interface ModuleRequirement {
  key: string;
  label: string;
  required: boolean;
  source: string;
}

export interface ModuleManifest {
  id: string;
  schema_version: number;
  display_name: string;
  description: string;
  group: string;
  module_type: "core" | "built_in" | "connector" | "custom";
  required: boolean;
  default_state: ModuleState;
  dependencies: string[];
  conflicts: string[];
  compatible_product_versions: string;
  compatible_schema_versions: string;
  configuration_fields: ModuleRequirement[];
  secret_requirements: ModuleRequirement[];
  api_boundaries: string[];
  navigation_boundaries: string[];
  job_boundaries: string[];
  healthcheck: string;
  data_ownership: string[];
  export_behavior: string;
  backup_behavior: string;
  restore_behavior: string;
  activation_behavior: string;
  deactivation_behavior: string;
  update_behavior: string;
}

export interface ModuleStatus {
  manifest: ModuleManifest;
  state: ModuleState;
  configuration: { key: string; configured: boolean }[];
  secrets: { key: string; configured: boolean }[];
  health: { status: string; message: string };
}

export interface CatalogVersion {
  id: number;
  item_id: number;
  version: number;
  description: string;
  unit: string;
  net_unit_price: string;
  tax_rate: string;
  valid_from: string;
  valid_until: string | null;
  created_at: string;
}

export interface CatalogItem {
  id: number;
  stable_key: string;
  kind: "service" | "material" | "travel";
  name: string;
  active: boolean;
  versions: CatalogVersion[];
  created_at: string;
}

export interface AssistantSelection {
  catalog_version_id?: number | null;
  package_version_id?: number | null;
  quantity: string | number;
}

export interface QuotePackageVersion {
  id: number;
  package_id: number;
  version: number;
  description: string;
  valid_from: string;
  valid_until: string | null;
  items: { catalog_version_id: number; quantity: string; sort_order: number }[];
  created_at: string;
}

export interface QuotePackage {
  id: number;
  stable_key: string;
  name: string;
  active: boolean;
  versions: QuotePackageVersion[];
  created_at: string;
}

export interface AssistantTemplateVersion {
  id: number;
  template_id: number;
  version: number;
  description: string;
  questions: string[];
  selections: AssistantSelection[];
  surcharge_percent: string;
  discount_percent: string;
  created_at: string;
}

export interface AssistantTemplate {
  id: number;
  stable_key: string;
  name: string;
  active: boolean;
  versions: AssistantTemplateVersion[];
  created_at: string;
}

export interface AssistantLine {
  catalog_version_id: number;
  package_version_id: number | null;
  description: string;
  quantity: string;
  unit: string;
  unit_price: string;
  tax_rate: string;
  net_amount: string;
  tax_amount: string;
  amount: string;
  sort_order: number;
}

export interface AssistantPreview {
  pricing_date: string;
  lines: AssistantLine[];
  tax_breakdown: {
    tax_rate: string;
    base_net: string;
    surcharge: string;
    discount: string;
    taxable_net: string;
    tax_amount: string;
    gross: string;
  }[];
  calculation_steps: {
    key: string;
    label: string;
    expression: string;
    amount: string;
  }[];
  base_net_total: string;
  surcharge_percent: string;
  surcharge_amount: string;
  discount_percent: string;
  discount_amount: string;
  net_total: string;
  tax_total: string;
  total: string;
}

export interface AssistantDraft extends AssistantPreview {
  id: number;
  client_id: number;
  project_id: number | null;
  template_version_id: number | null;
  quote_id: number | null;
  title: string;
  status: "draft" | "approved" | "transferred";
  guided_answers: Record<string, string>;
  notes: string;
  approved_at: string | null;
  transferred_at: string | null;
  created_at: string;
  updated_at: string;
}
