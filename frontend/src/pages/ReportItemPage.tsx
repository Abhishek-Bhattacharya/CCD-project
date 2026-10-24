import React, { useState } from 'react';
import { Upload, AlertCircle, CheckCircle2 } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { ItemFormData, ItemType } from '../types/database';
import { CATEGORIES, CAMPUS_LOCATIONS } from '../lib/constants';

interface ReportItemPageProps {
  initialType?: ItemType;
  onSuccess: (id: string) => void;
}

export const ReportItemPage: React.FC<ReportItemPageProps> = ({
  initialType = 'lost',
  onSuccess,
}) => {
  const [reporterName, setReporterName] = useState('');
  const [reporterPhone, setReporterPhone] = useState('');
  const [formData, setFormData] = useState<ItemFormData>({
    title: '',
    type: initialType,
    category: CATEGORIES[0],
    description: '',
    date_lost_or_found: new Date().toISOString().split('T')[0],
    location: CAMPUS_LOCATIONS[0],
    image_url: null,
    contact_email: '',
  });

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.size > 5 * 1024 * 1024) {
        setErrorMsg('Image size cannot exceed 5MB.');
        return;
      }
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setErrorMsg(null);
    }
  };

  const uploadPhoto = async (file: File): Promise<string | null> => {
    const fileExt = file.name.split('.').pop();
    const fileName = `${Date.now()}-${Math.random().toString(36).substring(2)}.${fileExt}`;
    const filePath = `items/${fileName}`;

    const { error: uploadError } = await supabase.storage
      .from('item-photos')
      .upload(filePath, file);

    if (uploadError) {
      console.error('Storage upload failed:', uploadError);
      return null;
    }

    const { data } = supabase.storage.from('item-photos').getPublicUrl(filePath);
    return data.publicUrl;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (formData.title.trim().length < 3) {
      setErrorMsg('Item title must be at least 3 characters.');
      return;
    }
    if (formData.description.trim().length < 10) {
      setErrorMsg('Description must be at least 10 characters.');
      return;
    }
    if (
      formData.contact_email &&
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.contact_email.trim())
    ) {
      setErrorMsg('Please enter a valid contact email address.');
      return;
    }

    setLoading(true);

    try {
      let finalImageUrl: string | null = null;
      if (selectedFile) {
        finalImageUrl = await uploadPhoto(selectedFile);
      }

      const { data, error } = await supabase
        .from('items')
        .insert([
          {
            title: formData.title.trim(),
            type: formData.type,
            category: formData.category,
            description: formData.description.trim(),
            date_lost_or_found: formData.date_lost_or_found,
            location: formData.location,
            image_url: finalImageUrl,
            contact_email: formData.contact_email?.trim() || null,
            status: 'open',
          },
        ])
        .select()
        .single();

      if (error) throw error;

      setSuccess(true);
      setTimeout(() => {
        if (data?.id) onSuccess(data.id);
      }, 1000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Database error.';
      setErrorMsg(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-4">
      <div className="mb-6">
        <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-campus-terracotta">Help an item find its person</span>
        <h1 className="mt-1 font-serif text-3xl sm:text-4xl text-campus-espresso font-normal">Report an item</h1>
        <p className="text-xs text-campus-espresso-muted mt-1 font-sans">
          Tell the community what you lost or found, and where it was last seen.
        </p>
      </div>

      {success ? (
        <div className="bg-campus-sandstone-surface border border-campus-sandstone-border rounded p-8 text-center space-y-2">
          <CheckCircle2 className="w-10 h-10 text-campus-terracotta mx-auto" />
          <h2 className="font-serif text-xl text-campus-espresso">Report Logged Successfully</h2>
          <p className="text-xs text-campus-espresso-muted font-sans">Redirecting to your listing...</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-campus-sandstone-border p-5 sm:p-8 space-y-5 shadow-warm">
          {errorMsg && (
            <div className="p-3 rounded bg-campus-terracotta-light border border-campus-terracotta-border text-campus-terracotta-text text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-campus-terracotta" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div>
            <label className="block text-[11px] font-semibold text-campus-espresso-muted uppercase tracking-wider mb-2">
              Report Type *
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setFormData({ ...formData, type: 'lost' })}
                className={`py-2 px-3 rounded text-xs font-semibold border text-center transition-all ${
                  formData.type === 'lost'
                    ? 'border-campus-terracotta-border bg-campus-terracotta-light text-campus-terracotta-text'
                    : 'border-campus-sandstone-border bg-white text-campus-espresso-muted hover:bg-stone-50'
                }`}
              >
                I Lost Something
              </button>
              <button
                type="button"
                onClick={() => setFormData({ ...formData, type: 'found' })}
                className={`py-2 px-3 rounded text-xs font-semibold border text-center transition-all ${
                  formData.type === 'found'
                    ? 'border-campus-turmeric-border bg-campus-turmeric-light text-campus-turmeric-text'
                    : 'border-campus-sandstone-border bg-white text-campus-espresso-muted hover:bg-stone-50'
                }`}
              >
                I Found Something
              </button>
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-campus-espresso-muted uppercase tracking-wider mb-1.5">
              Item Title *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Blue water bottle with silver stickers"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="w-full px-3 py-2 rounded bg-campus-ivory border border-campus-sandstone-border text-xs sm:text-sm text-campus-espresso focus:outline-none focus:ring-1 focus:ring-campus-terracotta focus:bg-white"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-semibold text-campus-espresso-muted uppercase tracking-wider mb-1.5">
                Category *
              </label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="w-full px-3 py-2 rounded bg-campus-ivory border border-campus-sandstone-border text-xs text-campus-espresso focus:outline-none focus:ring-1 focus:ring-campus-terracotta focus:bg-white"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-campus-espresso-muted uppercase tracking-wider mb-1.5">
                Location *
              </label>
              <select
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                className="w-full px-3 py-2 rounded bg-campus-ivory border border-campus-sandstone-border text-xs text-campus-espresso focus:outline-none focus:ring-1 focus:ring-campus-terracotta focus:bg-white"
              >
                {CAMPUS_LOCATIONS.map((loc) => (
                  <option key={loc} value={loc}>{loc}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-campus-espresso-muted uppercase tracking-wider mb-1.5">
              Date {formData.type === 'lost' ? 'Lost' : 'Found'} *
            </label>
            <input
              type="date"
              required
              value={formData.date_lost_or_found}
              onChange={(e) => setFormData({ ...formData, date_lost_or_found: e.target.value })}
              className="w-full px-3 py-2 rounded bg-campus-ivory border border-campus-sandstone-border text-xs text-campus-espresso focus:outline-none focus:ring-1 focus:ring-campus-terracotta focus:bg-white"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-campus-espresso-muted uppercase tracking-wider mb-1.5">
              Description & Identifying Details *
            </label>
            <textarea
              required
              rows={3}
              placeholder="Provide identifying details (e.g. color, stickers, brand, or distinguishing marks)..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 rounded bg-campus-ivory border border-campus-sandstone-border text-xs sm:text-sm text-campus-espresso focus:outline-none focus:ring-1 focus:ring-campus-terracotta focus:bg-white"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-campus-espresso-muted uppercase tracking-wider mb-1.5">
              Photograph (Optional)
            </label>
            <div className="flex items-center gap-3">
              {previewUrl && (
                <div className="w-16 h-16 rounded border border-campus-sandstone-border overflow-hidden shrink-0">
                  <img src={previewUrl} alt="Preview" className="w-full h-full object-cover" />
                </div>
              )}
              <label className="flex-1 cursor-pointer flex flex-col items-center justify-center p-3 border border-dashed border-campus-sandstone-border rounded bg-campus-ivory/50 hover:bg-stone-100/50 transition-colors">
                <Upload className="w-4 h-4 text-campus-espresso-subtle mb-0.5" />
                <span className="text-xs font-medium text-campus-espresso font-sans">
                  {selectedFile ? selectedFile.name : 'Upload item photo (PNG, JPG)'}
                </span>
                <input
                  type="file"
                  accept="image/png, image/jpeg, image/webp"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          <section className="space-y-3 rounded-xl border border-campus-sandstone-border bg-campus-sandstone-surface/60 p-4">
            <div>
              <h2 className="text-xs font-semibold text-campus-espresso">Your contact details</h2>
              <p className="mt-1 text-[11px] text-campus-espresso-muted">
                Let someone reach you to arrange a handover.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor="reporter-name" className="mb-1 block text-[11px] font-medium text-campus-espresso-muted">
                  Your name
                </label>
                <input
                  id="reporter-name"
                  type="text"
                  required
                  autoComplete="name"
                  placeholder="Name"
                  value={reporterName}
                  onChange={(e) => setReporterName(e.target.value)}
                  className="w-full rounded-lg border border-campus-sandstone-border bg-campus-ivory px-3 py-2 text-xs text-campus-espresso focus:border-campus-terracotta focus:bg-white focus:outline-none focus:ring-1 focus:ring-campus-terracotta"
                />
              </div>
              <div>
                <label htmlFor="reporter-email" className="mb-1 block text-[11px] font-medium text-campus-espresso-muted">
                  Contact email
                </label>
                <input
                  id="reporter-email"
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={formData.contact_email || ''}
                  onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                  className="w-full rounded-lg border border-campus-sandstone-border bg-campus-ivory px-3 py-2 text-xs text-campus-espresso focus:border-campus-terracotta focus:bg-white focus:outline-none focus:ring-1 focus:ring-campus-terracotta"
                />
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="reporter-phone" className="mb-1 block text-[11px] font-medium text-campus-espresso-muted">
                  Phone number <span className="font-normal">(optional)</span>
                </label>
                <input
                  id="reporter-phone"
                  type="tel"
                  autoComplete="tel"
                  placeholder="A number where you can be reached"
                  value={reporterPhone}
                  onChange={(e) => setReporterPhone(e.target.value)}
                  className="w-full rounded-lg border border-campus-sandstone-border bg-campus-ivory px-3 py-2 text-xs text-campus-espresso focus:border-campus-terracotta focus:bg-white focus:outline-none focus:ring-1 focus:ring-campus-terracotta"
                />
              </div>
            </div>
            <p className="text-[10px] leading-relaxed text-campus-espresso-subtle">
              Email is attached to the listing. Name and phone are collected for this UI preview and are not saved yet.
            </p>
          </section>

          <div className="pt-2 flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="w-full sm:w-auto px-5 py-2.5 rounded bg-campus-terracotta hover:bg-campus-terracotta-hover text-white dark:bg-campus-terracotta-light dark:text-campus-terracotta-text dark:hover:bg-campus-terracotta-light text-xs font-medium transition-colors disabled:opacity-50 shadow-2xs"
            >
              {loading ? 'Submitting...' : 'Publish Listing'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};