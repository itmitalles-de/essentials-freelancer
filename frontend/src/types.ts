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
  date: string;
  description: string;
  duration_minutes: number;
  hourly_rate: string;
  running_started_at: string | null;
  billed: boolean;
  invoice_id: number | null;
}

export type InvoiceStatus = "draft" | "sent" | "paid" | "cancelled";

export interface InvoiceLineItem {
  id: number;
  description: string;
  quantity: string;
  unit_price: string;
  amount: string;
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
  line_items: InvoiceLineItem[];
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
  default_hourly_rate: string;
  default_payment_terms_days: number;
  next_invoice_number: number;
  has_logo: boolean;
}
