import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { SystemHealth } from '../types';
import { ShieldCheck } from 'lucide-react';

export const HealthBadge: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [error, setError] = useState<boolean>(false);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await apiClient.get<SystemHealth>('/health/');
        setHealth(res.data);
        setError(false);
      } catch {
        setError(true);
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  if (error || !health) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 border border-red-200">
        <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
        API Offline
      </span>
    );
  }

  return (
    <span 
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-sm"
      title={health.service ? `${health.service} (v${health.version})` : `FX SkillHub (v${health.version})`}
    >
      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
      <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
      FXEC Live ({health.version})
    </span>
  );
};
