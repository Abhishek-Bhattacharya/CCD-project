import React, { useState } from 'react';
import { X, Mail, ShieldAlert, Check } from 'lucide-react';

interface ContactModalProps {
  email: string | null;
  itemTitle: string;
  itemType: 'lost' | 'found';
  onClose: () => void;
}

export const ContactModal: React.FC<ContactModalProps> = ({
  email,
  itemTitle,
  itemType,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!email) return;
    navigator.clipboard.writeText(email);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 bg-campus-espresso/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-lg max-w-md w-full p-6 shadow-warm-md border border-campus-sandstone-border relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded text-campus-espresso-subtle hover:text-campus-espresso"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="w-9 h-9 bg-campus-terracotta-light text-campus-terracotta rounded flex items-center justify-center mb-3">
          <Mail className="w-4 h-4" />
        </div>

        <h3 className="font-serif text-xl text-campus-espresso">
          Contact {itemType === 'lost' ? 'Owner' : 'Finder'}
        </h3>
        <p className="text-xs text-campus-espresso-muted mt-1 font-sans">
          Regarding: <span className="font-semibold text-campus-espresso">{itemTitle}</span>
        </p>

        {email ? (
          <div className="mt-5 space-y-3">
            <div className="p-3 bg-campus-ivory border border-campus-sandstone-border rounded flex items-center justify-between">
              <span className="text-xs font-mono text-campus-espresso select-all break-all pr-2">
                {email}
              </span>
              <button
                onClick={handleCopy}
                className="shrink-0 text-xs font-medium px-2.5 py-1 rounded bg-white border border-campus-sandstone-border hover:bg-stone-50 flex items-center gap-1 text-campus-espresso"
              >
                {copied ? <Check className="w-3 h-3 text-campus-terracotta" /> : null}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>

            <a
              href={`mailto:${email}?subject=${encodeURIComponent(`[Foundly] ${itemTitle}`)}`}
              className="w-full inline-flex justify-center items-center py-2 px-4 rounded bg-campus-terracotta hover:bg-campus-terracotta-hover text-white dark:bg-campus-terracotta-light dark:text-campus-terracotta-text dark:hover:bg-campus-terracotta-light text-xs font-medium transition-colors"
            >
              Open Email App
            </a>
          </div>
        ) : (
          <div className="mt-4 p-3 rounded bg-campus-turmeric-light border border-campus-turmeric-border text-campus-turmeric-text text-xs leading-relaxed">
            This person did not include an email address. Check the listing details or try asking in person where the item was reported.
          </div>
        )}

        <div className="mt-4 flex items-start gap-2 text-[11px] text-campus-espresso-muted bg-campus-sandstone-surface p-2.5 rounded border border-campus-sandstone-border">
          <ShieldAlert className="w-3.5 h-3.5 text-campus-terracotta shrink-0 mt-0.5" />
          <span>
            For a safe handover, arrange to meet in a public, well-lit place.
          </span>
        </div>
      </div>
    </div>
  );
};