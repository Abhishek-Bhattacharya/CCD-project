import React from 'react';

interface BadgeProps {
  variant: 'lost' | 'found' | 'open' | 'resolved' | 'neutral';
  children: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({ variant, children }) => {
  const styles = {
    lost: 'bg-campus-terracotta-light text-campus-terracotta-text border-campus-terracotta-border',
    found: 'bg-campus-turmeric-light text-campus-turmeric-text border-campus-turmeric-border',
    open: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    resolved: 'bg-campus-sandstone/70 text-campus-espresso-muted border-campus-sandstone-border',
    neutral: 'bg-campus-sandstone/50 text-campus-espresso-muted border-campus-sandstone-border',
  }[variant];

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-sans font-semibold tracking-wider uppercase border ${styles}`}
    >
      {children}
    </span>
  );
};