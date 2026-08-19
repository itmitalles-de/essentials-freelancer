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
  net_amount: string;
  tax_rate: string;
  tax_amount: string;
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
  subtotal: string;
  tax_total: string;
  total: string;
  notes: string;
  sent_at: string | null;
  paid_at: string | null;
  created_at: string;
  quote_id: number | null;
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
