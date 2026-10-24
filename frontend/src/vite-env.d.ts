/// <reference types="vite/client" />
interface Window {
  __FOUNDLY_CONFIG__?: {
    supabaseUrl: string;
    supabaseAnonKey: string;
  };
}
