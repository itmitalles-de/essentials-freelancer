export interface Client {
  id: number;
  name: string;
  contact_person: string;
  address_line1: string;
  address_line2: string;
  zip_city: string;
  email: string;
  hourly_rate: string | null;
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
  hourly_rate: string;
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
  active: boolean;
  created_at: string;
}

export type InvoiceStatus = "draft" | "sent" | "paid" | "cancelled";

export interface InvoiceLineItem {
  id: number;
  description: string;
  quantity: string;
  unit_price: string;
  amount: string;
  unit: string;
  project_id: number | null;
}

export interface Invoice {
  id: number;
  client_id: number;
  invoice_number: string;
  issue_date: string;
  due_date: string;
  status: InvoiceStatus;
  total: string;
  notes: string;
  sent_at: string | null;
  paid_at: string | null;
  created_at: string;
  quote_id: number | null;
  line_items: InvoiceLineItem[];
}

export type QuoteStatus = "draft" | "sent" | "accepted" | "rejected" | "converted";

export interface QuoteLineItem {
  id: number;
  description: string;
  quantity: string;
  unit: string;
  unit_price: string;
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
  total: string;
  notes: string;
  converted_invoice_id: number | null;
  created_at: string;
  line_items: QuoteLineItem[];
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
