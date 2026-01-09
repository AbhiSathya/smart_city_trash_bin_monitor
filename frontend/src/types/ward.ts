export interface WardLatest {
  ward: number;
  window_start: string;
  window_end: string;
  avg_fill_level: number;
}

export interface WardHistory {
  window_end: string;
  avg_fill_level: number;
}
