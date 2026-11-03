export type User = {
  id: number;
  name: string;
  email: string;
  role: "admin" | "customer";
  phone: string;
  address: string;
  city: string;
  active: boolean;
  notes: string;
  created_at: string;
  avatar_url: string;
  customer_code: string | null;
  customer_type: string;
  document: string | null;
  postal_code: string;
  district: string;
  state: string;
  contact_name: string;
  portal_enabled: boolean;
};
export type Species = {
  plant_groups: string[];
  id: number;
  name: string;
  scientific_name: string;
  light: string;
  watering: string;
  size: string;
  environment: string;
  difficulty: string;
  use: string;
  description: string;
  image_url: string;
  demo_asset: string;
  watering_frequency: string;
  height: string;
  care: string;
  substrate: string;
  propagation: string;
  precautions: string;
  family: string;
  origin: string;
  photos: PlantPhoto[];
  sources: Source[];
};
export type Source = { title: string; url: string; accessed_at: string };
export type PlantPhoto = {
  url: string;
  author: string;
  license: string;
  license_url: string;
  source_url: string;
  caption: string;
  changes: string;
};
export type Article = {
  id: number;
  slug: string;
  title: string;
  category: string;
  summary: string;
  minutes: number;
  species_id: number;
  sections: { title: string; text: string; steps: string[] }[];
  sources: Source[];
};
export type LearningProgress = {
  id: number;
  user_id: number;
  article_id: number;
  completed_at: string;
};
export type Product = {
  brand: string;
  variant: string;
  barcode: string | null;
  unit: string;
  cost_cents?: number;
  markup_percent?: number;
  pricing_mode?: string;
  tax_regime?: string;
  tax_rates?: Record<string, number>;
  ncm?: string;
  supplier_id?: number | null;
  id: number;
  name: string;
  category: string;
  description: string;
  price_cents: number;
  stock: number;
  low_stock: number;
  species_id: number | null;
  image_url: string;
  active: boolean;
  sku: string;
  location: string;
  demo_asset: string;
};
export type Service = {
  delivery_mode: "Virtual" | "Presencial";
  details: {
    includes: string[];
    deliverables: string[];
    preparation: string[];
    documents: string[];
    steps: string[];
    sources: { title: string; url: string }[];
  };
  id: number;
  name: string;
  description: string;
  price_cents: number;
  unit: string;
  category: string;
  duration: string;
  responsible: string;
  active: boolean;
  demo_asset: string;
};
export type Quote = {
  brief?: LandscapeBrief;
  brief_revision: number;
  id: number;
  customer_id: number;
  service_id: number;
  area: number;
  address: string;
  description: string;
  status: string;
  amount_cents: number;
  created_at: string;
  plants: { species_id: number; quantity: number; application: string }[];
  materials: Cost[];
};
export type Cost = { name: string; quantity: number; unit_price_cents: number };
export type Project = {
  brief?: LandscapeBrief;
  brief_revision: number;
  delivery_mode: "Virtual" | "Presencial";
  reference_image_url: string;
  reference_image_note: string;
  id: number;
  name: string;
  customer_id: number;
  quote_id: number | null;
  address: string;
  area: number;
  status: string;
  budget_cents: number;
  start_date: string;
  end_date: string;
  description: string;
  plants: { species_id: number; quantity: number; application?: string }[];
  materials: Cost[];
  services: Cost[];
  tasks: { title: string; date: string; done: boolean }[];
};
export type LayoutPlant = {
  species_id: number;
  quantity: number;
  application: string;
  x: number;
  y: number;
  diameter: number;
};
export type LayoutZone = {
  name: string;
  kind: "Canteiro" | "Caminho" | "Deck" | "Gramado" | "Construção" | "Água";
  x: number;
  y: number;
  width: number;
  length: number;
};
export type LandscapeBrief = {
  width: number;
  length: number;
  north: number;
  light: string;
  soil: string;
  drainage: string;
  maintenance: string;
  objective: string;
  notes: string;
  plantings: LayoutPlant[];
  zones: LayoutZone[];
};
export type Order = {
  id: number;
  customer_id: number;
  total_cents: number;
  items: {
    product_id: number;
    name: string;
    quantity: number;
    price_cents: number;
  }[];
  status: string;
  created_at: string;
};
export type Dashboard = {
  revenue_cents: number;
  orders_count: number;
  average_ticket_cents: number;
  recurring_customers: number;
  active_projects: number;
  quotes_pending: number;
  services_count: number;
  project_budget_cents: number;
  low_stock: Product[];
  popular_products: [string, number][];
  popular_plants: [string, number][];
  monthly_sales: { month: string; total_cents: number }[];
};
export type Move = {
  balance_before: number | null;
  balance_after: number | null;
  origin: string;
  destination: string;
  reference: string;
  supplier_id: number | null;
  unit_cost_cents: number | null;
  id: number;
  product_id: number;
  quantity: number;
  reason: string;
  created_at: string;
  actor_id: number;
};
export type Appointment = {
  id: number;
  service_id: number;
  customer_id: number;
  title: string;
  date: string;
  start_time: string;
  end_time: string;
  responsible: string;
  status: string;
  address: string;
  amount_cents: number;
};
export type Ledger = {
  id: number;
  direction: string;
  source: string;
  customer_id: number | null;
  order_id: number | null;
  counterparty: string;
  description: string;
  due_date: string;
  amount_cents: number;
  status: string;
  paid_date: string;
};
export type Review = {
  id: number;
  product_id: number;
  customer_id: number;
  customer_name: string;
  rating: number;
  comment: string;
  created_at: string;
};
export type Analytics = {
  start: string;
  end: string;
  income: number;
  expense: number;
  profit: number;
  overdue_income: number;
  growth: number | null;
  products_sold: number;
  services_completed: number;
  active_services: number;
  teams: number;
  service_income: number;
  projects_active: number;
  customers_active: number;
  customers_new: number;
  customers_recurring: number;
  average_ticket: number;
  stock_moves_month: number;
  monthly: { month: string; income: number; expense: number }[];
  categories: Record<string, number>;
  origins: Record<string, number>;
  top_products: { product: Product; quantity: number; revenue_cents: number }[];
  accounts_receivable: Ledger[];
  accounts_payable: Ledger[];
};
export type AppData = {
  suppliers: Supplier[];
  products: Product[];
  species: Species[];
  services: Service[];
  projects: Project[];
  quotes: Quote[];
  orders: Order[];
  customers: User[];
  moves: Move[];
  appointments: Appointment[];
  ledger: Ledger[];
  reviews: Review[];
  favorites: number[];
  analytics: Analytics | null;
  settings: Record<string, unknown>;
  articles: Article[];
  learningProgress: LearningProgress[];
};
export type Supplier = {
  id: number;
  code: string;
  name: string;
  trade_name: string;
  document: string | null;
  category: string;
  contact_name: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  postal_code: string;
  delivery_days: number;
  notes: string;
  active: boolean;
  created_at: string;
  updated_at: string;
};
export const stages = [
  "Orçamento",
  "Aprovado",
  "Planejamento",
  "Execução",
  "Finalizado",
  "Manutenção",
];
export const money = (cents: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
    cents / 100,
  );
export const dateLabel = (date: string) =>
  new Date(date.length === 10 ? date + "T12:00:00" : date).toLocaleDateString(
    "pt-BR",
  );
