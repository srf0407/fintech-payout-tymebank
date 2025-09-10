// Type definitions for Google Identity Services SDK
interface GoogleAccounts {
  id: {
    initialize: (options: {
      client_id: string;
      callback: (response: any) => void;
    }) => void;
    renderButton: (
      parent: HTMLElement,
      options: {
        theme?: 'outline' | 'filled_blue' | 'filled_black';
        size?: 'large' | 'medium' | 'small';
        width?: number;
      }
    ) => void;
  };
}

declare global {
  interface Window {
    google?: {
      accounts: GoogleAccounts;
    };
  }
}
export {};
