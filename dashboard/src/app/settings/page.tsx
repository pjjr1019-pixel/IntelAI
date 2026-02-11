'use client';

import { useState } from 'react';
import { SettingsModal } from '@/components/SettingsModal';

export const dynamic = 'force-dynamic';

export default function SettingsPage() {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-white mb-8">Settings</h1>
        <SettingsModal isOpen={isOpen} onClose={() => setIsOpen(false)} />
      </div>
    </div>
  );
}