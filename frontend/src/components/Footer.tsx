import React from 'react';
import { ShieldCheck } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-campus-sandstone-surface border-t border-campus-sandstone-border mt-20">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-campus-espresso-muted font-sans">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-campus-terracotta" />
          <span>Foundly · A community lost &amp; found</span>
        </div>
      </div>
    </footer>
  );
};