export interface User {
  id: string;
  email: string;
  name: string;
}

export interface Alert {
  id: string;
  title: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
  source: string;
}

export interface WatchlistItem {
  id: string;
  name: string;
  type: 'keyword' | 'entity' | 'source';
  added_at: string;
}

export interface Source {
  id: string;
  name: string;
  type: string;
  status: 'active' | 'inactive';
  last_updated: string;
}