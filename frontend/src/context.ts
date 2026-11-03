import { createContext, useContext } from "react";
import type { AppData, Product, User } from "./types";
export type Page =
  | "dashboard"
  | "products"
  | "inventory"
  | "customers"
  | "suppliers"
  | "services"
  | "service-detail"
  | "quotes"
  | "projects"
  | "finance"
  | "reports"
  | "settings"
  | "home"
  | "catalog"
  | "product"
  | "project"
  | "history"
  | "species"
  | "learn";
export type GreenContext = {
  user: User;
  data: AppData;
  search: string;
  setSearch: (s: string) => void;
  page: Page;
  go: (page: Page, id?: number) => void;
  open: (kind: string, item?: any) => void;
  act: (
    path: string,
    body?: unknown,
    method?: string,
    message?: string,
  ) => Promise<boolean>;
  reload: () => Promise<void>;
  busy: boolean;
  cart: Record<number, number>;
  setCart: (cart: Record<number, number>) => void;
  addCart: (product: Product, quantity?: number) => void;
  favorite: (id: number) => Promise<void>;
  period: { start: string; end: string };
  setPeriod: (p: { start: string; end: string }) => void;
  selectedId: number | null;
  toast: (text: string) => void;
};
export const Green = createContext<GreenContext | null>(null);
export function useGreen() {
  return useContext(Green)!;
}
